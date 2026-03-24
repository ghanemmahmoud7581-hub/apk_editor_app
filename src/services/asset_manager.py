"""
AssetManager
------------
Manages the relationship between the app and Android's asset system.

Android Asset Architecture:
┌──────────────────────────────────────────────────────────┐
│  APK File (ZIP)                                          │
│  ├── assets/          ← raw assets (AssetManager API)   │
│  ├── res/             ← compiled resources (R.java)      │
│  │   ├── drawable/                                       │
│  │   ├── layout/                                         │
│  │   └── values/                                         │
│  ├── AndroidManifest.xml  (binary XML)                   │
│  ├── classes.dex                                         │
│  └── lib/                                                │
│       ├── arm64-v8a/                                     │
│       ├── armeabi-v7a/                                   │
│       └── x86_64/                                        │
└──────────────────────────────────────────────────────────┘

Our app (APK Editor Pro) needs to read ANOTHER app's assets.
Since Android 10+, direct file access is restricted.
Solution: User selects the target APK via SAF → we parse it as ZIP.
"""
from pathlib import Path
from typing import Optional, Iterator
import zipfile
import base64


# MIME type map for display
MIME_TYPES: dict[str, str] = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "xml": "text/xml",
    "json": "application/json",
    "txt": "text/plain",
    "html": "text/html",
    "css": "text/css",
    "js": "application/javascript",
    "ttf": "font/ttf",
    "otf": "font/otf",
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "ogg": "audio/ogg",
    "so": "application/octet-stream",
    "dex": "application/octet-stream",
}

# Categories for the UI tree
ASSET_CATEGORIES = {
    "🖼️ صور":   ["png", "jpg", "jpeg", "webp", "gif", "bmp", "svg"],
    "📄 XML":   ["xml"],
    "📋 JSON":  ["json"],
    "🔤 نصوص": ["txt", "html", "css", "js", "md", "properties"],
    "🔤 خطوط": ["ttf", "otf", "woff", "woff2"],
    "🎵 صوت":  ["mp3", "ogg", "wav", "flac", "aac"],
    "🎬 فيديو":["mp4", "webm", "mkv"],
    "📦 ثنائي":["so", "dex", "bin", "dat"],
}


class AssetManager:
    """
    Reads assets from a target APK (which is just a ZIP file).
    Works entirely in user-space — no root, no special Android APIs.
    The user must select the APK via SAF (ft.FilePicker) first.
    """

    def __init__(self, apk_path: str):
        self.apk_path = apk_path
        self._cache: dict[str, bytes] = {}  # entry_name → bytes

    # ── Listing ─────────────────────────────────────────────────────────────

    def all_entries(self) -> list[str]:
        try:
            with zipfile.ZipFile(self.apk_path) as z:
                return z.namelist()
        except Exception as e:
            print(f"[AssetManager] all_entries: {e}")
            return []

    def assets_only(self) -> list[str]:
        """Only entries under assets/"""
        return [e for e in self.all_entries() if e.startswith("assets/")]

    def res_entries(self) -> list[str]:
        return [e for e in self.all_entries() if e.startswith("res/")]

    def categorize(self) -> dict[str, list[str]]:
        """Group all entries by category for the UI tree."""
        result: dict[str, list[str]] = {cat: [] for cat in ASSET_CATEGORIES}
        result["📁 أخرى"] = []

        for entry in self.all_entries():
            ext = entry.rsplit(".", 1)[-1].lower() if "." in entry else ""
            placed = False
            for cat, exts in ASSET_CATEGORIES.items():
                if ext in exts:
                    result[cat].append(entry)
                    placed = True
                    break
            if not placed:
                result["📁 أخرى"].append(entry)

        # Remove empty categories
        return {k: v for k, v in result.items() if v}

    # ── Reading ──────────────────────────────────────────────────────────────

    def read(self, entry: str) -> Optional[bytes]:
        if entry in self._cache:
            return self._cache[entry]
        try:
            with zipfile.ZipFile(self.apk_path) as z:
                if entry in z.namelist():
                    data = z.read(entry)
                    self._cache[entry] = data
                    return data
        except Exception as e:
            print(f"[AssetManager] read {entry}: {e}")
        return None

    def read_text(self, entry: str) -> Optional[str]:
        data = self.read(entry)
        if data is None:
            return None
        # Try UTF-8, fall back to latin-1
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return f"[Cannot decode – {len(data)} bytes]"

    def read_as_data_url(self, entry: str) -> Optional[str]:
        """Return a base64 data-URL for displaying images in Flet."""
        data = self.read(entry)
        if data is None:
            return None
        ext = entry.rsplit(".", 1)[-1].lower() if "." in entry else "bin"
        mime = MIME_TYPES.get(ext, "application/octet-stream")
        b64 = base64.b64encode(data).decode()
        return f"data:{mime};base64,{b64}"

    def get_mime_type(self, entry: str) -> str:
        ext = entry.rsplit(".", 1)[-1].lower() if "." in entry else ""
        return MIME_TYPES.get(ext, "application/octet-stream")

    def is_image(self, entry: str) -> bool:
        ext = entry.rsplit(".", 1)[-1].lower() if "." in entry else ""
        return ext in ASSET_CATEGORIES.get("🖼️ صور", [])

    def is_text(self, entry: str) -> bool:
        ext = entry.rsplit(".", 1)[-1].lower() if "." in entry else ""
        text_exts = set()
        for cat in ["📄 XML", "📋 JSON", "🔤 نصوص"]:
            text_exts.update(ASSET_CATEGORIES.get(cat, []))
        return ext in text_exts

    # ── Search ───────────────────────────────────────────────────────────────

    def search(self, query: str, text_only: bool = True) -> Iterator[tuple[str, list[int]]]:
        """
        Yield (entry_name, [matching_line_numbers]) for entries containing query.
        If text_only=True, skips binary files.
        """
        q = query.lower()
        for entry in self.all_entries():
            if text_only and not self.is_text(entry):
                continue
            text = self.read_text(entry)
            if not text:
                continue
            lines = [
                i + 1
                for i, line in enumerate(text.splitlines())
                if q in line.lower()
            ]
            if lines:
                yield entry, lines

    # ── Stats ────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        cats = self.categorize()
        entries = self.all_entries()
        total_size = 0
        try:
            with zipfile.ZipFile(self.apk_path) as z:
                total_size = sum(info.compress_size for info in z.infolist())
        except Exception:
            pass

        return {
            "total_entries": len(entries),
            "compressed_size_kb": round(total_size / 1024, 1),
            "categories": {cat: len(items) for cat, items in cats.items()},
        }
