#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path
from typing import Any


def is_array_field(field_definition: dict[str, Any]) -> bool:
    sample_values = field_definition.get("sample_values", [])
    if not isinstance(sample_values, list):
        return False
    return any(isinstance(value, list) for value in sample_values)


def is_simple_field(field_definition: dict[str, Any]) -> bool:
    return field_definition.get("simple") is True


def select_fields_for_mode(fields: list[dict[str, Any]], advanced_mode: bool) -> list[dict[str, Any]]:
    if advanced_mode:
        return fields
    return [field for field in fields if is_simple_field(field)]


def prompt_for_metadata(fields: list[dict[str, Any]]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    print("\nEnter metadata fields. Leave blank to skip a field.\n")

    for field in fields:
        field_name = field.get("field")
        if not field_name or field_name == "level_code":
            continue

        display_name = field.get("display_name") or field_name
        description = field.get("description")

        print(f"{display_name}:")
        if description:
            print(f"  {description}")

        raw_value = input("> ").strip()
        if not raw_value:
            print()
            continue

        if is_array_field(field):
            parsed_values = [item.strip() for item in raw_value.split(",") if item.strip()]
            if parsed_values:
                metadata[field_name] = parsed_values
        else:
            metadata[field_name] = raw_value

        print()

    return metadata


def load_fields(fields_file: Path) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(fields_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Failed to load fields from {fields_file}: {error}") from error

    if not isinstance(parsed, list):
        raise RuntimeError("fields.json must contain a JSON array.")

    valid_fields = [entry for entry in parsed if isinstance(entry, dict)]
    return valid_fields


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    code_dir = repo_root / "Levels" / "code"
    meta_dir = repo_root / "Levels" / "meta"
    fields_file = repo_root / "fields.json"

    code_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    try:
        fields = load_fields(fields_file)
    except RuntimeError as error:
        print(error)
        return

    level_code = input("Paste the level code: ")
    if not level_code.strip():
        print("No level code provided. Exiting.")
        return

    advanced_mode_response = input("Enable advanced mode? (y/N): ").strip().lower()
    advanced_mode = advanced_mode_response in {"y", "yes"}

    selected_fields = select_fields_for_mode(fields, advanced_mode)
    metadata = prompt_for_metadata(selected_fields)

    code_hash = hashlib.sha256(level_code.encode("utf-8")).hexdigest()
    metadata["code_hash"] = code_hash

    code_file = code_dir / f"{code_hash}.txt"
    meta_file = meta_dir / f"{code_hash}.json"

    if code_file.exists() or meta_file.exists():
        print("A level with this code hash already exists. No files were written.")
        print(f"Hash: {code_hash}")
        return

    code_file.write_text(level_code, encoding="utf-8")
    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Level added successfully.")
    print(f"Code file: {code_file}")
    print(f"Metadata file: {meta_file}")


if __name__ == "__main__":
    main()