# ⚙️ APK Editor Pro — Flet + Python for Android

تطبيق أندرويد لتحرير ملفات APK مبني بـ **Python + Flet**، مع دعم كامل لـ:
- 🗂️ استعراض وتحرير محتويات APK
- 🖨️ طباعة الفواتير عبر Android PrintManager
- 📄 تصدير الفواتير إلى PDF
- 🔐 إدارة صلاحيات Android بشكل صحيح

---

## 📁 هيكل المشروع

```
apk_editor_app/
├── src/
│   ├── main.py                         # نقطة الدخول
│   ├── pages/
│   │   ├── home_page.py               # الرئيسية + تحميل APK
│   │   ├── editor_page.py             # مستعرض ومحرر APK
│   │   ├── invoice_page.py            # إنشاء الفاتورة
│   │   └── settings_page.py           # الإعدادات والصلاحيات
│   ├── utils/
│   │   ├── permissions.py             # PermissionManager
│   │   └── storage.py                 # StorageManager (SAF bridge)
│   └── services/
│       └── print_service.py           # PrintService (HTML → Android Print)
│
├── android/
│   └── app/src/main/
│       ├── AndroidManifest.xml        # جميع الصلاحيات
│       ├── java/com/apkeditor/
│       │   └── MainActivity.java      # جسر PrintManager
│       └── res/
│           ├── xml/file_provider_paths.xml
│           └── values/strings.xml
│
├── flet_build.yml                     # إعدادات البناء
├── requirements.txt
└── .github/workflows/build_android.yml
```

---

## 🔐 الصلاحيات المُعلَنة

| الصلاحية | السبب |
|---|---|
| `READ/WRITE_EXTERNAL_STORAGE` | قراءة ملفات APK (API < 33) |
| `MANAGE_EXTERNAL_STORAGE` | وصول كامل (مدير ملفات) |
| `READ_MEDIA_IMAGES/VIDEO/AUDIO` | وسائط Android 13+ |
| `REQUEST_INSTALL_PACKAGES` | تثبيت APK المعدّل |
| `BLUETOOTH_CONNECT` | الطباعة اللاسلكية |
| `INTERNET` | Flet WebSocket + تحديثات |
| `CAMERA` | مسح QR |

---

## 🖨️ كيف تعمل الطباعة

المشكلة الأصلية كانت أن Flet لا يدعم `PrintManager` مباشرةً.  
الحل المُطبَّق:

```
Python (Flet)                Android (Java)
─────────────────────────────────────────────
page.invoke_method(          MainActivity.java
  "print_html",         ──►  MethodChannel
  {"html": "...",            │
   "job_name": "..."}        ▼
)                        WebView.createPrintDocumentAdapter()
                              │
                              ▼
                         PrintManager.print()
                              │
                              ▼
                         [نافذة الطباعة النظام]
                         PDF / Wi-Fi / BT
```

---

## 🗂️ الأصول والعلاقة مع Android

### مشكلة الأصول
في Android:
- التطبيقات **لا تملك** صلاحية قراءة ملفات التطبيقات الأخرى مباشرةً
- ملفات APK مجرد ZIPs — نستخدم `zipfile` لفتحها بعد اختيارها عبر **SAF**

### الحل المُطبَّق
```python
# StorageManager يستخدم ft.FilePicker الذي يستدعي SAF
self.storage.pick_apk(callback)  # → Android Storage Access Framework
# بعد الاختيار، نحصل على مسار مؤقت مُصرَّح به
with zipfile.ZipFile(path) as z:
    assets = [f for f in z.namelist() if f.startswith("assets/")]
```

---

## 🚀 البناء والتشغيل

### متطلبات البيئة
```bash
pip install flet>=0.21.0
# Android SDK + JDK 17
```

### تشغيل على سطح المكتب (للتطوير)
```bash
cd src
python main.py
```

### بناء APK
```bash
cd src
flet build android --verbose
```

### تثبيت على الجهاز
```bash
adb install build/apk/outputs/apk/debug/app-debug.apk
```

---

## 📝 ملاحظات مهمة

1. **`MANAGE_EXTERNAL_STORAGE`** يتطلب موافقة يدوية من المستخدم في الإعدادات
2. الطباعة تعمل فقط على Android — على سطح المكتب يفتح HTML في المتصفح
3. `REQUEST_INSTALL_PACKAGES` يتطلب إذن "تثبيت تطبيقات غير معروفة" من الإعدادات
