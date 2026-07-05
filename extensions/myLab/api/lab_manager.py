# myLab/api/lab_manager.py - Final with local HTTP server
import sys
import logging
import tempfile
import webbrowser
import os
import threading
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

_myLab_dir = Path(__file__).resolve().parent.parent
if str(_myLab_dir) not in sys.path:
    sys.path.insert(0, str(_myLab_dir))

from module.smart_lab_loader import Grade, Subject
from api import PhETLabAPI

logger = logging.getLogger(__name__)


def _detect_backend() -> str:
    py_ver = sys.version_info[:2]
    if py_ver <= (3, 9):
        try:
            import cefpython3  # noqa
            return "cef"
        except ImportError:
            pass
    try:
        import webview  # noqa
        return "webview"
    except ImportError:
        pass
    return "browser"


def _start_local_server(html: str, locale: str = "fa") -> str:
    """Start a local HTTP server to serve one HTML file and return the URL."""
    # Find a free port
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]

    # Store HTML in a dict accessible by the handler
    _server_data['html'] = html
    _server_data['port'] = port

    class PhETHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/?locale=') or self.path == '/':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(_server_data['html'].encode('utf-8'))
            else:
                super().do_GET()

        def log_message(self, format, *args):
            pass  # Silence logs

    server = HTTPServer(('127.0.0.1', port), PhETHandler)

    # Start server in background thread
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f'http://127.0.0.1:{port}/?locale={locale}'
    return url


# Shared data between main thread and HTTP handler
_server_data = {'html': '', 'port': 0}


class _CEFBackend:
    def __init__(self):
        import cefpython3 as cef
        self._cef = cef
        self._initialized = False
        self._browsers = {}

    def _init(self):
        if not self._initialized:
            try: self._cef.Initialize()
            except TypeError: self._cef.Initialize(settings={"multi_threaded_message_loop": False})
            self._initialized = True

    def open(self, key, html, title, locale="fa"):
        self._init()
        url = _start_local_server(html, locale)
        browser = self._cef.CreateBrowserSync(url=url, window_title=title)
        self._browsers[key] = browser

    def close(self, key):
        if key in self._browsers:
            try: self._browsers.pop(key).CloseBrowser()
            except: pass

    def close_all(self):
        for k in list(self._browsers): self.close(k)
        if self._initialized:
            self._cef.Shutdown()
            self._initialized = False

    def run(self):
        if self._initialized: self._cef.MessageLoop()


class _WebViewBackend:
    def __init__(self):
        import webview
        self._webview = webview
        self._windows = {}

    def open(self, key, html, title, locale="fa"):
        url = _start_local_server(html, locale)
        w = self._webview.create_window(title=title, url=url, width=1024, height=768)
        self._windows[key] = w

    def close(self, key):
        if key in self._windows:
            try: self._windows.pop(key).destroy()
            except: pass

    def close_all(self):
        for k in list(self._windows): self.close(k)

    def run(self):
        if self._windows: self._webview.start()


class _BrowserBackend:
    def __init__(self):
        self._files = {}

    def open(self, key, html, title, locale="fa"):
        tmp_path = Path(tempfile.gettempdir()) / f"phet_{key}.html"
        tmp_path.write_text(html, encoding='utf-8')
        webbrowser.open(f'file:///{tmp_path}?locale={locale}')
        self._files[key] = str(tmp_path)

    def close(self, key):
        if key in self._files:
            try: Path(self._files.pop(key)).unlink(missing_ok=True)
            except: pass

    def close_all(self):
        for k in list(self._files): self.close(k)

    def run(self):
        pass


class LabManager:
    def __init__(self, build_dir: str = None):
        if build_dir is None:
            build_dir = Path(__file__).resolve().parent.parent / "build"
        self._api = PhETLabAPI(build_dir)
        self._backend_type = _detect_backend()
        self._backend = {"cef": _CEFBackend, "webview": _WebViewBackend, "browser": _BrowserBackend}[self._backend_type]()
        logger.info("LabManager using backend: %s", self._backend_type)

    def open_lab(self, sim_name, grade, subject, locale="fa"):
        key = f"{sim_name}_{grade}-{subject}"
        html = self._api.get_lab(sim_name, grade, subject)
        if html is None: return
        self._backend.open(key, html, f"{sim_name} ({grade}-{subject})", locale=locale)

    def close_lab(self, sim_name, grade, subject):
        self._backend.close(f"{sim_name}_{grade}-{subject}")

    def close_all(self):
        self._backend.close_all()

    def run(self):
        self._backend.run()

    def list_available_labs(self, grade=None, subject=None):
        return self._api.list_labs(grade=grade, subject=subject)

    def search_labs(self, query):
        return self._api.search(query)

    def get_tree(self):
        return self._api.get_tree()

    def get_stats(self):
        return self._api.get_stats()

    @property
    def api(self):
        return self._api

    @property
    def backend(self):
        return self._backend_type
