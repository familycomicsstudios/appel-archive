# appel-archive
A repository of Appel levels and their relevant metadata, indexed by the level code's SHA256 hash

## Import from ALDR sheet

Use `sheet_to_levels.py` to download the Google Sheet TSV and convert each row into:

- `Levels/code/<sha256>.txt` (raw level code)
- `Levels/meta/<sha256>.json` (mapped metadata)

Examples:

```bash
python sheet_to_levels.py --dry-run --limit 20
python sheet_to_levels.py
python sheet_to_levels.py --overwrite
```

By default, existing files are skipped unless `--overwrite` is provided.
