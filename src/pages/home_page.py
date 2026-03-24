"""HomePage – Dashboard / APK loader."""
import flet as ft
from pathlib import Path


class HomePage:
    def __init__(self, page, app_state, perm_manager, storage_manager):
        self.page = page
        self.state = app_state
        self.perms = perm_manager
        self.storage = storage_manager
        self._info_col = ft.Column(spacing=6)

    def build(self):
        drop_zone = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.UPLOAD_FILE, size=64, color="#58a6ff"),
                    ft.Text("اسحب ملف APK هنا", size=18, color="#8b949e"),
                    ft.Text("أو", size=14, color="#8b949e"),
                    ft.ElevatedButton(
                        "📂 اختيار ملف APK",
                        on_click=self._pick_apk,
                        bgcolor="#58a6ff",
                        color="#0d1117",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            alignment=ft.Alignment.CENTER,
            bgcolor="#161b22",
            border=ft.border.all(2, "#30363d"),
            border_radius=12,
            padding=40,
            width=500,
        )

        perm_status = self._build_permissions_widget()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("🏠 الرئيسية", size=22, weight=ft.FontWeight.BOLD, color="#e6edf3"),
                    ft.Divider(color="#30363d"),
                    perm_status,
                    ft.Divider(color="#30363d"),
                    drop_zone,
                    self._info_col,
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
            expand=True,
        )

    def _build_permissions_widget(self):
        status = self.perms.get_status()
        chips = []
        labels = {
            "storage": "التخزين",
            "media_location": "الوسائط",
            "manage_files": "إدارة الملفات",
            "camera": "الكاميرا",
            "notifications": "الإشعارات",
        }
        for key, label in labels.items():
            granted = status.get(key, False)
            chips.append(
                ft.Chip(
                    label=ft.Text(f"{'✅' if granted else '❌'} {label}"),
                    bgcolor="#1c2128" if granted else "#2d1b1b",
                )
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("🔐 الصلاحيات", size=14, color="#8b949e", weight=ft.FontWeight.BOLD),
                            ft.TextButton(
                                "تحديث",
                                on_click=lambda e: self.perms.request_all_permissions(),
                                style=ft.ButtonStyle(color="#58a6ff"),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(chips, wrap=True, spacing=6),
                ],
                spacing=8,
            ),
            bgcolor="#161b22",
            border=ft.border.all(1, "#30363d"),
            border_radius=8,
            padding=12,
        )

    def _pick_apk(self, e):
        if not self.perms.has_storage():
            self.perms.request_storage(on_done=lambda ok: self._pick_apk(None) if ok else None)
            return
        self.storage.pick_apk(self._on_apk_selected)

    def _on_apk_selected(self, path: str):
        if not path:
            return
        self.state["current_apk"] = path
        p = Path(path)
        size_mb = p.stat().st_size / (1024 * 1024) if p.exists() else 0

        # List entries
        entries = self.storage.list_apk_assets(path)
        assets  = [e for e in entries if e.startswith("assets/")]

        self._info_col.controls.clear()
        self._info_col.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("✅ تم تحميل الملف", color="#3fb950", weight=ft.FontWeight.BOLD),
                        ft.Text(f"الاسم: {p.name}", color="#e6edf3"),
                        ft.Text(f"الحجم: {size_mb:.2f} MB", color="#e6edf3"),
                        ft.Text(f"إجمالي المداخل: {len(entries)}", color="#e6edf3"),
                        ft.Text(f"الأصول (assets): {len(assets)}", color="#58a6ff"),
                        ft.Divider(color="#30363d"),
                        ft.Text("عينة من الأصول:", color="#8b949e", size=12),
                        ft.Column(
                            [ft.Text(f"  • {a}", size=11, color="#8b949e") for a in assets[:10]],
                            spacing=2,
                        ),
                    ],
                    spacing=6,
                ),
                bgcolor="#161b22",
                border=ft.border.all(1, "#3fb950"),
                border_radius=8,
                padding=16,
            )
        )
        self.page.update()
