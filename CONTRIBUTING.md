# Contributing to appel-archive

Thank you for contributing! Follow the steps below to add a level to the archive.

## Directory Structure

```
Levels/
├── code/   # Raw level code files (.txt)
└── meta/   # Level metadata files (.json)
```

## Naming Convention

All files are named using the **SHA256 hash** of the level's raw code (the contents of the `.txt` file), with no extension for the hash itself — the files use `.txt` and `.json` extensions respectively.

For example, if your level code hashes to `a3f5c2...e9b1` (abbreviated), you would create:
- `Levels/code/a3f5c2...e9b1.txt`
- `Levels/meta/a3f5c2...e9b1.json`

(Use the full 64-character hex string as the actual filename.)

You can compute the hash with:
```bash
sha256sum your_level.txt
```

## Adding a Level

1. **Export the level code** from the game and save it as a plain text file.
2. **Compute the SHA256 hash** of the file contents.
3. **Add the code file** at `Levels/code/<hash>.txt`.
4. **Add the metadata file** at `Levels/meta/<hash>.json` using the following schema:

```json
{
  "name": "Level Name",
  "alternate_names": ["Alt Name 1", "Alt Name 2"],
  "acronym": "LN",
  "creators": ["Creator One", "Creator Two"],
  "description": "A brief description of the level.",
  "mod": "Name of the mod the level originates from",
  "mod_url": "The URL to the mod the level originates from",
  "official_difficulty": "Easy / Medium / Hard / etc."
}
```

Please note that fields may be omitted if needed, such as if the level has no official difficulty, name, etc. No fields are required. Custom fields can also be added if relevant.

| Field | Type | Description |
|---|---|---|
| `name` | string | The primary display name of the level |
| `alternate_names` | array of strings | Any other names the level is known by (can be empty `[]`) |
| `acronym` | string | A short acronym for the level name |
| `creators` | array of strings | The username(s) of the level's creator(s) |
| `description` | string | A brief description of the level |
| `mod` | string | The mod the level originates from (leave blank if none) |
| `mod_url` | string | A link to the mod the level originates from (leave blank if none) |
| `official_difficulty` | string | The official rated difficulty of the level, according to the mod or creator (this can be in any format) |

5. **Open a pull request** with both files included.

## Sample Files

See [`Levels/code/sample.txt`](Levels/code/sample.txt) and [`Levels/meta/sample.json`](Levels/meta/sample.json) for examples of the expected format.
