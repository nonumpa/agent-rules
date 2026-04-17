---
name: gdrive
description: Use when accessing Google Drive — list, download, upload, search, or export files via Drive API v3
---

# Google Drive Skill

Google Drive file operations via Drive API v3. List, download, upload, search, and export files.

## Triggers

Use this skill when:
- User provides a Google Drive URL (drive.google.com or docs.google.com)
- User asks to "download from Drive", "list Drive folder", "upload to Drive"
- User asks to access Google Drive files or folders
- Another skill needs files from Google Drive

## Prerequisites

- OAuth credentials configured at `~/.config/gdrive3/<account>/` (secret.json + tokens.json)
- If not configured, run auth first (see below)
- Dependencies: `google-auth`, `requests` (both pre-installed)

## Script Location

```
$SKILL_DIR/gdrive.py
```

## Commands

### List folder contents
```bash
python3 $SKILL_DIR/gdrive.py ls <folder_url_or_id>
python3 $SKILL_DIR/gdrive.py ls "https://drive.google.com/drive/folders/1ZJMAJqRrEXTbcw4fnnX91Cs0l_WVJuaU"
```

### Download a single file
```bash
python3 $SKILL_DIR/gdrive.py download <file_url_or_id> --dest ~/output/
```

### Download entire folder (recursive)
```bash
python3 $SKILL_DIR/gdrive.py download-folder <folder_url_or_id> --dest ~/output/
```
- Automatically exports Google Docs/Sheets/Slides as docx/xlsx/pptx
- Skips video files

### Export Google Docs/Sheets/Slides
```bash
python3 $SKILL_DIR/gdrive.py export <file_url_or_id> --format docx
python3 $SKILL_DIR/gdrive.py export <spreadsheet_url> --format xlsx --dest ~/output/
```
Formats: docx, xlsx, pptx, pdf, csv, txt

### Upload a file
```bash
python3 $SKILL_DIR/gdrive.py upload ./report.pdf --parent <folder_id>
```

### Search files
```bash
python3 $SKILL_DIR/gdrive.py search "自評表"
python3 $SKILL_DIR/gdrive.py search "keyword" --folder <folder_id> --content
```
`--content` flag searches file content in addition to file names.

### Auth setup (first time only)
```bash
python3 $SKILL_DIR/gdrive.py auth --account user@example.com --port 8085
```
Auth flow:
1. Script starts localhost server on port 8085
2. User SSH tunnels: `ssh -L 8085:127.0.0.1:8085 server`
3. User opens the printed URL in local browser
4. After Google authorization, tokens are saved automatically

## As Python Module

```python
import sys
from pathlib import Path
sys.path.insert(0, "<path-to-gdrive-skill-directory>")
from gdrive import DriveClient

client = DriveClient()
files = client.ls("https://drive.google.com/drive/folders/FOLDER_ID")
client.download("FILE_ID", dest=Path("./output"))
client.download_folder("FOLDER_URL", dest=Path("./vendor-docs"))
client.upload(Path("./report.pdf"), parent_id="FOLDER_ID")
results = client.search("keyword", search_content=True)
```

## URL Format Support

Accepts both Google Drive URLs and raw IDs:
- `https://drive.google.com/drive/folders/ABC123`
- `https://drive.google.com/file/d/ABC123/view`
- `https://docs.google.com/spreadsheets/d/ABC123/edit`
- `ABC123` (raw ID)
