#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
import os
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

DEFAULT_SHEET_TSV_URL = (
    "https://docs.google.com/spreadsheets/d/1q01STuHSABJcptgHRmfFeXzkhFRtY6ymurO9uxkflfQ/export?format=tsv&gid=0"
)

overwrite_rules: dict[str, bool] = {}

def merge_metadata(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    merged = existing.copy()

    for key, value in new.items():

        # Key doesn't exist yet
        if key not in merged:
            merged[key] = value
            continue

        old_value = merged[key]

        # Same value
        if old_value == value:
            continue

        # Recursively merge dictionaries
        if isinstance(old_value, dict) and isinstance(value, dict):
            merged[key] = merge_metadata(old_value, value)
            continue

        # Combine lists
        if isinstance(old_value, list) and isinstance(value, list):
            combined = old_value.copy()

            for item in value:
                if item not in combined:
                    combined.append(item)

            merged[key] = combined
            continue

        # Apply saved rule
        if key in overwrite_rules:
            if overwrite_rules[key]:
                merged[key] = value
            continue

        while True:
            choice = input(
                f"\nConflict for '{key}'\n"
                f"Existing: {old_value}\n"
                f"New:      {value}\n"
                f"Overwrite? (y/n): "
            ).strip().lower()

            if choice in ("y", "n"):
                break

        if choice == "y":
            merged[key] = value

            always = input(
                f"Always overwrite '{key}'? (y/n): "
            ).strip().lower()

            if always == "y":
                overwrite_rules[key] = True

        else:
            never = input(
                f"Never overwrite '{key}'? (y/n): "
            ).strip().lower()

            if never == "y":
                overwrite_rules[key] = False

    return merged

def get_default_sheet_tsv_url() -> str:
    env_value = os.getenv("AHLL_SHEET_TSV_URL", "").strip()
    if env_value:
        return env_value
    env_value = os.getenv("SHEET_TSV_URL", "").strip()
    if env_value:
        return env_value

    return DEFAULT_SHEET_TSV_URL


COLUMN_MAP = {
    "AHLL_ID": 0,
    "RANK": 1,
    "LEVEL_NAME": 2,
    "IMAGE": 3,
    "CREATOR": 4,
    "PROJECT": 5,
    "DIFFICULTY_1": 6,
    "DIFFICULTY_2": 7,
    "VERIFIER": 8,
    "FASTEST_TIME": 9,
    "VIDEO": 10,
    "POINTS": 11,
    "LEVEL_CODE": 12,
    "NOTES": 13,
    "EXPIRATION_DATE": 14,
}


def fetch_sheet_rows(tsv_url: str) -> list[list[str]]:
    try:
        with urlopen(tsv_url, timeout=15) as response:
            content = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"Failed to download TSV: {error}") from error

    reader = csv.reader(StringIO(content, newline=""), delimiter="\t")
    return list(reader)


def get_cell(row: list[str], column_name: str) -> str:
    index = COLUMN_MAP[column_name]
    if index >= len(row):
        return ""
    return row[index].strip()


