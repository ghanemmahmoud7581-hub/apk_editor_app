"""
EditorPage (enhanced)
─────────────────────
Full APK asset browser with:
  • Categorized tree view
  • Text / binary / image preview
  • In-entry search
  • Save patch back to APK
"""
import flet as ft
from services.apk_service   import APKService
from services.asset_manager import AssetManager
from pathlib import Path


class EditorPage:
    def __init__(self, page: ft.Page, app_state: dict, storage_manager):
        self.page    = page
        self.state   = app_state
        self.storage = storage_manager

        self._apk_svc: APKService | None   = None
        self._assets:  AssetManager | None = None
        self._selected_entry: str | None   = None

        # UI refs
        self._tree_col     = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self._search_f     = ft.TextField(
            label="🔍 بحث في المداخل", expand=True,
            bgcolor="#161b22", border_color="#30363d", color="#e6edf3",
            on_change=self._on_search_change,
        )
        self._preview_area = ft.Container(expand=True, bgcolor="#0d1117")
        self._info_bar     = ft.Text("", size=11, color="#8b949e", italic=True)
        self._stats_row    = ft.Row([], spacing=12, wrap=True)

    # ── Build ──────────────────────────────────────────────────────────────

    def build(self) -> ft.Control:
        toolbar = ft.Row(
            [
                ft.ElevatedButton(
                    "📂 تحميل APK",
                    bgcolor="#58a6ff", color="#0d1117",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=self._load_apk,
                ),
                ft.OutlinedButton(
                    "🔍 بحث نصي",
                    style=ft.ButtonStyle(side=ft.BorderSide(color="#8b949e"), color="#8b949e"),
                    on_click=self._open_search_dialog,
                ),
                ft.OutlinedButton(
                    "📊 إحصائيات",
                    style=ft.ButtonStyle(side=ft.BorderSide(color="#d29922"), color="#d29922"),
                    on_click=self._show_stats,
                ),
            ],
            spacing=8, wrap=True,
        )

        sidebar = ft.Container(
            content=ft.Column(
                [self._search_f,
                 ft.Divider(color="#30363d", height=1),
                 self._tree_col],
                spacing=6, expand=True,
            ),
            width=270,
            bgcolor="#161b22",
            border=ft.border.all(1, "#30363d"),
            border_radius=8,
            padding=8,
        )

        preview_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Row([ft.Icon(ft.icons.DESCRIPTION_OUTLINED, color="#8b949e", size=14),
                            self._info_bar], spacing=6),
                    ft.Divider(color="#30363d", height=1),
                    self._preview_area,
                ],
                spacing=6, expand=True,
            ),
            expand=True,
            bgcolor="#0d1117",
            border=ft.border.all(1, "#30363d"),
            border_radius=8,
            padding=12,
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("✏️ محرر APK", size=22, weight=ft.FontWeight.BOLD, color="#e6edf3"),
                    toolbar,
                    self._stats_row,
                    ft.Divider(color="#30363d"),
                    ft.Row(
                        [sidebar, preview_panel],
                        expand=True, spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                ],
                spacing=10, expand=True,
            ),
            padding=20, expand=True,
        )

    # ── Load APK ───────────────────────────────────────────────────────────

    def _load_apk(self, e=None):
        existing = self.state.get("current_apk")
        if existing:
            self._init_services(existing)
        else:
            self.storage.pick_apk(lambda p: self._init_services(p) if p else None)

    def _init_services(self, path: str):
        if not path:
            return
        self.state["current_apk"] = path
        self._apk_svc = APKService(path, self.storage.temp_dir)
        self._assets  = AssetManager(path)
        self._render_tree()
        self._render_stats()
        self.page.update()

    # ── Tree rendering ─────────────────────────────────────────────────────

    def _render_tree(self, filter_q: str = ""):
        self._tree_col.controls.clear()
        if not self._assets:
            return
        cats = self._assets.categorize()
        for cat, entries in cats.items():
            filtered = [e for e in entries if filter_q.lower() in e.lower()] if filter_q else entries
            if not filtered:
                continue
            # Category header
            self._tree_col.controls.append(
                ft.Container(
                    content=ft.Text(f"{cat}  ({len(filtered)})", size=12,
                                    color="#8b949e", weight=ft.FontWeight.BOLD),
                    padding=ft.padding.only(top=8, bottom=2, left=4),
                )
            )
            for entry in filtered[:80]:
                is_sel = entry == self._selected_entry
                self._tree_col.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(self._icon_for(entry), size=13),
                                ft.Text(
                                    entry.split("/")[-1],
                                    size=11,
                                    color="#e6edf3" if is_sel else "#c9d1d9",
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                ),
                            ],
                            spacing=6,
                        ),
                        bgcolor="#2d333b" if is_sel else "transparent",
                        border_radius=4,
                        padding=ft.padding.symmetric(vertical=4, horizontal=6),
                        on_click=lambda e2, ent=entry: self._open_entry(ent),
                        tooltip=entry,
                    )
                )
            if len(filtered) > 80:
                self._tree_col.controls.append(
                    ft.Text(f"  … و{len(filtered)-80} آخرون", size=10, color="#8b949e")
                )

    def _icon_for(self, entry: str) -> str:
        ext = entry.rsplit(".", 1)[-1].lower() if "." in entry else ""
        return {
            "xml":"📄","json":"📋","txt":"📃","html":"🌐","css":"🎨","js":"⚡",
            "png":"🖼️","jpg":"🖼️","webp":"🖼️","gif":"🖼️",
            "ttf":"🔤","otf":"🔤","mp3":"🎵","ogg":"🎵","mp4":"🎬",
            "so":"📦","dex":"🔩","properties":"📝","smali":"⚙️",
        }.get(ext, "📁")

    # ── Open entry ─────────────────────────────────────────────────────────

    def _open_entry(self, entry: str):
        if not self._assets:
            return
        self._selected_entry = entry
        data = self._assets.read(entry)
        size_str = f"{len(data):,} bytes" if data else "—"
        self._info_bar.value = f"{entry}   |   {size_str}"
        self._render_tree(self._search_f.value)

        ext = entry.rsplit(".", 1)[-1].lower() if "." in entry else ""
        if self._assets.is_image(entry):
            self._show_image(entry)
        elif self._assets.is_text(entry) or ext in ("xml","json","smali","properties","html","css","js","txt","md"):
            self._show_text(entry)
        else:
            self._show_binary(entry, data)

        self.page.update()

    def _show_text(self, entry: str):
        text = self._assets.read_text(entry) or ""
        editor = ft.TextField(
            value=text, multiline=True, min_lines=28, expand=True,
            bgcolor="#0d1117", border_color="#30363d", color="#e6edf3",
            text_style=ft.TextStyle(font_family="monospace", size=12),
        )
        save_btn = ft.ElevatedButton(
            "💾 حفظ التعديل",
            bgcolor="#3fb950", color="#0d1117",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=lambda e, ent=entry: self._save_patch(ent, editor.value),
        )
        self._preview_area.content = ft.Column(
            [ft.Row([save_btn]), editor], spacing=8, expand=True,
        )

    def _show_image(self, entry: str):
        data_url = self._assets.read_as_data_url(entry)
        if data_url:
            self._preview_area.content = ft.Column(
                [
                    ft.Text("معاينة الصورة", size=12, color="#8b949e"),
                    ft.Image(src=data_url, fit=ft.ImageFit.CONTAIN, expand=True),
                ],
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        else:
            self._preview_area.content = ft.Text("تعذّر تحميل الصورة", color="#f85149")

    def _show_binary(self, entry: str, data):
        size = len(data) if data else 0
        self._preview_area.content = ft.Column(
            [
                ft.Icon(ft.icons.INSERT_DRIVE_FILE, size=64, color="#30363d"),
                ft.Text("ملف ثنائي", size=16, color="#8b949e"),
                ft.Text(f"الحجم: {size:,} bytes", color="#8b949e"),
                ft.ElevatedButton(
                    "📤 استخراج",
                    bgcolor="#58a6ff", color="#0d1117",
                    on_click=lambda e, ent=entry: self._extract_entry(ent),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )

    # ── Actions ────────────────────────────────────────────────────────────

    def _save_patch(self, entry: str, text: str):
        if not self._apk_svc:
            return
        ok = self._apk_svc.patch_entry(entry, text.encode("utf-8"))
        self._snack("✅ تم الحفظ" if ok else "❌ فشل", "#3fb950" if ok else "#f85149")

    def _extract_entry(self, entry: str):
        if not self._assets:
            return
        name = entry.split("/")[-1]
        def on_save(path):
            if path and self._apk_svc:
                self._apk_svc.extract_entry(entry, Path(path))
                self._snack(f"✅ تم: {name}", "#3fb950")
        self.storage.save_file(name, on_save)

    # ── Search dialog ──────────────────────────────────────────────────────

    def _open_search_dialog(self, e=None):
        if not self._assets:
            self._snack("حمّل APK أولاً", "#f85149")
            return
        query_f     = ft.TextField(label="ابحث في محتوى الملفات", autofocus=True,
                                   bgcolor="#161b22", border_color="#30363d", color="#e6edf3")
        results_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, spacing=2)

        def do_search(e):
            results_col.controls.clear()
            q = query_f.value.strip()
            if not q:
                return
            found = 0
            for entry, lines in self._assets.search(q):
                found += 1
                results_col.controls.append(
                    ft.ListTile(
                        title=ft.Text(entry, size=12, color="#58a6ff"),
                        subtitle=ft.Text(f"أسطر: {lines[:5]}", size=11, color="#8b949e"),
                        dense=True,
                        on_click=lambda e2, ent=entry: (
                            self._open_entry(ent),
                            setattr(self.page.dialog, "open", False),
                            self.page.update(),
                        ),
                    )
                )
                if found >= 30:
                    break
            if not found:
                results_col.controls.append(ft.Text("لا نتائج", color="#8b949e"))
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("🔍 بحث في APK", color="#e6edf3"),
            bgcolor="#161b22",
            content=ft.Column(
                [query_f,
                 ft.ElevatedButton("بحث", on_click=do_search,
                                   bgcolor="#58a6ff", color="#0d1117"),
                 results_col],
                spacing=10, tight=True,
            ),
            actions=[ft.TextButton(
                "إغلاق",
                on_click=lambda e: setattr(self.page.dialog, "open", False) or self.page.update(),
            )],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # ── Stats ──────────────────────────────────────────────────────────────

    def _render_stats(self):
        if not self._assets:
            return
        s = self._assets.stats()
        chips = [self._chip(f"📦 {s['total_entries']} مدخل"),
                 self._chip(f"💾 {s['compressed_size_kb']} KB")]
        chips += [self._chip(f"{cat} {cnt}") for cat, cnt in list(s["categories"].items())[:4]]
        self._stats_row.controls = chips

    def _show_stats(self, e=None):
        if not self._assets:
            self._snack("حمّل APK أولاً", "#f85149")
            return
        s = self._assets.stats()
        rows = [
            ft.DataRow(cells=[ft.DataCell(ft.Text(k, color="#e6edf3")),
                               ft.DataCell(ft.Text(str(v), color="#58a6ff"))])
            for k, v in s["categories"].items()
        ]
        dlg = ft.AlertDialog(
            title=ft.Text("📊 إحصائيات APK", color="#e6edf3"),
            bgcolor="#161b22",
            content=ft.DataTable(
                columns=[ft.DataColumn(ft.Text("الفئة", color="#8b949e")),
                         ft.DataColumn(ft.Text("العدد",  color="#8b949e"))],
                rows=rows,
            ),
            actions=[ft.TextButton(
                "إغلاق",
                on_click=lambda e: setattr(self.page.dialog, "open", False) or self.page.update(),
            )],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _chip(self, label: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(label, size=11, color="#8b949e"),
            bgcolor="#161b22",
            border=ft.border.all(1, "#30363d"),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

    def _on_search_change(self, e):
        self._render_tree(e.control.value)
        self.page.update()

    def _snack(self, msg: str, color: str = "#58a6ff"):
        self.page.snack_bar = ft.SnackBar(ft.Text(msg, color="#e6edf3"), bgcolor="#161b22")
        self.page.snack_bar.open = True
        self.page.update()
