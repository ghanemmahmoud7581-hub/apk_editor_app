"""
PermissionManager
-----------------
Handles ALL Android runtime permissions required by the APK Editor app.

Key permissions managed:
  • READ_EXTERNAL_STORAGE / WRITE_EXTERNAL_STORAGE  (API < 33)
  • READ_MEDIA_IMAGES / READ_MEDIA_VIDEO            (API ≥ 33)
  • MANAGE_EXTERNAL_STORAGE                         (broad file access)
  • PRINT_SERVICE (via PrintManager)
  • REQUEST_INSTALL_PACKAGES                        (install edited APKs)
  • BLUETOOTH_CONNECT                               (optional – wireless print)
"""
import flet as ft
from typing import Callable, Optional
import asyncio


# Map from logical name → Android permission string
REQUIRED_PERMISSIONS: dict[str, str] = {
    "storage":          "android.permission.READ_EXTERNAL_STORAGE",
    "media_location":   "android.permission.READ_MEDIA_IMAGES",         # photos/media (API 33+)
    "manage_files":     "android.permission.MANAGE_EXTERNAL_STORAGE",
    "camera":           "android.permission.CAMERA",                # scan QR on APK
    "notifications":    "android.permission.POST_NOTIFICATIONS",
    "location":         "android.permission.ACCESS_FINE_LOCATION",              # optional
}


