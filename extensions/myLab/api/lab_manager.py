# myLab/api/lab_manager.py
import sys
import logging
import json
import queue  # برای مدیریت تردینگ و انتقال وظایف به مین ترد
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from .html_generator import get_main_html

_myLab_dir = Path(__file__).resolve().parent.parent
if str(_myLab_dir) not in sys.path:
    sys.path.insert(0, str(_myLab_dir))

from module.smart_lab_loader import Grade, Subject
from api import LabAPI

logger = logging.getLogger(__name__)

EXPLORER_HTML = get_main_html()

def _detect_backend():
    py_ver = sys.version_info[:2]
    if py_ver <= (3, 9):
        try:
            import cefpython3  # type: ignore
            return "cef"
        except ImportError:
            pass
    try:
        import webview
        return "webview"
    except ImportError:
        pass
    return "browser"


class LabExplorer:
    """کاوشگر آزمایشگاه مجازی - صفحه اصلی با فیلتر و جستجو"""

    def __init__(self, api: LabAPI):
        self.api = api
        self._server = None
        self._port = 0
        self._labs = api.list_labs()
        self._open_callback = None

    def _start_server(self):
        """شروع HTTP سرور برای سرو HTML"""
        import socket
        import threading

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            self._port = s.getsockname()[1]

        explorer = self

        class Handler(SimpleHTTPRequestHandler):
            def do_GET(handler_self):
                try:
                    if handler_self.path == '/' or handler_self.path == '/explorer':
                        handler_self._serve_html()
                    elif handler_self.path.startswith('/api/labs'):
                        handler_self._serve_json()
                    elif handler_self.path.startswith('/open'):
                        handler_self._handle_open()
                    else:
                        handler_self.send_response(404)
                        handler_self.end_headers()
                except Exception as e:
                    logger.error(f"Error handling request: {e}")

            def _serve_html(handler_self):
                handler_self.send_response(200)
                handler_self.send_header('Content-Type', 'text/html; charset=utf-8')
                handler_self.end_headers()
                handler_self.wfile.write(EXPLORER_HTML.encode('utf-8'))

            def _serve_json(handler_self):
                handler_self.send_response(200)
                handler_self.send_header('Content-Type', 'application/json; charset=utf-8')
                handler_self.end_headers()
                handler_self.wfile.write(json.dumps(explorer._labs, ensure_ascii=False).encode('utf-8'))

            def _handle_open(handler_self):
                from urllib.parse import urlparse, parse_qs
                params = parse_qs(urlparse(handler_self.path).query)
                name = params.get('name', [''])[0]
                grade = params.get('grade', [''])[0]
                subject = params.get('subject', [''])[0]

                if name and grade and subject and explorer._open_callback:
                    explorer._open_callback(name, grade, subject)
                    handler_self.send_response(200)
                    handler_self.send_header('Content-Type', 'application/json')
                    handler_self.end_headers()
                    handler_self.wfile.write(b'{"status":"ok"}')
                else:
                    handler_self.send_response(400)
                    handler_self.send_header('Content-Type', 'application/json')
                    handler_self.end_headers()
                    handler_self.wfile.write(b'{"status":"error","message":"Missing parameters"}')

            def log_message(handler_self, format, *args):
                pass

        self._server = HTTPServer(('127.0.0.1', self._port), Handler)
        server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        server_thread.start()

    def show(self, open_callback, run_loop_callback=None):
        """نمایش کاوشگر در WebView"""
        self._open_callback = open_callback
        self._start_server()

        backend = _detect_backend()
        url = f'http://127.0.0.1:{self._port}/explorer'

        if backend == "cef":
            import cefpython3 as cef  # type: ignore
            try:
                cef.Initialize()
            except TypeError:
                cef.Initialize(settings={"multi_threaded_message_loop": False})
            cef.CreateBrowserSync(url=url, window_title="آزمایشگاه مجازی")

            # در CEF اگر قرار است صفی چک شود، باید در لوپ سفارشی چرخید:
            if run_loop_callback:
                import threading
                def cef_loop():
                    while True:
                        run_loop_callback()
                        time.sleep(0.1)
                t = threading.Thread(target=cef_loop, daemon=True)
                t.start()

            cef.MessageLoop()
            cef.Shutdown()

        elif backend == "webview":
            import webview
            webview.create_window("آزمایشگاه مجازی", url=url, width=1200, height=800)

            # پاس دادن تابع مانیتورینگ صف به متد start بومیِ خود pywebview
            # این تابع در یک ترد بک‌گراند اجرا می‌شود اما با ساختار پنجره‌ها تداخل ندارد
            if run_loop_callback:
                webview.start(run_loop_callback)
            else:
                webview.start()

        else:
            import webbrowser
            webbrowser.open(url)
            if run_loop_callback:
                while True:
                    try:
                        run_loop_callback()
                        time.sleep(0.1)
                    except KeyboardInterrupt:
                        break

    def __del__(self):
        """پاکسازی سرور هنگام حذف شیء"""
        if self._server:
            self._server.shutdown()
            self._server.server_close()


# ===== LabManager =====

# ===== LabManager =====

