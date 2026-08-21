"""
Chatbot Launcher - Simple Direct Launcher
==========================================
لانچر ساده برای اجرای مستقیم chatbot_app.py

Usage:
    from MathAssistant.utils.chatbot_launcher import launch_chatbot
    success, message = launch_chatbot()

Author: AmirMohammad Ghasemzadeh
Version: 1.0.0
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Tuple, Optional

# ============================================================================
# Configuration
# ============================================================================

class ChatbotConfig:
    """تنظیمات مسیرها."""

    # مسیر پروژه
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # مسیرهای مختلف احتمالی برای chatbot_app.py
    POSSIBLE_PATHS = [
        PROJECT_ROOT / "src" / "MathAssistant" / "bot" / "chatbot_app.py",
        PROJECT_ROOT / "MathAssistant" / "bot" / "chatbot_app.py",
        PROJECT_ROOT / "bot" / "chatbot_app.py",
        PROJECT_ROOT / "chatbot_app.py",
        PROJECT_ROOT / "Math-bot.py",
    ]

    # Python executable
    PYTHON_EXECUTABLE = sys.executable


# ============================================================================
# Process Manager
# ============================================================================

class ChatbotProcessManager:
    """مدیریت ساده فرآیند چت‌بات."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """راه‌اندازی."""
        self._process: Optional[subprocess.Popen] = None

    @property
    def is_running(self) -> bool:
        """بررسی اجرا بودن."""
        if self._process is None:
            return False
        return self._process.poll() is None

    @property
    def process(self) -> Optional[subprocess.Popen]:
        """دریافت فرآیند."""
        return self._process

    def find_chatbot_script(self) -> Optional[Path]:
        """پیدا کردن اسکریپت چت‌بات."""
        for path in ChatbotConfig.POSSIBLE_PATHS:
            if path.exists():
                return path
        return None

    def launch(self) -> Tuple[bool, str]:
        """
        اجرای چت‌بات.

        Returns:
            (success, message)
        """
        # بررسی اجرای قبلی
        if self.is_running:
            return False, "چت‌بات در حال اجراست"

        # پیدا کردن اسکریپت
        script_path = self.find_chatbot_script()

        if script_path is None:
            return False, (
                "فایل chatbot_app.py یافت نشد.\n"
                "مسیرهای بررسی شده:\n" +
                "\n".join(f"  - {p}" for p in ChatbotConfig.POSSIBLE_PATHS)
            )

        # بررسی مجوز
        if not os.access(str(script_path), os.R_OK):
            return False, f"فایل {script_path} قابل خواندن نیست"

        try:
            # اجرای مستقیم
            self._process = subprocess.Popen(
                [
                    ChatbotConfig.PYTHON_EXECUTABLE,
                    str(script_path),
                ],
                cwd=str(script_path.parent),  # اجرا از دایرکتوری اسکریپت
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt" else 0,
            )

            # بررسی سریع اجرا
            import time
            time.sleep(1)

            if self._process.poll() is not None:
                # فرآیند فوراً خارج شد
                return_code = self._process.returncode
                self._process = None
                return False, f"چت‌بات نتوانست اجرا شود (کد خطا: {return_code})"

            return True, f"Success • (PID: {self._process.pid})"

        except PermissionError:
            return False, "دسترسی کافی برای اجرا نیست"

        except OSError as e:
            return False, f"خطای سیستم: {e}"

        except Exception as e:
            return False, f"خطای غیرمنتظره: {e}"

    def stop(self) -> Tuple[bool, str]:
        """توقف چت‌بات."""
        if not self.is_running:
            return True, "چت‌بات در حال اجرا نیست"

        try:
            self._process.terminate()

            try:
                self._process.wait(timeout=5)
                return True, "چت‌بات متوقف شد"
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)
                return True, "چت‌بات به زور متوقف شد"

        except Exception as e:
            return False, f"خطا در توقف چت‌بات: {e}"

        finally:
            self._process = None


# ============================================================================
# Convenience Functions
# ============================================================================

def launch_chatbot() -> Tuple[bool, str]:
    """
    اجرای چت‌بات.

    Returns:
        (success, message)

    Example:
        >>> success, message = launch_chatbot()
        >>> if success:
        ...     print("OK")
    """
    manager = ChatbotProcessManager()
    return manager.launch()


def stop_chatbot() -> Tuple[bool, str]:
    """توقف چت‌بات."""
    manager = ChatbotProcessManager()
    return manager.stop()


def is_chatbot_running() -> bool:
    """بررسی اجرا بودن."""
    manager = ChatbotProcessManager()
    return manager.is_running


def get_chatbot_process():
    """دریافت فرآیند."""
    manager = ChatbotProcessManager()
    return manager.process


# ============================================================================
# CLI
# ============================================================================

def main():
    """خط فرمان."""
    import argparse

    parser = argparse.ArgumentParser(description="Chatbot Launcher")
    parser.add_argument(
        "command",
        nargs="?",
        default="launch",
        choices=["launch", "stop", "status"],
        help="دستور (پیش‌فرض: launch)"
    )

    args = parser.parse_args()

    if args.command == "launch":
        success, message = launch_chatbot()
        print(f"{'✅' if success else '❌'} {message}")
        return 0 if success else 1

    elif args.command == "stop":
        success, message = stop_chatbot()
        print(f"{'✅' if success else '❌'} {message}")
        return 0 if success else 1

    elif args.command == "status":
        running = is_chatbot_running()
        print(f"Running: {running}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
