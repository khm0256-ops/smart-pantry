import os
import sys
import webbrowser
import threading
import time
from home_app import app

def open_browser():
    """فتح المتصفح بعد تشغيل السيرفر"""
    time.sleep(2)  # انتظار تشغيل السيرفر
    webbrowser.open('http://127.0.0.1:5002')

def get_resource_path(relative_path):
    """الحصول على المسار الصحيح للملفات عند التحويل لـ EXE"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    # طباعة رسالة ترحيبية
    print("=" * 60)
    print("🏠 تطبيق بيتي الذكي - Smart Home App")
    print("=" * 60)
    print("✅ التطبيق يعمل الآن...")
    print("📱 سيتم فتح المتصفح تلقائياً...")
    print("🌐 العنوان: http://127.0.0.1:5002")
    print("")
    print("⚠️  تحذير مهم:")
    print("   - لا تغلق هذه النافذة طالما تستخدم التطبيق")
    print("   - لإيقاف التطبيق: اضغط Ctrl+C أو أغلق النافذة")
    print("=" * 60)
    print("")
    
    # فتح المتصفح تلقائياً
    threading.Thread(target=open_browser, daemon=True).start()
    
    # تشغيل التطبيق
    try:
        app.run(host='127.0.0.1', port=5002, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n✅ تم إيقاف التطبيق بنجاح. شكراً لاستخدامك!")
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        input("\nاضغط Enter للخروج...")