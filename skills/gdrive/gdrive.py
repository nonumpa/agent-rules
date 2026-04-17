"""Google Drive operations via Drive API v3.

Commands:
    auth             OAuth setup (localhost redirect + SSH tunnel)
    ls               List folder contents
    download         Download a single file
    download-folder  Recursively download an entire folder
    export           Export Google Docs/Sheets/Slides to local format
    upload           Upload a file to Drive
    search           Search files by name or content

Usage:
    python3 gdrive.py auth [--port 8085] [--account EMAIL]
    python3 gdrive.py ls <folder_url_or_id>
    python3 gdrive.py download <file_url_or_id> [--dest DIR]
    python3 gdrive.py download-folder <folder_url_or_id> [--dest DIR]
    python3 gdrive.py export <file_url_or_id> --format docx|xlsx|pdf [--dest DIR]
    python3 gdrive.py upload <local_file> [--parent FOLDER_ID] [--name NAME]
    python3 gdrive.py search <query> [--folder FOLDER_ID]

    As module:
        from gdrive import DriveClient
        client = DriveClient()
        files = client.ls("1ZJMAJqRrEXTbcw4fnnX91Cs0l_WVJuaU")
        client.download("file_id", dest=Path("./out"))
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
from google.oauth2.credentials import Credentials
import google.auth.transport.requests

GDRIVE3_CONFIG = Path.home() / ".config" / "gdrive3"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]
TOKEN_URI = "https://oauth2.googleapis.com/token"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
DRIVE_API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"

GOOGLE_MIME_EXPORT = {
    "application/vnd.google-apps.document": {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "txt": "text/plain",
    },
    "application/vnd.google-apps.spreadsheet": {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "pdf": "application/pdf",
    },
    "application/vnd.google-apps.presentation": {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
    },
}

DEFAULT_EXPORT_EXT = {
    "application/vnd.google-apps.document": "docx",
    "application/vnd.google-apps.spreadsheet": "xlsx",
    "application/vnd.google-apps.presentation": "pptx",
}


def _extract_id(url_or_id: str) -> str:
    patterns = [
        r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)",
        r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
        r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)",
        r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)",
        r"docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, url_or_id)
        if m:
            return m.group(1)
    return url_or_id.strip()


def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}" if unit != "B" else f"{nbytes} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class _AuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    auth_code: Optional[str] = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            _AuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<!DOCTYPE html><html><body>"
                "<h2>✅ 授權成功！</h2>"
                "<p>可以關閉此分頁。</p>"
                "</body></html>".encode("utf-8")
            )
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h2>❌ 授權失敗：{error}</h2>".encode("utf-8"))

    def log_message(self, format, *args):
        pass


def _load_gdrive3_secret(account_dir: Path) -> dict:
    secret_file = account_dir / "secret.json"
    if not secret_file.exists():
        raise FileNotFoundError(f"No secret.json in {account_dir}")
    return json.loads(secret_file.read_text())


def _load_gdrive3_tokens(account_dir: Path) -> dict:
    tokens_file = account_dir / "tokens.json"
    if not tokens_file.exists():
        raise FileNotFoundError(f"No tokens.json in {account_dir}")
    tokens = json.loads(tokens_file.read_text())
    if isinstance(tokens, list) and tokens:
        return max(tokens, key=lambda t: len(t.get("scopes", [])))
    raise ValueError(f"Invalid tokens.json format in {account_dir}")


def _resolve_account(account: Optional[str] = None) -> str:
    if account:
        return account
    account_file = GDRIVE3_CONFIG / "account.json"
    if account_file.exists():
        data = json.loads(account_file.read_text())
        current = data.get("current")
        if current:
            return current
    accounts = [
        d.name for d in GDRIVE3_CONFIG.iterdir()
        if d.is_dir() and (d / "secret.json").exists()
    ] if GDRIVE3_CONFIG.exists() else []
    if len(accounts) == 1:
        return accounts[0]
    raise RuntimeError(
        "No account configured. Run: python3 gdrive.py auth --account YOUR_EMAIL"
    )


def _save_tokens(account_dir: Path, creds: Credentials):
    now = time.gmtime()
    token_entry = {
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "token": {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expires_at": list(now[:9]),
            "id_token": None,
        },
    }
    tokens_file = account_dir / "tokens.json"
    if tokens_file.exists():
        try:
            existing = json.loads(tokens_file.read_text())
            if isinstance(existing, list):
                for i, t in enumerate(existing):
                    if set(t.get("scopes", [])) == set(token_entry["scopes"]):
                        existing[i] = token_entry
                        break
                else:
                    existing.append(token_entry)
                tokens_file.write_text(json.dumps(existing, indent=2))
                return
        except (json.JSONDecodeError, KeyError):
            pass
    tokens_file.write_text(json.dumps([token_entry], indent=2))


def load_credentials(account: Optional[str] = None) -> Credentials:
    account = _resolve_account(account)
    account_dir = GDRIVE3_CONFIG / account
    secret = _load_gdrive3_secret(account_dir)
    token_entry = _load_gdrive3_tokens(account_dir)
    token = token_entry["token"]

    creds = Credentials(
        token=None,
        refresh_token=token.get("refresh_token"),
        client_id=secret["client_id"],
        client_secret=secret["client_secret"],
        token_uri=TOKEN_URI,
        scopes=token_entry.get("scopes", SCOPES),
    )

    creds.refresh(google.auth.transport.requests.Request())
    _save_tokens(account_dir, creds)

    return creds


def do_auth(account: str, port: int = 8085, client_id: Optional[str] = None, client_secret: Optional[str] = None):
    account_dir = GDRIVE3_CONFIG / account
    account_dir.mkdir(parents=True, exist_ok=True)

    if client_id and client_secret:
        secret = {"client_id": client_id, "client_secret": client_secret}
        (account_dir / "secret.json").write_text(json.dumps(secret, indent=2))
    elif (account_dir / "secret.json").exists():
        secret = json.loads((account_dir / "secret.json").read_text())
    else:
        raise RuntimeError(
            "No client credentials found. Provide --client-id and --client-secret, "
            "or place secret.json in " + str(account_dir)
        )

    redirect_uri = f"http://127.0.0.1:{port}"
    auth_url = (
        f"{AUTH_URI}?"
        f"scope={urllib.parse.quote(' '.join(SCOPES))}"
        f"&access_type=offline"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&response_type=code"
        f"&client_id={secret['client_id']}"
        f"&prompt=consent"
    )

    _AuthCallbackHandler.auth_code = None
    server = http.server.HTTPServer(("127.0.0.1", port), _AuthCallbackHandler)
    server_thread = threading.Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    print(f"1. SSH tunnel:  ssh -L {port}:127.0.0.1:{port} <your-server>")
    print(f"2. Open URL in local browser:\n\n{auth_url}\n")
    print("Waiting for authorization...")

    server_thread.join(timeout=300)
    server.server_close()

    if not _AuthCallbackHandler.auth_code:
        raise RuntimeError("Authorization timed out or failed.")

    token_resp = requests.post(TOKEN_URI, data={
        "code": _AuthCallbackHandler.auth_code,
        "client_id": secret["client_id"],
        "client_secret": secret["client_secret"],
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })
    token_resp.raise_for_status()
    token_data = token_resp.json()

    now = time.gmtime()
    token_entry = [{
        "scopes": SCOPES,
        "token": {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "expires_at": list(now[:9]),
            "id_token": token_data.get("id_token"),
        },
    }]
    (account_dir / "tokens.json").write_text(json.dumps(token_entry, indent=2))

    account_json = GDRIVE3_CONFIG / "account.json"
    account_json.write_text(json.dumps({"current": account}, indent=2))

    print(f"✅ Authorized as {account}")


# ---------------------------------------------------------------------------
# Drive Client
# ---------------------------------------------------------------------------

class DriveClient:
    def __init__(self, account: Optional[str] = None):
        self._creds = load_credentials(account)
        self._session = requests.Session()

    def _headers(self) -> dict:
        if not self._creds.valid:
            self._creds.refresh(google.auth.transport.requests.Request())
        return {"Authorization": f"Bearer {self._creds.token}"}

    def _get(self, url: str, params: dict = None, **kwargs) -> requests.Response:
        params = params or {}
        params.setdefault("supportsAllDrives", "true")
        params.setdefault("includeItemsFromAllDrives", "true")
        resp = self._session.get(url, headers=self._headers(), params=params, **kwargs)
        resp.raise_for_status()
        return resp

    def _post(self, url: str, **kwargs) -> requests.Response:
        resp = self._session.post(url, headers=self._headers(), **kwargs)
        resp.raise_for_status()
        return resp

    def ls(self, folder_id: str, page_size: int = 100) -> list[dict]:
        folder_id = _extract_id(folder_id)
        items = []
        page_token = None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                "pageSize": page_size,
                "orderBy": "folder, name",
            }
            if page_token:
                params["pageToken"] = page_token
            data = self._get(f"{DRIVE_API}/files", params=params).json()
            items.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return items

    def download(self, file_id: str, dest: Path = Path("."), name: Optional[str] = None) -> Path:
        file_id = _extract_id(file_id)
        meta = self._get(
            f"{DRIVE_API}/files/{file_id}",
            params={"fields": "id, name, mimeType, size"},
        ).json()

        mime = meta.get("mimeType", "")
        file_name = name or meta["name"]

        if mime in GOOGLE_MIME_EXPORT:
            ext = DEFAULT_EXPORT_EXT.get(mime, "pdf")
            return self.export(file_id, fmt=ext, dest=dest, name=file_name)

        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        out_path = dest / file_name

        resp = self._get(
            f"{DRIVE_API}/files/{file_id}",
            params={"alt": "media"},
            stream=True,
        )

        total = int(meta.get("size", 0))
        downloaded = 0
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 // total
                    print(f"\r  {file_name}: {pct}% ({_human_size(downloaded)}/{_human_size(total)})", end="", flush=True)
        if total > 0:
            print()

        return out_path

    def download_folder(self, folder_id: str, dest: Path = Path("."), _depth: int = 0) -> list[Path]:
        folder_id = _extract_id(folder_id)

        if _depth == 0:
            meta = self._get(
                f"{DRIVE_API}/files/{folder_id}",
                params={"fields": "name"},
            ).json()
            dest = Path(dest) / meta.get("name", folder_id)

        dest.mkdir(parents=True, exist_ok=True)
        items = self.ls(folder_id)
        downloaded = []

        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                sub_dir = dest / item["name"]
                downloaded.extend(self.download_folder(item["id"], dest=sub_dir, _depth=_depth + 1))
            elif item["mimeType"].startswith("video/"):
                print(f"  Skipping video: {item['name']}")
                continue
            else:
                try:
                    path = self.download(item["id"], dest=dest, name=item["name"])
                    downloaded.append(path)
                except Exception as e:
                    print(f"  ERROR downloading {item['name']}: {e}", file=sys.stderr)

        return downloaded

    def export(self, file_id: str, fmt: str, dest: Path = Path("."), name: Optional[str] = None) -> Path:
        file_id = _extract_id(file_id)
        meta = self._get(
            f"{DRIVE_API}/files/{file_id}",
            params={"fields": "id, name, mimeType"},
        ).json()

        mime = meta.get("mimeType", "")
        export_mimes = GOOGLE_MIME_EXPORT.get(mime, {})
        if fmt not in export_mimes:
            available = ", ".join(export_mimes.keys()) if export_mimes else "N/A (not a Google Doc)"
            raise ValueError(f"Cannot export as '{fmt}'. Available: {available}")

        export_mime = export_mimes[fmt]
        base_name = name or meta["name"]
        if not base_name.endswith(f".{fmt}"):
            base_name = f"{base_name}.{fmt}"

        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        out_path = dest / base_name

        resp = self._get(
            f"{DRIVE_API}/files/{file_id}/export",
            params={"mimeType": export_mime},
            stream=True,
        )

        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"  Exported: {out_path}")
        return out_path

    def upload(self, local_path: Path, parent_id: Optional[str] = None, name: Optional[str] = None) -> dict:
        local_path = Path(local_path)
        if not local_path.is_file():
            raise FileNotFoundError(f"File not found: {local_path}")

        file_name = name or local_path.name
        metadata = {"name": file_name}
        if parent_id:
            metadata["parents"] = [_extract_id(parent_id)]

        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(local_path))
        mime_type = mime_type or "application/octet-stream"

        headers = self._headers()
        headers["Content-Type"] = "multipart/related; boundary=gdrive_boundary"

        meta_json = json.dumps(metadata)
        file_data = local_path.read_bytes()

        body = (
            b"--gdrive_boundary\r\n"
            b"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            + meta_json.encode("utf-8") + b"\r\n"
            b"--gdrive_boundary\r\n"
            b"Content-Type: " + mime_type.encode("utf-8") + b"\r\n\r\n"
            + file_data + b"\r\n"
            b"--gdrive_boundary--"
        )

        resp = self._session.post(
            f"{UPLOAD_API}/files?uploadType=multipart&fields=id,name,mimeType,size,webViewLink",
            headers=headers,
            data=body,
        )
        resp.raise_for_status()
        result = resp.json()
        print(f"  Uploaded: {file_name} → {result.get('webViewLink', result['id'])}")
        return result

    def search(
        self,
        query: str,
        folder_id: Optional[str] = None,
        search_content: bool = False,
        page_size: int = 50,
    ) -> list[dict]:
        q_parts = ["trashed = false"]

        if folder_id:
            q_parts.append(f"'{_extract_id(folder_id)}' in parents")

        escaped = query.replace("\\", "\\\\").replace("'", "\\'")
        if search_content:
            q_parts.append(f"(name contains '{escaped}' or fullText contains '{escaped}')")
        else:
            q_parts.append(f"name contains '{escaped}'")

        items = []
        page_token = None
        while True:
            params = {
                "q": " and ".join(q_parts),
                "fields": "nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, webViewLink)",
                "pageSize": page_size,
                "orderBy": "modifiedTime desc",
            }
            if page_token:
                params["pageToken"] = page_token
            data = self._get(f"{DRIVE_API}/files", params=params).json()
            items.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token or len(items) >= page_size:
                break
        return items


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _format_ls(items: list[dict]) -> str:
    lines = []
    for f in items:
        is_folder = f["mimeType"] == "application/vnd.google-apps.folder"
        is_gdoc = f["mimeType"] in GOOGLE_MIME_EXPORT
        size = "[DIR]" if is_folder else ("[Google Doc]" if is_gdoc else _human_size(int(f.get("size", 0))))
        icon = "📁" if is_folder else ("📄" if is_gdoc else "📎")
        lines.append(f"  {icon} {f['name']:<50s} {size:>12s}  {f['id']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Google Drive operations")
    parser.add_argument("--account", "-a", default=None, help="Account email")
    sub = parser.add_subparsers(dest="command", required=True)

    p_auth = sub.add_parser("auth", help="OAuth authorization setup")
    p_auth.add_argument("--port", type=int, default=8085)
    p_auth.add_argument("--client-id", default=None)
    p_auth.add_argument("--client-secret", default=None)

    p_ls = sub.add_parser("ls", help="List folder contents")
    p_ls.add_argument("folder", help="Folder URL or ID")

    p_dl = sub.add_parser("download", help="Download a single file")
    p_dl.add_argument("file", help="File URL or ID")
    p_dl.add_argument("--dest", "-d", default=".", help="Destination directory")
    p_dl.add_argument("--name", "-n", default=None, help="Override file name")

    p_dlf = sub.add_parser("download-folder", help="Recursively download a folder")
    p_dlf.add_argument("folder", help="Folder URL or ID")
    p_dlf.add_argument("--dest", "-d", default=".", help="Destination directory")

    p_exp = sub.add_parser("export", help="Export Google Docs/Sheets/Slides")
    p_exp.add_argument("file", help="File URL or ID")
    p_exp.add_argument("--format", "-f", required=True, choices=["docx", "xlsx", "pptx", "pdf", "csv", "txt"])
    p_exp.add_argument("--dest", "-d", default=".", help="Destination directory")
    p_exp.add_argument("--name", "-n", default=None)

    p_up = sub.add_parser("upload", help="Upload a file")
    p_up.add_argument("file", help="Local file path")
    p_up.add_argument("--parent", "-p", default=None, help="Parent folder ID/URL")
    p_up.add_argument("--name", "-n", default=None, help="Override file name")

    p_search = sub.add_parser("search", help="Search files")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--folder", "-f", default=None, help="Limit to folder")
    p_search.add_argument("--content", "-c", action="store_true", help="Also search file content")

    args = parser.parse_args()

    if args.command == "auth":
        account = args.account
        if not account:
            account = input("Google account email: ").strip()
        do_auth(account, port=args.port, client_id=args.client_id, client_secret=args.client_secret)
        return

    client = DriveClient(account=args.account)

    if args.command == "ls":
        items = client.ls(args.folder)
        print(f"Found {len(items)} items:\n")
        print(_format_ls(items))

    elif args.command == "download":
        path = client.download(args.file, dest=Path(args.dest), name=args.name)
        print(f"Downloaded: {path}")

    elif args.command == "download-folder":
        paths = client.download_folder(args.folder, dest=Path(args.dest))
        print(f"\nDownloaded {len(paths)} files.")
        for p in paths:
            print(f"  {p}")

    elif args.command == "export":
        path = client.export(args.file, fmt=args.format, dest=Path(args.dest), name=args.name)
        print(f"Exported: {path}")

    elif args.command == "upload":
        result = client.upload(Path(args.file), parent_id=args.parent, name=args.name)
        print(f"File ID: {result['id']}")

    elif args.command == "search":
        items = client.search(args.query, folder_id=args.folder, search_content=args.content)
        print(f"Found {len(items)} results:\n")
        print(_format_ls(items))


if __name__ == "__main__":
    main()
