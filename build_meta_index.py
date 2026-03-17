#!/usr/bin/env python3

import json
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    meta_dir = repo_root / "Levels" / "meta"
    output_file = repo_root / "Levels" / "meta-index.json"

    entries = []
    for path in sorted(meta_dir.glob("*.json")):
        if path.name == "sample.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue

        code_hash = str(data.get("code_hash") or path.stem)
        entries.append({"hash": code_hash, "data": data})

    output_file.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {output_file}")


if __name__ == "__main__":
    main()