def split_csv_values(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def append_note(existing_notes: str, addition: str) -> str:
    addition = addition.strip()
    if not addition:
        return existing_notes
    if not existing_notes:
        return addition
    return f"{existing_notes}\n{addition}"


def is_thumbnail_reference(value: str) -> bool:
    lower = value.strip().lower()
    if not lower:
        return False
    if "/assets/thumbnails/" in lower:
        return True
    image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")
    return lower.endswith(image_extensions)


def is_actual_video(value: str) -> bool:
    lower = value.strip().lower()
    if not lower:
        return False
    if is_thumbnail_reference(lower):
        return False
    video_hosts = (
        "youtube.com/watch",
        "youtu.be/",
        "youtube.com/shorts/",
        "vimeo.com/",
        "twitch.tv/",
        "streamable.com/",
        "scratch.mit.edu/projects/",
    )
    if any(host in lower for host in video_hosts):
        return True
    video_extensions = (".mp4", ".webm", ".mov", ".mkv", ".avi")
    return lower.endswith(video_extensions)


def strip_difficulty_text(raw: str) -> str:
    val = raw.strip()
    for prefix in ["low", "mid", "high", "Low", "Mid", "High"]:
        if val.lower().startswith(prefix):
            val = val[len(prefix):].strip()
    return val


def build_metadata(row: list[str], code_hash: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    name = get_cell(row, "LEVEL_NAME")
    creators_raw = get_cell(row, "CREATOR")
    diff1 = get_cell(row, "DIFFICULTY_1")
    diff2 = get_cell(row, "DIFFICULTY_2")
    notes = get_cell(row, "NOTES")
    ahll_id = get_cell(row, "AHLL_ID")

    if name:
        metadata["name"] = name
    if creators_raw:
        creators = split_csv_values(creators_raw)
        metadata["creators"] = creators if len(creators) > 1 else creators_raw

    # DIFFICULTY_1 is the difficulty chosen by the creator (official_difficulty)
    if diff1:
        metadata["official_difficulty"] = diff1

    # DIFFICULTY_2 is based on list placement (michael_chan_extended_difficulty_rating, stripped of text)
    list_diff = diff2 if diff2 else diff1
    if list_diff:
        metadata["michael_chan_extended_difficulty_rating"] = strip_difficulty_text(list_diff)

    # DIFFICULTY_2 as a separate field with subtier text
    if diff2:
        metadata["ahll_difficulty"] = diff2

    if ahll_id:
        metadata["ahll_id"] = ahll_id

    # Populate other difficulty/ranking details
    ratings = {}
    rank = get_cell(row, "RANK")
    if rank:
        ratings["ahll_rank"] = rank

    if ratings:
        metadata["other_difficulty_system_ratings"] = ratings

    project = get_cell(row, "PROJECT")
    if project and project.lower() not in {"", "n/a", "na", "none", "-"}:
        metadata["source"] = project

    video = get_cell(row, "VIDEO")
    if is_actual_video(video):
        metadata["video"] = video

    verifier = get_cell(row, "VERIFIER")
    if verifier and verifier.lower() not in {"", "n/a", "na", "none", "-"}:
        notes = append_note(notes, f"Verifier/First Victor: {verifier}")

    fastest_time = get_cell(row, "FASTEST_TIME")
    if fastest_time and fastest_time.lower() not in {"", "n/a", "na", "none", "-"}:
        notes = append_note(notes, f"Fastest Time: {fastest_time}")

    if notes:
        metadata["notes"] = notes

    metadata["code_hash"] = code_hash
    return metadata


def write_level_files(
    code_dir: Path,
    meta_dir: Path,
    level_code: str,
    metadata: dict[str, Any],
    overwrite: bool,
    dry_run: bool,
) -> str:
    code_hash = metadata["code_hash"]

    code_file = code_dir / f"{code_hash}.txt"
    meta_file = meta_dir / f"{code_hash}.json"

    if meta_file.exists():
        try:
            existing_metadata = json.loads(
                meta_file.read_text(encoding="utf-8")
            )

            metadata = merge_metadata(
                existing_metadata,
                metadata,
            )

        except Exception as e:
            print(f"Warning: Could not read {meta_file}: {e}")

    if not overwrite and code_file.exists() and not meta_file.exists():
        return "skipped"

    if dry_run:
        return "created"

    code_file.write_text(level_code, encoding="utf-8")

    meta_file.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return "created"


def run(limit: int | None, overwrite: bool, dry_run: bool, tsv_url: str) -> int:
    repo_root = Path(__file__).resolve().parent
    code_dir = repo_root / "Levels" / "code"
    meta_dir = repo_root / "Levels" / "meta"
    code_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    rows = fetch_sheet_rows(tsv_url)
    if len(rows) < 2:
        print("No data rows found in sheet.")
        return 1

    created = 0
    skipped_empty_code = 0
    skipped_existing = 0

    data_rows = rows[1:]
    if limit is not None:
        data_rows = data_rows[:limit]

    for row in data_rows:
        # Check if the row has the required length
        if len(row) <= COLUMN_MAP["LEVEL_CODE"]:
            continue

        level_code = get_cell(row, "LEVEL_CODE")
        if not level_code:
            skipped_empty_code += 1
            continue

        code_hash = hashlib.sha256(level_code.encode("utf-8")).hexdigest()
        metadata = build_metadata(row, code_hash)
        result = write_level_files(code_dir, meta_dir, level_code, metadata, overwrite, dry_run)

        if result == "created":
            created += 1
        else:
            skipped_existing += 1

    print(f"Rows processed: {len(data_rows)}")
    print(f"Levels created: {created}{' (dry-run)' if dry_run else ''}")
    print(f"Skipped (empty level code): {skipped_empty_code}")
    print(f"Skipped (already exists): {skipped_existing}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download AHLL:E Google Sheet TSV and convert rows to level code + metadata files."
    )
    parser.add_argument(
        "--url",
        default=get_default_sheet_tsv_url(),
        help="TSV export URL for the sheet. Defaults to AHLL_SHEET_TSV_URL env var or built-in URL.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row limit (after header).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing hash files if they already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and map rows without writing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raise SystemExit(run(args.limit, args.overwrite, args.dry_run, args.url))


if __name__ == "__main__":
    main()