class PermissionManager:
    """Requests and tracks Android permissions for the Flet app."""

    def __init__(self, page: ft.Page):
        self.page = page
        self._status = {}
        self._callbacks = []

    # ── Public API ─────────────────────────────────────────────────────────

    async def request_all_permissions(self):
        """طلب جميع الصلاحيات الأساسية"""
        try:
            results = {}
            
            # طلب صلاحية التخزين
            storage_result = await self._request_permission_async(
                REQUIRED_PERMISSIONS["storage"]
            )
            self._status['storage'] = storage_result
            results['storage'] = storage_result
            
            # طلب صلاحية إدارة الملفات (Android 11+)
            manage_result = await self._request_permission_async(
                REQUIRED_PERMISSIONS["manage_files"]
            )
            self._status['manage_files'] = manage_result
            results['manage_files'] = manage_result
            
            # طلب صلاحية الوسائط (API 33+)
            media_result = await self._request_permission_async(
                REQUIRED_PERMISSIONS["media_location"]
            )
            self._status['media_location'] = media_result
            results['media_location'] = media_result
            
            # إخطار الكل بالتغييرات
            for name, granted in results.items():
                for fn in self._callbacks:
                    fn(name, granted)
            
            return results
        except Exception as e:
            print(f"[PermissionManager] Error requesting all permissions: {e}")
            return {}
        
    async def request_storage_permission(self):
        """طلب صلاحية التخزين"""
        try:
            # استخدام الصلاحية المناسبة حسب إصدار Android
            permission = REQUIRED_PERMISSIONS["storage"]
            result = await self._request_permission_async(permission)
            self._status['storage'] = result
            for fn in self._callbacks:
                fn('storage', result)
            if not result:
                self._show_denied_banner('storage')
            return result
        except Exception as e:
            print(f"[PermissionManager] Error requesting storage: {e}")
            self._status['storage'] = False
            return False
        
    async def request_manage_files_permission(self):
        """طلب صلاحية إدارة الملفات (Android 11+)"""
        try:
            permission = REQUIRED_PERMISSIONS["manage_files"]
            result = await self._request_permission_async(permission)
            self._status['manage_files'] = result
            for fn in self._callbacks:
                fn('manage_files', result)
            if not result:
                self._show_denied_banner('manage_files')
            return result
        except Exception as e:
            print(f"[PermissionManager] Error requesting manage_files: {e}")
            self._status['manage_files'] = False
            return False
    
    async def request_media_permission(self):
        """طلب صلاحية الوصول للوسائط (API 33+)"""
        try:
            permission = REQUIRED_PERMISSIONS["media_location"]
            result = await self._request_permission_async(permission)
            self._status['media_location'] = result
            for fn in self._callbacks:
                fn('media_location', result)
            if not result:
                self._show_denied_banner('media_location')
            return result
        except Exception as e:
            print(f"[PermissionManager] Error requesting media_location: {e}")
            self._status['media_location'] = False
            return False
    
    async def request_camera_permission(self):
        """طلب صلاحية الكاميرا"""
        try:
            permission = REQUIRED_PERMISSIONS["camera"]
            result = await self._request_permission_async(permission)
            self._status['camera'] = result
            for fn in self._callbacks:
                fn('camera', result)
            if not result:
                self._show_denied_banner('camera')
            return result
        except Exception as e:
            print(f"[PermissionManager] Error requesting camera: {e}")
            self._status['camera'] = False
            return False
    
    async def request_notifications_permission(self):
        """طلب صلاحية الإشعارات"""
        try:
            permission = REQUIRED_PERMISSIONS["notifications"]
            result = await self._request_permission_async(permission)
            self._status['notifications'] = result
            for fn in self._callbacks:
                fn('notifications', result)
            return result
        except Exception as e:
            print(f"[PermissionManager] Error requesting notifications: {e}")
            self._status['notifications'] = False
            return False
    
    async def request_location_permission(self):
        """طلب صلاحية الموقع"""
        try:
            permission = REQUIRED_PERMISSIONS["location"]
            result = await self._request_permission_async(permission)
            self._status['location'] = result
            for fn in self._callbacks:
                fn('location', result)
            return result
        except Exception as e:
            print(f"[PermissionManager] Error requesting location: {e}")
            self._status['location'] = False
            return False
    
    async def request_multiple_permissions(self, permissions_list):
        """طلب عدة صلاحيات مرة واحدة"""
        try:
            results = {}
            for perm_name in permissions_list:
                if perm_name in REQUIRED_PERMISSIONS:
                    permission = REQUIRED_PERMISSIONS[perm_name]
                    result = await self._request_permission_async(permission)
                    results[perm_name] = result
                    self._status[perm_name] = result
                    for fn in self._callbacks:
                        fn(perm_name, result)
                    if not result:
                        self._show_denied_banner(perm_name)
            return results
        except Exception as e:
            print(f"[PermissionManager] Error requesting multiple permissions: {e}")
            return {}
    
    async def _request_permission_async(self, permission: str):
        """
        دالة مساعدة لطلب صلاحية واحدة بشكل غير متزامن
        باستخدام الطريقة الصحيحة في Flet
        """
        try:
            # في Flet، الصلاحيات تطلب من خلال page.window
            if hasattr(self.page.window, 'request_permission_async'):
                # طريقة Flet الحديثة
                result = await self.page.window.request_permission_async(permission)
                return result
            elif hasattr(self.page.window, 'request_permission'):
                # طريقة Flet القديمة
                result = self.page.window.request_permission(permission)
                return result
            else:
                # طريقة بديلة باستخدام JavaScript (لـ web)
                print(f"[PermissionManager] No permission request method found")
                # محاكاة طلب الصلاحية - يجب تنفيذها حسب النظام
                return await self._request_permission_via_js(permission)
        except Exception as e:
            print(f"[PermissionManager] Error in _request_permission_async: {e}")
            return False
    
    async def _request_permission_via_js(self, permission: str):
        """
        طريقة بديلة لطلب الصلاحيات عبر JavaScript (للمنصات التي تدعمها)
        """
        try:
            # هذا يعمل فقط في بيئة الويب
            js_code = f"""
            async function requestPermission(permission) {{
                try {{
                    const result = await navigator.permissions.query({{name: permission}});
                    if (result.state === 'granted') {{
                        return true;
                    }} else if (result.state === 'prompt') {{
                        // لا يمكن طلب الصلاحية مباشرة في JavaScript
                        return false;
                    }}
                    return false;
                }} catch(e) {{
                    console.error(e);
                    return false;
                }}
            }}
            return await requestPermission('{permission}');
            """
            result = await self.page.window.run_javascript_async(js_code)
            return result
        except Exception as e:
            print(f"[PermissionManager] Error in JS permission request: {e}")
            return False

    def request_storage(self, on_done: Optional[Callable] = None):
        """Request storage permissions specifically (needed before file ops)."""
        async def _request():
            result = await self.request_storage_permission()
            if on_done:
                on_done(result)
        
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_request())
        except RuntimeError:
            asyncio.run(_request())

    def has_storage(self) -> bool:
        return self._status.get("storage", False) or self._status.get("manage_files", False)

    def has_all_required(self) -> bool:
        required = ["storage", "media_location"]
        return all(self._status.get(k, False) for k in required)

    def get_status(self) -> dict[str, bool]:
        return dict(self._status)

    def on_permissions_changed(self, cb: Callable):
        self._callbacks.append(cb)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _request_one(self, name: str, perm: str, cb: Optional[Callable] = None):
        async def _do():
            try:
                result = await self._request_permission_async(perm)
                granted = result if isinstance(result, bool) else getattr(result, 'granted', False)
                
                self._status[name] = granted
                for fn in self._callbacks:
                    fn(name, granted)
                if cb:
                    cb(granted)
                if not granted:
                    self._show_denied_banner(name)
            except Exception as e:
                print(f"[PermissionManager] Error requesting {name}: {e}")
                self._status[name] = False

        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_do())
        except RuntimeError:
            asyncio.run(_do())

    def _show_denied_banner(self, name: str):
        messages = {
            "storage":        "صلاحية التخزين مطلوبة لقراءة ملفات APK",
            "manage_files":   "صلاحية إدارة الملفات مطلوبة للوصول الكامل",
            "media_location": "صلاحية الوسائط مطلوبة لقراءة الأصول",
            "camera":         "صلاحية الكاميرا مطلوبة لمسح رموز QR",
            "notifications":  "صلاحية الإشعارات مطلوبة لإعلامك بحالة التطبيق",
        }
        msg = messages.get(name, f"صلاحية '{name}' مرفوضة")

        def close(e):
            self.page.banner.open = False
            self.page.update()

        self.page.banner = ft.Banner(
            bgcolor="#161b22",
            leading=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#d29922"),
            content=ft.Text(msg, color="#e6edf3"),
            actions=[
                ft.TextButton("إغلاق", on_click=close, style=ft.ButtonStyle(color="#58a6ff")),
                ft.TextButton(
                    "فتح الإعدادات",
                    on_click=lambda e: self.page.launch_url("app-settings:"),
                    style=ft.ButtonStyle(color="#3fb950"),
                ),
            ],
        )
        self.page.banner.open = True
        self.page.update()