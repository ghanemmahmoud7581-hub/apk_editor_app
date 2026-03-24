"""
StorageManager
--------------
Bridges Python file-system calls with Android's scoped-storage model.

On Android 10+ (API 29+) apps must use:
  • MediaStore API  – for media files
  • SAF (Storage Access Framework) – for arbitrary files
  • getExternalFilesDir() – for app-private external storage (no permission needed)

Flet exposes file_picker which internally uses SAF on Android, so we
delegate all "open" operations through ft.FilePicker.
"""
import os
import json
import flet as ft
from pathlib import Path
from typing import Optional, Callable


# App-private external directory (always writable, no permission required)
APP_DIR = Path("/sdcard/Android/data/com.apkeditor.app/files")


class StorageManager:
    def __init__(self, page: ft.Page):
        self.page = page
        self._ensure_dirs()

        # ── Flet FilePicker (uses Android SAF under the hood) ──────────────
        self._file_picker = ft.FilePicker()
        self._dir_picker  = ft.FilePicker()
        page.overlay.extend([self._file_picker, self._dir_picker])

    # ── Directory helpers ──────────────────────────────────────────────────

    def _ensure_dirs(self):
        for sub in ["apks", "output", "invoices", "temp"]:
            (APP_DIR / sub).mkdir(parents=True, exist_ok=True)

    @property
    def apk_dir(self)   -> Path: return APP_DIR / "apks"
    @property
    def output_dir(self)-> Path: return APP_DIR / "output"
    @property
    def invoice_dir(self)-> Path: return APP_DIR / "invoices"
    @property
    def temp_dir(self)  -> Path: return APP_DIR / "temp"

    # ── File picker wrappers ───────────────────────────────────────────────

    def pick_apk(self, on_result: Callable):
        """Open SAF picker filtered to APK files."""
        self._file_picker.on_result = lambda e: on_result(
            e.files[0].path if e.files else None
        )
        self._file_picker.pick_files(
            dialog_title="اختر ملف APK",
            allowed_extensions=["apk", "xapk", "apks"],
            allow_multiple=False,
        )

    def pick_any_file(self, on_result: Callable, extensions: Optional[list] = None):
        self._file_picker.on_result = lambda e: on_result(
            e.files[0].path if e.files else None
        )
        self._file_picker.pick_files(
            dialog_title="اختر ملفاً",
            allowed_extensions=extensions,
            allow_multiple=False,
        )

    def save_file(self, file_name: str, on_result: Callable):
        self._file_picker.on_result = lambda e: on_result(e.path)
        self._file_picker.save_file(
            dialog_title="حفظ الملف",
            file_name=file_name,
        )

    def pick_directory(self, on_result: Callable):
        self._dir_picker.on_result = lambda e: on_result(e.path)
        self._dir_picker.get_directory_path(dialog_title="اختر مجلداً")

    # ── JSON helpers ───────────────────────────────────────────────────────

    def save_invoice(self, invoice_data: dict, filename: str = "invoice.json") -> Path:
        path = self.invoice_dir / filename
        path.write_text(json.dumps(invoice_data, ensure_ascii=False, indent=2))
        return path

    def load_invoice(self, filename: str) -> Optional[dict]:
        path = self.invoice_dir / filename
        if path.exists():
            return json.loads(path.read_text())
        return None

    def list_invoices(self) -> list[Path]:
        return sorted(self.invoice_dir.glob("*.json"), reverse=True)

    # ── Asset access ───────────────────────────────────────────────────────

    def get_apk_asset(self, apk_path: str, asset_name: str) -> Optional[bytes]:
        """
        Extract a single asset from an APK (ZIP) by name.
        Returns raw bytes or None.
        """
        import zipfile
        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                # Assets live under  assets/<name>
                targets = [
                    f"assets/{asset_name}",
                    asset_name,
                ]
                for t in targets:
                    if t in z.namelist():
                        return z.read(t)
        except Exception as e:
            print(f"[StorageManager] get_apk_asset error: {e}")
        return None

    def list_apk_assets(self, apk_path: str) -> list[str]:
        """List all entries inside the APK."""
        import zipfile
        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                return z.namelist()
        except Exception as e:
            print(f"[StorageManager] list_apk_assets error: {e}")
            return []
