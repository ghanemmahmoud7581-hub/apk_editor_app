"""
APKService
----------
Core APK parsing, asset extraction, and rebuilding logic.

Uses zipfile (stdlib) + androguard (optional) for deep analysis.
Designed to work within Android's scoped storage model:
  – file path comes from SAF picker (StorageManager)
  – writes go to app-private external dir (no extra permission)
"""
import zipfile
import shutil
import json
import struct
import hashlib
import subprocess
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


# ── Custom exceptions ──────────────────────────────────────────────────────
class APKServiceError(Exception):
    """الخطأ الأساسي لخدمة APK"""
    pass

class APKNotFoundError(APKServiceError):
    """عند عدم وجود ملف APK"""
    pass

class APKCorruptedError(APKServiceError):
    """عند تلف ملف APK"""
    pass

class APKEntryNotFoundError(APKServiceError):
    """عند عدم وجود مدخل معين في APK"""
    pass


# ── Binary XML decoder (Android's AXML format) ─────────────────────────────
def is_axml(data: bytes) -> bool:
    """
    التحقق مما إذا كانت البيانات بصيغة Android Binary XML
    
    تنسيق AXML يبدأ بـ 0x00080003 بصيغة little-endian
    """
    if len(data) < 8:
        return False
    
    # التحقق من التوقيع السحري لـ AXML
    return data[:4] == b'\x03\x00\x08\x00'


def decode_axml(data: bytes) -> str:
    """
    فك تشفير Android Binary XML إلى نص XML قابل للقراءة
    """
    if not is_axml(data):
        # محاولة فك التشفير كنص عادي إذا بدا مثل XML
        try:
            decoded = data.decode('utf-8')
            if '<' in decoded and '>' in decoded and 'manifest' in decoded.lower():
                return decoded
        except:
            pass
        return f"[ليست بصيغة AXML – {len(data)} بايت]"
    
    # محاولة استخدام androguard أولاً
    try:
        from androguard.core.axml import AXMLPrinter
        xml_obj = AXMLPrinter(data).get_xml_obj()
        if xml_obj is not None:
            return xml_obj.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
    except ImportError:
        pass
    
    # محاولة استخدام axmlparserpy كبديل
    try:
        import axmlparserpy.axmlprinter as ap
        xml_str = ap.AXMLPrinter(data).get_xml()
        if xml_str:
            return xml_str
    except ImportError:
        pass
    
    return f"[ملف AXML ثنائي – {len(data)} بايت – قم بتثبيت androguard لفك التشفير]"


