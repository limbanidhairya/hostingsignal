"""
HostingSignal — File Manager
Server-side file operations for the web-based file manager.
"""
import os
import shutil
import mimetypes
import zipfile
from datetime import datetime
from .server_utils import DEV_MODE, logger

WEB_ROOT = "/home"

DEMO_FILES = [
    {"name": "public_html", "type": "directory", "size": 0, "modified": "2026-02-28 10:00", "permissions": "drwxr-xr-x", "children": 5},
    {"name": "logs", "type": "directory", "size": 0, "modified": "2026-02-28 12:30", "permissions": "drwxr-xr-x", "children": 2},
    {"name": ".htaccess", "type": "file", "size": 234, "modified": "2026-02-27 08:15", "permissions": "-rw-r--r--"},
    {"name": "wp-config.php", "type": "file", "size": 3245, "modified": "2026-02-26 14:20", "permissions": "-rw-r--r--"},
    {"name": "index.html", "type": "file", "size": 1024, "modified": "2026-02-28 09:00", "permissions": "-rw-r--r--"},
    {"name": "style.css", "type": "file", "size": 8192, "modified": "2026-02-25 16:45", "permissions": "-rw-r--r--"},
]


def _safe_path(base: str, path: str) -> str | None:
    """Prevent path traversal attacks."""
    full = os.path.realpath(os.path.join(base, path))
    if not full.startswith(os.path.realpath(base)):
        return None
    return full


def list_files(path: str, base_dir: str = WEB_ROOT) -> list[dict]:
    """List files and directories at a given path."""
    if DEV_MODE:
        return DEMO_FILES
    full_path = _safe_path(base_dir, path)
    if not full_path or not os.path.isdir(full_path):
        return []
    items = []
    for name in sorted(os.listdir(full_path)):
        fp = os.path.join(full_path, name)
        try:
            stat = os.stat(fp)
            is_dir = os.path.isdir(fp)
            items.append({
                "name": name,
                "type": "directory" if is_dir else "file",
                "size": 0 if is_dir else stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "permissions": oct(stat.st_mode)[-3:],
                "children": len(os.listdir(fp)) if is_dir else None,
            })
        except PermissionError:
            continue
    return items


def read_text_file(path: str, base_dir: str = WEB_ROOT) -> str | None:
    full_path = _safe_path(base_dir, path)
    if not full_path or not os.path.isfile(full_path):
        return None
    try:
        with open(full_path, "r", errors="replace") as f:
            return f.read(1024 * 512)  # Max 512KB
    except Exception:
        return None


def write_text_file(path: str, content: str, base_dir: str = WEB_ROOT) -> bool:
    full_path = _safe_path(base_dir, path)
    if not full_path:
        return False
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    return True


def create_directory(path: str, base_dir: str = WEB_ROOT) -> bool:
    full_path = _safe_path(base_dir, path)
    if not full_path:
        return False
    os.makedirs(full_path, exist_ok=True)
    return True


def delete_item(path: str, base_dir: str = WEB_ROOT) -> bool:
    full_path = _safe_path(base_dir, path)
    if not full_path or not os.path.exists(full_path):
        return False
    if os.path.isdir(full_path):
        shutil.rmtree(full_path)
    else:
        os.remove(full_path)
    return True


def rename_item(old_path: str, new_name: str, base_dir: str = WEB_ROOT) -> bool:
    full_old = _safe_path(base_dir, old_path)
    if not full_old or not os.path.exists(full_old):
        return False
    new_path = os.path.join(os.path.dirname(full_old), new_name)
    full_new = _safe_path(base_dir, os.path.relpath(new_path, base_dir))
    if not full_new:
        return False
    os.rename(full_old, full_new)
    return True


def copy_item(src: str, dst: str, base_dir: str = WEB_ROOT) -> bool:
    full_src = _safe_path(base_dir, src)
    full_dst = _safe_path(base_dir, dst)
    if not full_src or not full_dst or not os.path.exists(full_src):
        return False
    if os.path.isdir(full_src):
        shutil.copytree(full_src, full_dst)
    else:
        shutil.copy2(full_src, full_dst)
    return True


def move_item(src: str, dst: str, base_dir: str = WEB_ROOT) -> bool:
    full_src = _safe_path(base_dir, src)
    full_dst = _safe_path(base_dir, dst)
    if not full_src or not full_dst:
        return False
    shutil.move(full_src, full_dst)
    return True


def change_permissions(path: str, mode: str, base_dir: str = WEB_ROOT) -> bool:
    full_path = _safe_path(base_dir, path)
    if not full_path or not os.path.exists(full_path):
        return False
    os.chmod(full_path, int(mode, 8))
    return True


def compress(paths: list[str], output: str, base_dir: str = WEB_ROOT) -> bool:
    full_output = _safe_path(base_dir, output)
    if not full_output:
        return False
    with zipfile.ZipFile(full_output, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            full_p = _safe_path(base_dir, p)
            if full_p and os.path.exists(full_p):
                if os.path.isdir(full_p):
                    for root, dirs, files in os.walk(full_p):
                        for f in files:
                            fp = os.path.join(root, f)
                            zf.write(fp, os.path.relpath(fp, os.path.dirname(full_p)))
                else:
                    zf.write(full_p, os.path.basename(full_p))
    return True


def extract(archive_path: str, dest_dir: str, base_dir: str = WEB_ROOT) -> bool:
    full_archive = _safe_path(base_dir, archive_path)
    full_dest = _safe_path(base_dir, dest_dir)
    if not full_archive or not full_dest:
        return False
    with zipfile.ZipFile(full_archive, "r") as zf:
        zf.extractall(full_dest)
    return True
