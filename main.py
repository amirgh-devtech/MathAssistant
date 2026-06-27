"""
MathAssistant - نقطه ورود برنامه

این فایل نقطه شروع برنامه است که:
1. تشخیص خودکار Qt (PyQt5/PyQt6) بر اساس ویندوز
2. راه‌اندازی QApplication با تم مناسب
3. نمایش پنجره اصلی
4. مدیریت graceful shutdown

Usage:
    python main.py
    python main.py --theme dark
    python main.py --debug

Author: MathAssistant Team
Version: 4.0.0
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# افزودن مسیر پروژه به sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from MathAssistant.ui.styles import (
    theme, ThemeMode, SystemDetector, QtAdapter
)
from MathAssistant.utils.system_tools import LogSetup, SystemInfo


def parse_args():
    """پارسر آرگومان‌های خط فرمان."""
    parser = argparse.ArgumentParser(
        description="MathAssistant - ابزارهای کمک آموزشی ریاضی",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
مثال‌ها:
  python main.py                  # اجرای عادی با تم پیش‌فرض
  python main.py --theme dark     # اجرا با تم تاریک
  python main.py --theme ocean    # اجرا با تم اقیانوس
  python main.py --debug          # اجرا با لاگ سطح DEBUG

تم‌های موجود:
  light, dark, high_contrast, ocean, forest, sunset, midnight, aurora
        """
    )

    parser.add_argument(
        '--theme', '-t',
        type=str,
        default='light',
        choices=[m.name.lower() for m in ThemeMode],
        help='تم برنامه (پیش‌فرض: light)'
    )

    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='فعال‌سازی حالت debug با لاگ کامل'
    )

    parser.add_argument(
        '--no-log-file',
        action='store_true',
        help='ذخیره نکردن لاگ در فایل'
    )

    return parser.parse_args()


def setup_logging(debug: bool = False, log_to_file: bool = True):
    """تنظیم logging."""
    level = logging.DEBUG if debug else logging.INFO

    # فرمت‌های سفارشی
    console_format = (
        '%(levelname)-8s [%(name)-20s] %(message)s'
        if debug else
        '🎓 %(levelname)-8s %(message)s'
    )

    return LogSetup.setup(
        level=level,
        log_to_file=log_to_file,
        log_format_console=console_format
    )


def print_banner():
    """نمایش بنر شروع برنامه."""
    info = theme.get_system_info()

    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║         📐 MathAssistant v4.0 - Production Ready             ║
╠══════════════════════════════════════════════════════════════╣
║  🖥️  OS       : {info['os']:<44}  ║
║  🐍 Python   : {info['python']:<44}  ║
║  🧵 Qt       : {info['qt_version']:<44}  ║
║  🎨 Theme    : {info['theme']:<44}  ║
║  💾 RAM      : {info.get('ram_gb', 'N/A'):<44}  ║
║  📐 DPI      : {info.get('dpi', 'N/A'):<44}  ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """تابع اصلی."""
    # 1. پارس آرگومان‌ها
    args = parse_args()

    # 2. تنظیم logging
    logger = setup_logging(
        debug=args.debug,
        log_to_file=not args.no_log_file
    )

    logger.info("Starting MathAssistant v4.0...")

    # 3. تشخیص Qt و ایجاد QApplication
    try:
        adapter = QtAdapter()
    except ImportError as e:
        print(f"❌ خطا: {e}")
        print("لطفاً PyQt5 یا PyQt6 را نصب کنید:")
        print("  pip install PyQt6")
        print("  یا")
        print("  pip install PyQt5")
        sys.exit(1)

    app = adapter.QApplication(sys.argv)
    app.setApplicationName("MathAssistant")
    app.setApplicationVersion("4.0.0")
    app.setOrganizationName("MathAssistant Team")

    # 4. تنظیم تم
    try:
        theme_mode = ThemeMode[args.theme.upper()]
    except KeyError:
        logger.warning(f"Invalid theme '{args.theme}', using LIGHT")
        theme_mode = ThemeMode.LIGHT

    theme.set_mode(theme_mode)

    # 5. نمایش بنر
    print_banner()

    # 6. ایجاد و نمایش پنجره اصلی
    from MathAssistant.ui.main_window import MainWindow

    logger.info("Creating MainWindow...")
    window = MainWindow()
    window.show()

    logger.info("Application started successfully")

    # 7. اجرای event loop
    exit_code = app.exec()

    # 8. Graceful shutdown
    logger.info(f"Application exiting with code {exit_code}")

    # پاکسازی
    from MathAssistant.utils.system_tools import TimeoutExecutor
    TimeoutExecutor.shutdown()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
