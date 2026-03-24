"""
PrintService
------------
Handles invoice rendering, PDF export, and Android PrintManager integration.

Android printing flow:
  1. Build an HTML string representing the invoice.
  2. Pass it to Android's WebView-based PrintDocumentAdapter via
     a Flet platform channel (page.invoke_method).
  3. Android shows the system print dialog (PDF / Wi-Fi printer / BT printer).

Fallback (desktop / debug):
  Use WeasyPrint or pdfkit to generate a PDF locally.
"""
import json
import flet as ft
from datetime import datetime
from pathlib import Path
from typing import Optional


class PrintService:
    def __init__(self, page: ft.Page, storage_manager=None):
        self.page = page
        self.storage = storage_manager

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def print_invoice(self, invoice_data: dict):
        """Trigger Android system print dialog for the given invoice."""
        html = self._build_html(invoice_data)
        self._invoke_android_print(html, job_name="فاتورة APK Editor")

    def export_pdf(self, invoice_data: dict, out_path: str) -> bool:
        """Export invoice to PDF file (fallback / desktop)."""
        html = self._build_html(invoice_data)
        try:
            import weasyprint
            weasyprint.HTML(string=html).write_pdf(out_path)
            return True
        except ImportError:
            # WeasyPrint not available on Android; save HTML instead
            Path(out_path.replace(".pdf", ".html")).write_text(html, encoding="utf-8")
            return False
        except Exception as e:
            print(f"[PrintService] export_pdf error: {e}")
            return False

    def share_invoice(self, invoice_data: dict):
        """Share invoice via Android share sheet."""
        html = self._build_html(invoice_data)
        tmp = Path("/tmp/invoice_share.html")
        tmp.write_text(html, encoding="utf-8")
        # Open HTML in browser / share
        self.page.launch_url(f"file://{tmp}")

    # ──────────────────────────────────────────────────────────────────────
    # Android bridge
    # ──────────────────────────────────────────────────────────────────────

    def _invoke_android_print(self, html: str, job_name: str):
        """
        Call into Android's PrintManager via Flet platform channel.
        The Java side (PrintBridge.java) registers the method handler.

        If the channel is unavailable (desktop / test), falls back to
        opening the HTML in the default browser.
        """
        try:
            # Flet 0.21+ supports invoke_method for platform channels
            self.page.invoke_method(
                "print_html",
                {"html": html, "job_name": job_name},
            )
        except AttributeError:
            # Fallback: open in browser for printing
            tmp = Path("/tmp/_invoice_print.html")
            tmp.write_text(html, encoding="utf-8")
            self.page.launch_url(f"file://{tmp}")

    # ──────────────────────────────────────────────────────────────────────
    # HTML builder
    # ──────────────────────────────────────────────────────────────────────

    def _build_html(self, data: dict) -> str:
        items_rows = ""
        total = 0.0
        for item in data.get("items", []):
            name  = item.get("name",  "—")
            qty   = item.get("qty",   1)
            price = item.get("price", 0.0)
            sub   = qty * price
            total += sub
            items_rows += f"""
            <tr>
              <td>{name}</td>
              <td style="text-align:center">{qty}</td>
              <td style="text-align:right">{price:,.2f}</td>
              <td style="text-align:right">{sub:,.2f}</td>
            </tr>"""

        date_str = data.get("date", datetime.now().strftime("%Y-%m-%d %H:%M"))
        inv_no   = data.get("invoice_no", "INV-0001")
        client   = data.get("client", "")
        notes    = data.get("notes", "")
        currency = data.get("currency", "DZD")

        return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Cairo', 'Arial', sans-serif;
    background: #fff;
    color: #1a1a1a;
    padding: 32px;
    font-size: 14px;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 3px solid #58a6ff;
    padding-bottom: 16px;
    margin-bottom: 24px;
  }}
  .logo {{ font-size: 24px; font-weight: 700; color: #58a6ff; }}
  .meta {{ text-align: left; color: #555; line-height: 1.8; }}
  .client-box {{
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 24px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
  }}
  th {{
    background: #0d1117;
    color: #fff;
    padding: 10px 12px;
    font-weight: 700;
  }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #e8ecf0; }}
  tr:hover td {{ background: #f6f8fa; }}
  .total-row td {{
    font-weight: 700;
    font-size: 16px;
    border-top: 2px solid #58a6ff;
    color: #58a6ff;
  }}
  .notes {{ color: #555; font-size: 13px; margin-top: 16px; }}
  .footer {{
    margin-top: 40px;
    text-align: center;
    font-size: 12px;
    color: #999;
    border-top: 1px solid #e8ecf0;
    padding-top: 12px;
  }}
  @media print {{
    body {{ padding: 16px; }}
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>
  <div class="header">
    <div class="logo">⚙️ APK Editor Pro</div>
    <div class="meta">
      <div><strong>رقم الفاتورة:</strong> {inv_no}</div>
      <div><strong>التاريخ:</strong> {date_str}</div>
    </div>
  </div>

  {"<div class='client-box'><strong>العميل:</strong> " + client + "</div>" if client else ""}

  <table>
    <thead>
      <tr>
        <th>الصنف</th>
        <th>الكمية</th>
        <th>السعر</th>
        <th>الإجمالي</th>
      </tr>
    </thead>
    <tbody>
      {items_rows}
      <tr class="total-row">
        <td colspan="3">الإجمالي الكلي</td>
        <td>{total:,.2f} {currency}</td>
      </tr>
    </tbody>
  </table>

  {"<div class='notes'><strong>ملاحظات:</strong> " + notes + "</div>" if notes else ""}

  <div class="footer">
    تم الإنشاء بواسطة APK Editor Pro — {date_str}
  </div>

  <div class="no-print" style="margin-top:24px; text-align:center;">
    <button onclick="window.print()"
      style="padding:10px 28px; background:#58a6ff; color:#fff;
             border:none; border-radius:6px; font-size:15px; cursor:pointer;">
      🖨️ طباعة
    </button>
  </div>
</body>
</html>"""
