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
~/.config/opencode/superpowers/skills/gdrive/gdrive.py
```

## Commands

### List folder contents
```bash
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py ls <folder_url_or_id>
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py ls "https://drive.google.com/drive/folders/1ZJMAJqRrEXTbcw4fnnX91Cs0l_WVJuaU"
```

### Download a single file
```bash
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py download <file_url_or_id> --dest ~/output/
```

### Download entire folder (recursive)
```bash
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py download-folder <folder_url_or_id> --dest ~/output/
```
- Automatically exports Google Docs/Sheets/Slides as docx/xlsx/pptx
- Skips video files

### Export Google Docs/Sheets/Slides
```bash
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py export <file_url_or_id> --format docx
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py export <spreadsheet_url> --format xlsx --dest ~/output/
```
Formats: docx, xlsx, pptx, pdf, csv, txt

### Upload a file
```bash
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py upload ./report.pdf --parent <folder_id>
```

### Search files
```bash
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py search "自評表"
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py search "keyword" --folder <folder_id> --content
```
`--content` flag searches file content in addition to file names.

### Auth setup (first time only)
```bash
python3 ~/.config/opencode/superpowers/skills/gdrive/gdrive.py auth --account user@example.com --port 8085
```
Auth flow:
1. Script starts localhost server on port 8085
2. User SSH tunnels: `ssh -L 8085:127.0.0.1:8085 server`
3. User opens the printed URL in local browser
4. After Google authorization, tokens are saved automatically

## As Python Module

```python
import sys
sys.path.insert(0, str(Path("~/.config/opencode/superpowers/skills/gdrive").expanduser()))
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
