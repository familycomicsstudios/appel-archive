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
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRrZEUcAFIiGmzFAjjdUVKWhDSLue_SvTQIxT4ZbhlvBa6yc4l4juAZn3HREfvO0VIv2ms98453VItI/pub?gid=0&single=true&output=tsv"
)


def get_default_sheet_tsv_url() -> str:
    env_value = os.getenv("SHEET_TSV_URL", "").strip()
    if env_value:
        return env_value

    return DEFAULT_SHEET_TSV_URL


COLUMN_MAP = {
    "ALDR_ID": 0,
    "LEVEL_NAME": 1,
    "CREATOR": 2,
    "DIFFICULTY": 3,
    "SKILLS_BALANCE": 4,
    "LIST_POINTS": 5,
    "PROJECT": 6,
    "VIDEO": 7,
    "NOTES": 8,
    "LEVEL_CODE": 9,
    "VICTORS": 10,
    "IMPOSSIBLE": 11,
    "CHALLENGE": 12,
}


def fetch_sheet_rows(tsv_url: str) -> list[list[str]]:
    try:
        with urlopen(tsv_url, timeout=15) as response:
            content = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"Failed to download TSV: {error}") from error

    reader = csv.reader(StringIO(content), delimiter="\t")
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
    )
    if any(host in lower for host in video_hosts):
        return True
    video_extensions = (".mp4", ".webm", ".mov", ".mkv", ".avi")
    return lower.endswith(video_extensions)


def parse_flag(raw: str) -> bool | str:
    value = raw.strip().lower()
    if value in {"", "n/a", "na", "none"}:
        return ""
    if value in {"true", "yes", "y", "1"}:
        return True
    if value in {"false", "no", "n", "0"}:
        return False
    return raw.strip()


def build_metadata(row: list[str], code_hash: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    name = get_cell(row, "LEVEL_NAME")
    creators_raw = get_cell(row, "CREATOR")
    difficulty = get_cell(row, "DIFFICULTY")
    notes = get_cell(row, "NOTES")
    aldr_id = get_cell(row, "ALDR_ID")

    if name:
        metadata["name"] = name
    if creators_raw:
        creators = split_csv_values(creators_raw)
        metadata["creators"] = creators if len(creators) > 1 else creators_raw
    if difficulty:
        metadata["official_difficulty"] = difficulty
        metadata["punter_scale_difficulty_rating"] = difficulty
    if notes:
        metadata["notes"] = notes
    if aldr_id:
        metadata["aldr_id"] = aldr_id

    skills_balance = get_cell(row, "SKILLS_BALANCE")
    if skills_balance:
        metadata["other_difficulty_system_ratings"] = {"skills_balance": skills_balance}

    project = get_cell(row, "PROJECT")
    if project:
        metadata["source"] = project

    video = get_cell(row, "VIDEO")
    if is_actual_video(video):
        metadata["video"] = video

    impossible = parse_flag(get_cell(row, "IMPOSSIBLE"))
    if impossible is True:
        notes = append_note(notes, "Impossible: true")

    challenge = parse_flag(get_cell(row, "CHALLENGE"))
    if challenge is True:
        notes = append_note(notes, "Challenge: true")

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

    if not overwrite and (code_file.exists() or meta_file.exists()):
        return "skipped"

    if dry_run:
        return "created"

    code_file.write_text(level_code, encoding="utf-8")
    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
        description="Download ALDR Google Sheet TSV and convert rows to level code + metadata files."
    )
    parser.add_argument(
        "--url",
        default=get_default_sheet_tsv_url(),
        help="TSV export URL for the sheet. Defaults to SHEET_TSV_URL env var or built-in URL.",
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