class APKService:

    def __init__(self, apk_path: str, work_dir: Path):
        self.apk_path = apk_path
        self.work_dir = work_dir
        self._manifest_cache: Optional[str] = None
        self._zip_file: Optional[zipfile.ZipFile] = None
        self._entry_list_cache: Optional[list[str]] = None

    # ── Context manager support ────────────────────────────────────────────
    @contextmanager
    def _open_zip(self):
        """مدير سياق لفتح ملف ZIP مع التخزين المؤقت"""
        if self._zip_file is None:
            try:
                self._zip_file = zipfile.ZipFile(self.apk_path, "r")
            except FileNotFoundError as e:
                raise APKNotFoundError(f"لم يتم العثور على الملف: {e}")
            except zipfile.BadZipFile as e:
                raise APKCorruptedError(f"ملف APK تالف: {e}")
        try:
            yield self._zip_file
        except Exception:
            self.close()
            raise

    def close(self):
        """إغلاق ملف ZIP بشكل صريح"""
        if self._zip_file:
            self._zip_file.close()
            self._zip_file = None
            self._entry_list_cache = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def cleanup(self):
        """تنظيف الملفات المؤقتة وإغلاق الاتصالات"""
        self.close()
        
        # تنظيف الملفات المؤقتة في دليل العمل
        temp_files = list(self.work_dir.glob("_patching_*"))
        temp_files.extend(self.work_dir.glob("unsigned.*"))
        
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                print(f"فشل تنظيف {temp_file}: {e}")

    # ── Basic info ──────────────────────────────────────────────────────────

    def get_info(self) -> dict:
        """Return basic APK metadata."""
        p = Path(self.apk_path)
        entries = self.list_entries()
        assets  = [e for e in entries if e.startswith("assets/")]
        libs    = [e for e in entries if e.startswith("lib/")]
        dex     = [e for e in entries if e.endswith(".dex")]

        return {
            "filename":    p.name,
            "size_mb":     round(p.stat().st_size / 1_048_576, 2),
            "entries":     len(entries),
            "assets":      len(assets),
            "native_libs": len(libs),
            "dex_files":   len(dex),
            "has_manifest": "AndroidManifest.xml" in entries,
        }

    # ── Entry listing ───────────────────────────────────────────────────────

    def list_entries(self) -> list[str]:
        if self._entry_list_cache is not None:
            return self._entry_list_cache
        
        try:
            with self._open_zip() as z:
                self._entry_list_cache = z.namelist()
                return self._entry_list_cache
        except Exception as e:
            print(f"[APKService] list_entries error: {e}")
            return []

    def list_assets(self) -> list[str]:
        return [e for e in self.list_entries() if e.startswith("assets/")]

    def list_by_type(self, ext: str) -> list[str]:
        return [e for e in self.list_entries() if e.lower().endswith(f".{ext}")]

    # ── Read entry ──────────────────────────────────────────────────────────

    def read_entry(self, entry_name: str) -> Optional[bytes]:
        try:
            with self._open_zip() as z:
                if entry_name in z.namelist():
                    return z.read(entry_name)
                raise APKEntryNotFoundError(f"المدخل '{entry_name}' غير موجود في APK")
        except (APKEntryNotFoundError, APKNotFoundError, APKCorruptedError):
            raise
        except Exception as e:
            print(f"[APKService] read_entry error: {e}")
            return None

    def read_entry_text(self, entry_name: str) -> Optional[str]:
        data = self.read_entry(entry_name)
        if data is None:
            return None

        # Binary XML detection: starts with magic bytes 0x00080003
        if len(data) >= 4 and data[:4] == b"\x03\x00\x08\x00":
            return decode_axml(data)

        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return data.decode("latin-1")
            except Exception:
                return f"[Binary data – {len(data)} bytes]"

    # ── Manifest ────────────────────────────────────────────────────────────

    def get_manifest(self) -> Optional[str]:
        if self._manifest_cache:
            return self._manifest_cache
        data = self.read_entry("AndroidManifest.xml")
        if data:
            self._manifest_cache = decode_axml(data) if data[:4] == b"\x03\x00\x08\x00" else data.decode("utf-8", errors="replace")
        return self._manifest_cache

    # ── Extract ─────────────────────────────────────────────────────────────

    def extract_entry(self, entry_name: str, dest_path: Path) -> bool:
        data = self.read_entry(entry_name)
        if data is None:
            return False
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        return True

    def extract_all(self, dest_dir: Path) -> int:
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(self.apk_path, "r") as z:
                z.extractall(dest_dir)
                return len(z.namelist())
        except Exception as e:
            print(f"[APKService] extract_all error: {e}")
            return 0

    # ── Write / patch ───────────────────────────────────────────────────────

    def patch_entry(self, entry_name: str, new_content: bytes) -> bool:
        """
        Replace one entry inside the APK (ZIP).
        Strategy: copy APK to temp, then update the entry.
        """
        tmp = self.work_dir / "_patching_tmp.apk"
        try:
            shutil.copy2(self.apk_path, tmp)
            with zipfile.ZipFile(tmp, "a") as z:
                # ZipFile "a" mode adds duplicate; proper rebuild needed for production
                z.writestr(entry_name, new_content)
            shutil.move(str(tmp), self.apk_path)
            return True
        except Exception as e:
            print(f"[APKService] patch_entry error: {e}")
            if tmp.exists():
                tmp.unlink()
            return False

    def rebuild(self, source_dir: Path, output_path: Path) -> bool:
        """
        Repack a directory back into a ZIP/APK.
        NOTE: This creates an *unsigned* APK – signing required before install.
        """
        try:
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
                for file in source_dir.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(source_dir)
                        z.write(file, arcname)
            return True
        except Exception as e:
            print(f"[APKService] rebuild error: {e}")
            return False

    def rebuild_signed(self, source_dir: Path, output_path: Path, 
                       keystore_path: Optional[Path] = None,
                       keystore_pass: str = "android",
                       key_alias: str = "key0") -> bool:
        """
        إعادة بناء APK مع التوقيع الرقمي
        
        Args:
            source_dir: المصدر الذي يحتوي على الملفات
            output_path: مسار ملف APK النهائي
            keystore_path: مسار ملف keystore (إذا لم يتم تحديده، سيتم إنشاء مؤقت)
            keystore_pass: كلمة مرور keystore
            key_alias: اسم المفتاح
        """
        # إنشاء APK غير موقع أولاً
        unsigned_path = self.work_dir / "unsigned.apk"
        if not self.rebuild(source_dir, unsigned_path):
            return False
        
        # إذا لم يتم تحديد keystore، إنشاء واحد مؤقت
        if keystore_path is None:
            keystore_path = self.work_dir / "debug.keystore"
            if not keystore_path.exists():
                if not self._create_debug_keystore(keystore_path, keystore_pass):
                    return False
        
        # توقيع APK باستخدام apksigner أو jarsigner
        try:
            # محاولة استخدام apksigner (موصى به لـ Android)
            result = subprocess.run([
                "apksigner", "sign",
                "--ks", str(keystore_path),
                "--ks-pass", f"pass:{keystore_pass}",
                "--ks-key-alias", key_alias,
                "--out", str(output_path),
                str(unsigned_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                unsigned_path.unlink()
                return True
                
        except FileNotFoundError:
            # استخدام jarsigner كبديل
            try:
                result = subprocess.run([
                    "jarsigner", "-sigalg", "SHA1withRSA", "-digestalg", "SHA1",
                    "-keystore", str(keystore_path),
                    "-storepass", keystore_pass,
                    str(unsigned_path), key_alias
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    shutil.move(str(unsigned_path), str(output_path))
                    return True
            except FileNotFoundError:
                print("[APKService] لم يتم العثور على apksigner أو jarsigner")
            except Exception as e:
                print(f"[APKService] signing error: {e}")
        
        return False

    def _create_debug_keystore(self, keystore_path: Path, password: str) -> bool:
        """إنشاء keystore تصحيح أخطاء مؤقت"""
        try:
            subprocess.run([
                "keytool", "-genkey", "-v",
                "-keystore", str(keystore_path),
                "-alias", "key0",
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", "10000",
                "-storepass", password,
                "-keypass", password,
                "-dname", "CN=Android Debug, O=Android, C=US"
            ], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[APKService] فشل إنشاء keystore: {e}")
            return False
        except FileNotFoundError:
            print("[APKService] لم يتم العثور على keytool")
            return False

    # ── Search ──────────────────────────────────────────────────────────────

    def search_in_entries(self, query: str, 
                         file_extensions: Optional[list[str]] = None,
                         max_results: int = 50,
                         case_sensitive: bool = False) -> list[dict]:
        """
        البحث في محتويات الملفات داخل APK
        
        Args:
            query: النص المطلوب البحث عنه
            file_extensions: امتدادات الملفات المراد البحث فيها
            max_results: الحد الأقصى للنتائج
            case_sensitive: حساسية حالة الأحرف
        """
        results = []
        q = query if case_sensitive else query.lower()
        
        # امتدادات الملفات الثنائية التي يجب تخطيها
        skip_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.dex', '.so', '.gz', '.zip'}
        
        for entry in self.list_entries():
            ext = Path(entry).suffix.lower()
            
            # تخطي الملفات الثنائية
            if ext in skip_extensions:
                continue
                
            # فلترة حسب الامتداد إذا تم تحديده
            if file_extensions and ext not in file_extensions:
                continue
            
            text = self.read_entry_text(entry)
            if not text:
                continue
                
            search_text = text if case_sensitive else text.lower()
            if q in search_text:
                # العثور على الأسطر التي تحتوي على النص
                lines = []
                for i, line in enumerate(text.splitlines()):
                    line_search = line if case_sensitive else line.lower()
                    if q in line_search:
                        lines.append({
                            "line_number": i + 1,
                            "content": line.strip()[:200]  # تحديد طول السطر
                        })
                        if len(lines) >= 10:  # حد أقصى 10 أسطر لكل ملف
                            break
                
                if lines:
                    results.append({
                        "entry": entry,
                        "matches": lines,
                        "match_count": len(lines)
                    })
                    
            if len(results) >= max_results:
                break
        
        return results

    # ── Integrity verification ──────────────────────────────────────────────

    def verify_integrity(self) -> dict:
        """
        التحقق من سلامة ملف APK
        """
        try:
            with zipfile.ZipFile(self.apk_path, "r") as z:
                # التحقق من وجود الملفات الأساسية
                required_files = ["AndroidManifest.xml"]
                missing = [f for f in required_files if f not in z.namelist()]
                
                # حساب هاش الملف
                with open(self.apk_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                return {
                    "valid_zip": True,
                    "missing_required": missing,
                    "sha256": file_hash,
                    "file_size": Path(self.apk_path).stat().st_size,
                    "entry_count": len(z.namelist())
                }
        except zipfile.BadZipFile:
            return {
                "valid_zip": False,
                "error": "ملف APK تالف أو ليس بصيغة ZIP صحيحة"
            }
        except FileNotFoundError:
            return {
                "valid_zip": False,
                "error": "لم يتم العثور على ملف APK"
            }