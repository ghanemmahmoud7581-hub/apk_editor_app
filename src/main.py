"""
APK Editor - نسخة مع رفع الملفات ومؤشر تقدم
تعمل على Web و Windows و Android
"""
import flet as ft
import os
import zipfile
from pathlib import Path
import tempfile

def main(page: ft.Page):
    page.title = "APK Editor"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 800
    page.scroll = ft.ScrollMode.AUTO
    
    # التحقق من المنصة
    is_web = page.web
    
    # متغيرات الحالة
    current_apk_path = None
    current_apk_files = []
    current_apk_data = None  # لتخزين البيانات على الويب
    
    # عناصر واجهة المستخدم
    status_text = ft.Text("✅ جاهز", color="#57FF81")
    apk_name_text = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    apk_size_text = ft.Text("")
    files_count_text = ft.Text("")
    
    # قائمة الملفات
    files_list = ft.ListView(expand=True, spacing=5, height=450)
    
    # متغيرات لرفع الملفات
    file_picker = None
    prog_bars = {}
    
    def on_upload_progress(e: ft.FilePickerUploadEvent):
        """تحديث مؤشر التقدم أثناء الرفع"""
        if e.file_name in prog_bars:
            prog_bars[e.file_name].value = e.progress
            page.update()
    
    async def handle_files_pick(e):
        """معالجة اختيار الملفات"""
        nonlocal file_picker, current_apk_data
        
        # إنشاء FilePicker جديد لكل مرة
        file_picker = ft.FilePicker(on_upload=on_upload_progress)
        page.overlay.append(file_picker)
        page.update()
        
        try:
            if is_web:
                # على الويب: رفع الملف
                files = await file_picker.pick_files(allow_multiple=False)
                if files:
                    file = files[0]
                    status_text.value = "⏳ جاري رفع الملف..."
                    status_text.color = "#FFD857"
                    page.update()
                    
                    # عرض مؤشر تقدم
                    prog = ft.ProgressRing(value=0, bgcolor="#eeeeee", width=30, height=30)
                    prog_bars[file.name] = prog
                    
                    # رفع الملف
                    await file_picker.upload(
                        files=[
                            ft.FilePickerUploadFile(
                                name=file.name,
                                upload_url=page.get_upload_url(f"apk_files/{file.name}", 60),
                            )
                        ]
                    )
                    
                    # بعد الرفع، معالجة الملف
                    status_text.value = "✅ تم رفع الملف، جاري التحليل..."
                    page.update()
                    
                    # محاكاة معالجة الملف (على الويب يتم حفظه في الخادم)
                    process_web_file(file.name)
            else:
                # على سطح المكتب: اختيار ملف مباشر
                files = await file_picker.pick_files(allow_multiple=False)
                if files:
                    process_apk(files[0].path)
                    
        except Exception as e:
            status_text.value = f"❌ خطأ: {str(e)}"
            status_text.color = "#FF5757"
            page.update()
    
    def process_web_file(file_name):
        """معالجة الملف المرفوع على الويب"""
        # هنا يمكنك قراءة الملف من مجلد الرفع
        upload_path = os.path.join("uploads", "apk_files", file_name)
        if os.path.exists(upload_path):
            process_apk(upload_path)
        else:
            status_text.value = "❌ خطأ: لم يتم العثور على الملف المرفوع"
            status_text.color = "#FF5757"
            page.update()
    
    def process_apk(file_path):
        """معالجة ملف APK"""
        nonlocal current_apk_path, current_apk_files
        
        # تحديث الحالة
        status_text.value = "⏳ جاري تحليل الملف..."
        status_text.color = "#FFD857"
        page.update()
        
        try:
            # تحليل APK
            with zipfile.ZipFile(file_path, 'r') as apk:
                files = apk.namelist()
                size = os.path.getsize(file_path) / (1024 * 1024)
                
                current_apk_path = file_path
                current_apk_files = files
                
                # تحديث المعلومات
                apk_name_text.value = f"📱 {os.path.basename(file_path)}"
                apk_size_text.value = f"📦 الحجم: {size:.2f} MB"
                files_count_text.value = f"🗂️ عدد الملفات: {len(files)}"
                
                # عرض الملفات
                update_files_list(files)
                
                # تحديث الحالة
                status_text.value = "✅ تم تحليل الملف بنجاح"
                status_text.color = "#57FF81"
                
                # عرض رسالة نجاح
                page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"✅ تم تحميل: {os.path.basename(file_path)}"),
                        duration=3000,
                        bgcolor="#57FF81"
                    )
                )
                
        except zipfile.BadZipFile:
            status_text.value = "❌ خطأ: الملف ليس بصيغة APK صالحة"
            status_text.color = "#FF5757"
            page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("❌ الملف ليس بصيغة APK صالحة"),
                    duration=3000,
                    bgcolor="#FF5757"
                )
            )
        except Exception as e:
            status_text.value = f"❌ خطأ: {str(e)}"
            status_text.color = "#FF5757"
        
        page.update()
    
    def update_files_list(files):
        """تحديث قائمة الملفات"""
        files_list.controls.clear()
        
        # إضافة حقل بحث
        search_field = ft.TextField(
            hint_text="🔍 بحث في الملفات...",
            width=300,
            on_change=lambda e: filter_files(e.control.value)
        )
        files_list.controls.append(search_field)
        
        # عرض الملفات
        for file in files[:200]:
            # اختيار أيقونة حسب نوع الملف
            if file.endswith('.dex'):
                icon = ft.Icons.CODE
                icon_color = "#FF57DB"
            elif file.startswith('assets/'):
                icon = ft.Icons.FOLDER
                icon_color = "#FFD857"
            elif file.startswith('lib/'):
                icon = ft.Icons.APP_REGISTRATION
                icon_color = "#579AFF"
            elif file.endswith('.xml'):
                icon = ft.Icons.CODE
                icon_color = "#7EFF57"
            elif file.endswith(('.png', '.jpg', '.jpeg')):
                icon = ft.Icons.IMAGE
                icon_color = "#FF57CD"
            elif file.endswith('.so'):
                icon = ft.Icons.APP_REGISTRATION
                icon_color = "#FF5757"
            else:
                icon = ft.Icons.INSERT_DRIVE_FILE
                icon_color = "#95FF57"
            
            # إضافة الملف للقائمة
            files_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(icon, size=20, color=icon_color),
                        ft.Text(file, size=12, expand=True),
                        ft.Text(get_file_size(file), size=10, color="#57FF5F")
                    ]),
                    padding=8,
                    border=ft.border.all(1, "#GREY_300"),
                    border_radius=5,
                    on_click=lambda e, f=file: show_file_content(f),
                    ink=True
                )
            )
        
        if len(files) > 200:
            files_list.controls.append(
                ft.Text(f"... و {len(files) - 200} ملف آخر", italic=True, color="#57FF5F")
            )
    
    def get_file_size(file_name):
        """الحصول على حجم الملف داخل APK"""
        if not current_apk_path:
            return ""
        try:
            with zipfile.ZipFile(current_apk_path, 'r') as apk:
                info = apk.getinfo(file_name)
                size = info.file_size
                if size < 1024:
                    return f"{size} B"
                elif size < 1024 * 1024:
                    return f"{size/1024:.1f} KB"
                else:
                    return f"{size/(1024*1024):.1f} MB"
        except:
            return ""
    
    def filter_files(query):
        """تصفية الملفات حسب البحث"""
        if not current_apk_files:
            return
        if not query:
            update_files_list(current_apk_files[:200])
        else:
            filtered = [f for f in current_apk_files if query.lower() in f.lower()]
            update_files_list(filtered[:200])
    
    def show_file_content(entry_name):
        """عرض محتوى الملف"""
        if not current_apk_path:
            return
        
        try:
            with zipfile.ZipFile(current_apk_path, 'r') as apk:
                if entry_name in apk.namelist():
                    data = apk.read(entry_name)
                    
                    # محاولة عرض كنص
                    try:
                        content = data.decode('utf-8', errors='replace')
                        if len(content) > 10000:
                            content = content[:10000] + "\n\n... [تم اقتطاع المحتوى]"
                    except:
                        content = f"[ملف ثنائي - {len(data)} بايت]"
                        if entry_name.endswith(('.png', '.jpg', '.jpeg')):
                            content += f"\n\n📷 هذا ملف صورة"
                        elif entry_name.endswith('.dex'):
                            content += f"\n\n📱 هذا ملف DEX (Dalvik Executable)"
                        elif entry_name.endswith('.so'):
                            content += f"\n\n🔧 هذا ملف مكتبة (Shared Object)"
                    
                    # عرض في مربع حوار
                    dialog = ft.AlertDialog(
                        title=ft.Text(entry_name, size=16),
                        content=ft.Container(
                            content=ft.Text(content, size=11, selectable=True, font_family="monospace"),
                            width=700,
                            height=500,
                            padding=10,
                        ),
                        actions=[
                            ft.TextButton("إغلاق", on_click=lambda e: setattr(dialog, 'open', False))
                        ]
                    )
                    page.dialog = dialog
                    dialog.open = True
                    page.update()
        except Exception as e:
            page.show_snack_bar(ft.SnackBar(
                content=ft.Text(f"خطأ: {e}"),
                duration=3000
            ))
    
    def pick_file_async(e):
        """دالة لاختيار الملف (تعمل بشكل غير متزامن)"""
        import asyncio
        asyncio.create_task(handle_files_pick(e))
    
    # واجهة المستخدم الرئيسية
    page.add(
        ft.AppBar(
            title=ft.Text("📱 APK Editor Pro", size=24),
            center_title=True,
            bgcolor="#5770FF",
            color="#E6E6E6",
            actions=[
                ft.IconButton(ft.Icons.HELP_OUTLINE, on_click=lambda e: show_help())
            ]
        ),
        ft.Container(
            content=ft.Column([
                # معلومات التطبيق
                ft.Text("أداة تحليل وتعديل ملفات APK", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("قم بتحميل ملف APK لعرض محتوياته وتحليله", size=14, color="#A8FF57"),
                ft.Divider(height=20),
                
                # زر اختيار الملف
                ft.ElevatedButton(
                    "📂 اختيار ملف APK",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=pick_file_async,
                    style=ft.ButtonStyle(
                        bgcolor="#5A57FF",
                        color="#E7E7E7",
                        padding=15,
                        elevation=5
                    ),
                    width=250,
                    height=50
                ),
                
                # بطاقة معلومات الملف
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([status_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Divider(),
                            apk_name_text,
                            apk_size_text,
                            files_count_text,
                        ], spacing=10),
                        padding=20,
                        width=500
                    ),
                    elevation=3
                ),
                
                ft.Divider(),
                
                # قائمة الملفات
                ft.Row([
                    ft.Text("📁 محتويات APK", size=18, weight=ft.FontWeight.BOLD),
                ]),
                ft.Container(
                    content=files_list,
                    border=ft.border.all(1, "#747474"),
                    border_radius=10,
                    padding=10,
                    height=500,
                    width=800
                ),
                
                ft.Text(
                    "💡 نصائح: انقر على أي ملف لعرض محتوياته | يمكنك البحث في الملفات باستخدام مربع البحث",
                    size=12,
                    color="#757575",
                    italic=True
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
            padding=30,
            expand=True
        )
    )
    
    def show_help():
        """عرض مساعدة"""
        dialog = ft.AlertDialog(
            title=ft.Text("📖 المساعدة", size=20),
            content=ft.Text(
                "كيفية استخدام APK Editor:\n\n"
                "1. انقر على زر 'اختيار ملف APK'\n"
                "2. اختر ملف APK من جهازك\n"
                "3. انتظر حتى يتم تحليل الملف\n"
                "4. ستظهر معلومات التطبيق وقائمة الملفات\n"
                "5. انقر على أي ملف لعرض محتوياته\n"
                "6. استخدم مربع البحث للبحث عن ملف معين\n\n"
                f"المنصة: {'Web' if is_web else 'Desktop'}\n\n"
                "الميزات:\n"
                "• عرض جميع ملفات APK\n"
                "• عرض محتوى الملفات النصية\n"
                "• عرض معلومات الملفات (الحجم، النوع)\n"
                "• بحث سريع في الملفات\n"
                "• يدعم جميع منصات Flet (Windows, Android, iOS, Web)",
                size=14,
                selectable=True
            ),
            actions=[
                ft.TextButton("حسناً", on_click=lambda e: setattr(dialog, 'open', False))
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    page.update()

if __name__ == "__main__":
    # إنشاء مجلد للرفع
    os.makedirs("uploads/apk_files", exist_ok=True)
    
    # تشغيل التطبيق مع مجلد للرفع
    ft.app(target=main, upload_dir="uploads")