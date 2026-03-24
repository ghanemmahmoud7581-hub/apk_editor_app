"""SettingsPage – App settings and permission management."""
import flet as ft


class SettingsPage:
    def __init__(self, page, perm_manager):
        self.page = page
        self.perms = perm_manager

    def build(self):
        def section(title, controls):
            return ft.Container(
                content=ft.Column(
                    [ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color="#8b949e")] + controls,
                    spacing=8,
                ),
                bgcolor="#161b22",
                border=ft.border.all(1, "#30363d"),
                border_radius=8,
                padding=16,
            )

        perm_items = []
        labels = {
            "storage": ("التخزين", "قراءة/كتابة ملفات APK"),
            "manage_files": ("إدارة الملفات", "وصول كامل للتخزين الخارجي"),
            "media_location": ("الوسائط", "الصور والفيديو"),
            "camera": ("الكاميرا", "مسح QR"),
            "notifications": ("الإشعارات", "إشعارات التطبيق"),
        }
        status = self.perms.get_status()
        for key, (label, desc) in labels.items():
            granted = status.get(key, False)
            perm_items.append(
                ft.ListTile(
                    leading=ft.Icon(
                        ft.icons.CHECK_CIRCLE if granted else ft.icons.CANCEL,
                        color="#3fb950" if granted else "#f85149",
                    ),
                    title=ft.Text(label, color="#e6edf3"),
                    subtitle=ft.Text(desc, size=11, color="#8b949e"),
                    trailing=ft.TextButton(
                        "منح" if not granted else "ممنوحة",
                        disabled=granted,
                        on_click=lambda e, k=key: self.perms.request_all_permissions(),
                        style=ft.ButtonStyle(color="#58a6ff"),
                    ),
                )
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("⚙️ الإعدادات", size=22, weight=ft.FontWeight.BOLD, color="#e6edf3"),
                    ft.Divider(color="#30363d"),
                    section("🔐 الصلاحيات", perm_items),
                    section("ℹ️ حول التطبيق", [
                        ft.Text("APK Editor Pro", color="#58a6ff", size=16, weight=ft.FontWeight.BOLD),
                        ft.Text("الإصدار: 1.0.0", color="#8b949e"),
                        ft.Text("Flet + Python for Android", color="#8b949e"),
                    ]),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=16,
            ),
            padding=20,
            expand=True,
        )
