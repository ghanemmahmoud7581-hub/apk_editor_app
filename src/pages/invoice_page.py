"""
InvoicePage
-----------
Create, preview, print, and export invoices.
Works on Android via PrintService → Android PrintManager bridge.
"""
import flet as ft
from datetime import datetime
from services.print_service import PrintService


class InvoicePage:
    def __init__(self, page: ft.Page, app_state: dict, storage_manager):
        self.page = page
        self.state = app_state
        self.storage = storage_manager
        self.print_svc = PrintService(page, storage_manager)

        self._items: list[dict] = []
        self._inv_no_field = ft.TextField(
            value="INV-0001", label="رقم الفاتورة", width=160,
            bgcolor="#161b22", border_color="#30363d", color="#e6edf3",
        )
        self._client_field = ft.TextField(
            label="اسم العميل", expand=True,
            bgcolor="#161b22", border_color="#30363d", color="#e6edf3",
        )
        self._notes_field = ft.TextField(
            label="ملاحظات", multiline=True, min_lines=2,
            bgcolor="#161b22", border_color="#30363d", color="#e6edf3",
        )
        self._items_col = ft.Column(spacing=6)
        self._total_text = ft.Text("الإجمالي: 0.00 DZD", size=18, weight=ft.FontWeight.BOLD,
                                   color="#58a6ff")

    # ── Build ──────────────────────────────────────────────────────────────

    def build(self) -> ft.Control:
        self._refresh_items_ui()

        action_bar = ft.Row(
            [
                ft.ElevatedButton(
                    "🖨️ طباعة",
                    on_click=self._on_print,
                    bgcolor="#58a6ff", color="#0d1117",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                ),
                ft.OutlinedButton(
                    "💾 تصدير PDF",
                    on_click=self._on_export_pdf,
                    style=ft.ButtonStyle(
                        side=ft.BorderSide(color="#3fb950"),
                        color="#3fb950",
                    ),
                ),
                ft.OutlinedButton(
                    "📤 مشاركة",
                    on_click=self._on_share,
                    style=ft.ButtonStyle(
                        side=ft.BorderSide(color="#d29922"),
                        color="#d29922",
                    ),
                ),
                ft.OutlinedButton(
                    "💾 حفظ JSON",
                    on_click=self._on_save,
                    style=ft.ButtonStyle(
                        side=ft.BorderSide(color="#8b949e"),
                        color="#8b949e",
                    ),
                ),
            ],
            wrap=True, spacing=8,
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("📋 الفاتورة", size=22, weight=ft.FontWeight.BOLD, color="#e6edf3"),
                    ft.Divider(color="#30363d"),
                    ft.Row([self._inv_no_field, self._client_field], spacing=12),
                    self._notes_field,
                    ft.Divider(color="#30363d"),
                    ft.Row(
                        [
                            ft.Text("📦 الأصناف", size=16, color="#e6edf3", weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                ft.icons.ADD_CIRCLE_OUTLINE,
                                icon_color="#3fb950",
                                tooltip="إضافة صنف",
                                on_click=self._add_item,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self._items_col,
                    ft.Divider(color="#30363d"),
                    self._total_text,
                    ft.Divider(color="#30363d"),
                    action_bar,
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=12,
                expand=True,
            ),
            padding=20,
            expand=True,
        )

    # ── Items management ───────────────────────────────────────────────────

    def _add_item(self, e=None):
        idx = len(self._items)
        item = {"name": "", "qty": 1, "price": 0.0}
        self._items.append(item)
        self._items_col.controls.append(self._item_row(idx, item))
        self.page.update()

    def _item_row(self, idx: int, item: dict) -> ft.Control:
        name_f  = ft.TextField(
            value=item["name"], label="الصنف", expand=True,
            bgcolor="#161b22", border_color="#30363d", color="#e6edf3",
            on_change=lambda e, i=idx: self._update_item(i, "name", e.control.value),
        )
        qty_f   = ft.TextField(
            value=str(item["qty"]), label="الكمية", width=80, keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#161b22", border_color="#30363d", color="#e6edf3",
            on_change=lambda e, i=idx: self._update_item(i, "qty", e.control.value),
        )
        price_f = ft.TextField(
            value=str(item["price"]), label="السعر", width=120, keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#161b22", border_color="#30363d", color="#e6edf3",
            on_change=lambda e, i=idx: self._update_item(i, "price", e.control.value),
        )
        del_btn = ft.IconButton(
            ft.icons.DELETE_OUTLINE, icon_color="#f85149",
            on_click=lambda e, i=idx: self._remove_item(i),
        )
        return ft.Row([name_f, qty_f, price_f, del_btn], spacing=8)

    def _update_item(self, idx: int, key: str, val: str):
        try:
            if key == "qty":
                self._items[idx][key] = int(val or 0)
            elif key == "price":
                self._items[idx][key] = float(val or 0)
            else:
                self._items[idx][key] = val
        except ValueError:
            pass
        self._update_total()

    def _remove_item(self, idx: int):
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._refresh_items_ui()
            self.page.update()

    def _refresh_items_ui(self):
        self._items_col.controls.clear()
        for i, item in enumerate(self._items):
            self._items_col.controls.append(self._item_row(i, item))
        self._update_total()

    def _update_total(self):
        total = sum(i["qty"] * i["price"] for i in self._items)
        self._total_text.value = f"الإجمالي: {total:,.2f} DZD"
        self.page.update()

    # ── Invoice data ───────────────────────────────────────────────────────

    def _build_data(self) -> dict:
        return {
            "invoice_no": self._inv_no_field.value or "INV-0001",
            "client":     self._client_field.value or "",
            "notes":      self._notes_field.value or "",
            "date":       datetime.now().strftime("%Y-%m-%d %H:%M"),
            "items":      list(self._items),
            "currency":   "DZD",
        }

    # ── Actions ────────────────────────────────────────────────────────────

    def _on_print(self, e):
        if not self._items:
            self._snack("أضف صنفاً واحداً على الأقل", "#f85149")
            return
        self.print_svc.print_invoice(self._build_data())
        self._snack("تم إرسال الفاتورة للطابعة ✅", "#3fb950")

    def _on_export_pdf(self, e):
        data = self._build_data()
        inv_no = data["invoice_no"].replace("/", "-")

        def on_save(path):
            if path:
                ok = self.print_svc.export_pdf(data, path)
                self._snack("✅ تم التصدير" if ok else "⚠️ تم الحفظ بصيغة HTML", "#d29922")

        self.storage.save_file(f"{inv_no}.pdf", on_save)

    def _on_share(self, e):
        self.print_svc.share_invoice(self._build_data())

    def _on_save(self, e):
        data = self._build_data()
        path = self.storage.save_invoice(data, f"{data['invoice_no']}.json")
        self._snack(f"✅ تم الحفظ: {path.name}", "#3fb950")

    def _snack(self, msg: str, color: str = "#58a6ff"):
        self.page.snack_bar = ft.SnackBar(
            ft.Text(msg, color="#e6edf3"),
            bgcolor="#161b22",
        )
        self.page.snack_bar.open = True
        self.page.update()