class LabManager:
    def __init__(self, build_dir=None):
        if build_dir is None:
            build_dir = Path(__file__).resolve().parent.parent / "build"
        self._api = LabAPI(build_dir)
        self._explorer = LabExplorer(self._api)
        self._lab_servers = []
        self._ui_queue = queue.Queue()
        self._is_running = True  # فلگ کنترلی برای متوقف کردن حلقه وایل هنگام خروج

    def show_explorer(self):
        """نمایش صفحه کاوشگر آزمایشگاه‌ها"""
        self._is_running = True
        self._explorer.show(
            open_callback=self._queue_open_lab_request,
            run_loop_callback=self._check_ui_queue
        )
        # به محض اینکه متد بالا (که بلاکینگ است) تمام شود، یعنی کاربر پنجره اصلی را بسته است
        self._is_running = False

    def _queue_open_lab_request(self, sim_name, grade, subject, locale="fa"):
        """ثبت سریع درخواست در صف"""
        self._ui_queue.put((sim_name, grade, subject, locale))

    def _check_ui_queue(self):
        """حلقه‌ای که مدام صف را چک می‌کند و با بسته شدن برنامه کاملاً متوقف می‌شود"""
        import time
        import queue

        # تا زمانی که پنجره اصلی باز است این حلقه می‌چرخد
        while self._is_running:
            try:
                task = self._ui_queue.get(timeout=0.2)
                self._execute_open_lab(*task)
                self._ui_queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Error processing UI queue: {e}")

            time.sleep(0.05)

        logger.info("UI Queue thread stopped cleanly.")

    def _execute_open_lab(self, sim_name, grade, subject, locale="fa"):
        """ایجاد آنی پنجره و سپس بارگذاری محتوا در پس‌زمینه"""
        backend = _detect_backend()

        if backend == "webview":
            import webview
            # ۱. فوراً پنجره را با یک دیتای موقت لودینگ باز می‌کنیم تا کاربر حس کند برنامه سریع است
            loading_html = "data:text/html;charset=utf-8,<html><body style='background:#1e1e1e;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;'><h2>در حال بارگذاری آزمایشگاه... لطفا شکیبا باشید</h2></body></html>"
            new_window = webview.create_window(sim_name, url=loading_html, width=1024, height=768)

            # ۲. حالا منطق سنگین (لود اچ‌تی‌ام‌ال و سوکت) را به یک ترد داخلی می‌سپاریم تا UI فریز نشود
            import threading
            def bg_load_and_serve():
                html = self._api.get_lab(sim_name, grade, subject)
                if not html:
                    logger.error(f"Failed to get lab: {sim_name}")
                    return

                import socket
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', 0))
                    port = s.getsockname()[1]

                class LabHandler(SimpleHTTPRequestHandler):
                    def do_GET(handler_self):
                        try:
                            handler_self.send_response(200)
                            handler_self.send_header('Content-Type', 'text/html; charset=utf-8')
                            handler_self.end_headers()
                            handler_self.wfile.write(html.encode('utf-8'))
                        except Exception as e:
                            logger.error(f"Error serving lab: {e}")
                    def log_message(handler_self, f, *a): pass

                server = HTTPServer(('127.0.0.1', port), LabHandler)
                self._lab_servers.append(server)

                s_thread = threading.Thread(target=server.serve_forever, daemon=True)
                s_thread.start()

                # ۳. سرور آماده است؛ حالا آدرس پنجره لودینگ را به آدرس واقعی تغییر می‌دهیم
                final_url = f'http://127.0.0.1:{port}/?locale={locale}'
                new_window.load_url(final_url)

            # اجرای پروسه ساخت سرور در پس‌زمینه پنجره‌ی تازه متولد شده
            threading.Thread(target=bg_load_and_serve, daemon=True).start()

        else:
            # برای سایر بک‌اندهایی مثل مرورگر عادی یا CEF که ساختار متفاوتی دارند
            html = self._api.get_lab(sim_name, grade, subject)
            if not html: return

            import threading
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]

            class LabHandler(SimpleHTTPRequestHandler):
                def do_GET(handler_self):
                    handler_self.send_response(200)
                    handler_self.send_header('Content-Type', 'text/html; charset=utf-8')
                    handler_self.end_headers()
                    handler_self.wfile.write(html.encode('utf-8'))
                def log_message(handler_self, f, *a): pass

            server = HTTPServer(('127.0.0.1', port), LabHandler)
            self._lab_servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()

            url = f'http://127.0.0.1:{port}/?locale={locale}'
            if backend == "cef":
                import cefpython3 as cef # type: ignore
                cef.CreateBrowserSync(url=url, window_title=sim_name)
            else:
                import webbrowser
                webbrowser.open(url)

    def open_lab(self, sim_name, grade, subject, locale="fa"):
        self._execute_open_lab(sim_name, grade, subject, locale)

    def run(self):
        """اجرای کاوشگر (blocking)"""
        self.show_explorer()

    def __del__(self):
        """پاکسازی سرورها"""
        self._is_running = False
        for server in self._lab_servers:
            try:
                server.shutdown()
                server.server_close()
            except:
                pass
