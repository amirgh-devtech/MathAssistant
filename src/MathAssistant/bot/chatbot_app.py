"""
Math Chat Bot - Bridge-Integrated Version
=========================================
A PyQt6 desktop application that communicates with a local bridge server,
which forwards requests to a browser-based API client (e.g., Groq, OpenAI)
to bypass network restrictions.

This version removes direct Gemini API calls and uses the BridgeClient class
to send/receive messages via the bridge server.
"""

import sys
import os
import json
import re
import time
import random
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import io
import base64
import numpy as np
from dotenv import load_dotenv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLineEdit, QPushButton, QLabel, QMessageBox,
                             QFileDialog)
from PyQt6.QtCore import (Qt, QThread, pyqtSignal, QObject, QUrl, QTimer,
                          QThreadPool, QRunnable)
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWebEngineWidgets import QWebEngineView

# --- Bridge Client (replaces Gemini libraries) ---
import requests
from requests.exceptions import RequestException, Timeout

# --- Load environment variables (only for optional config) ---
load_dotenv()  # Not strictly needed but kept for potential future use

# ============================================================================
# Bridge Client Class
# ============================================================================

class BridgeClient:
    """Simple client for the local bridge server."""
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.timeout = 2  # seconds for HTTP requests
        self.poll_interval = 0.5  # seconds between response polls
        self.max_wait = 60  # maximum seconds to wait for a response

    def check_health(self) -> bool:
        """Return True if the bridge server is reachable."""
        try:
            r = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
            return r.status_code == 200
        except RequestException:
            return False

    def submit_request(self, prompt: str) -> str:
        """
        Submit a text prompt to the bridge server.
        Returns the request_id on success, raises Exception on failure.
        """
        try:
            r = self.session.post(
                f"{self.base_url}/api/v1/request",
                json={"payload": prompt, "type": "text"},
                timeout=self.timeout
            )
            if r.status_code == 202:
                data = r.json()
                return data.get("request_id")
            else:
                raise Exception(f"Bridge server returned status {r.status_code}")
        except RequestException as e:
            raise Exception(f"Cannot submit request: {e}")

    def get_response(self, request_id: str, timeout_seconds: int = 60) -> str:
        """
        Poll the bridge server for a response matching the given request_id.
        Returns the response text, or raises Exception on timeout/error.
        """
        start = time.time()
        while time.time() - start < timeout_seconds:
            try:
                r = self.session.get(
                    f"{self.base_url}/api/v1/response",
                    timeout=self.timeout
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == "completed":
                        resp = data.get("response", {})
                        # Verify request_id matches if provided
                        if resp.get("id") == request_id or not resp.get("id"):
                            return resp.get("payload", "")
                # If empty or not our response, keep polling
                time.sleep(self.poll_interval)
            except RequestException:
                time.sleep(self.poll_interval)
        raise TimeoutError(f"No response received for request {request_id} within {timeout_seconds}s")

# ============================================================================
# Modular Code
# ============================================================================

class BotManager(QObject):
    """Manages communication with the AI through the bridge server."""
    chunk_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, model_name='default', parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self.bridge = BridgeClient()
        self.full_response_text = ""
        self._is_running = False
        self.retry_count = 0
        self.max_retries = 2
        self.conversation_history = []  # List of dicts: {"role": "user"/"assistant", "content": str}
        self.system_prompt = self._get_system_prompt()

    def setup_model(self) -> bool:
        """Check if the bridge server is available."""
        if self.bridge.check_health():
            print("Bridge server is reachable.")
            return True
        else:
            self.error_occurred.emit(
                "خطا در اتصال به سرور پل.",
                "Bridge server is not running. Please start bridge_server.py first."
            )
            return False

    def _get_system_prompt(self) -> str:
        """Return the system instruction as a single string."""
        return """
        شما یک معلم ریاضی متخصص و صبور هستید که به دانش‌آموزان در سطوح مختلف کمک می‌کنید.
        لطفاً به سوالات ریاضی پاسخ دهید، مفاهیم را به صورت ساده توضیح دهید و مسائل را گام به گام حل کنید.

        **مهم و حیاتی:**
        * همیشه به زبان فارسی صحبت کنید.
        * از کلمه "ولو" استفاده نکنید.
        * فرمول‌ها و عبارات ریاضی را با استفاده از **raw LaTeX** بنویسید.
        * برای فرمول‌های **درون‌متنی** از `$`. مثال: `$a^2 + b^2 = c^2$`
        * برای فرمول‌های **نمایشی** از `$$` در یک خط جداگانه.
        * برای متن عادی از فرمت‌بندی استاندارد Markdown استفاده کنید.
        * به شدت از ایجاد هرگونه جایگاه‌دهنده یا عبارات غیر-LaTeX برای فرمول‌ها خودداری کنید.
        * پاسخ‌های شما باید مستقیماً به سوال کاربر مرتبط باشد.
        * اگر کاربر پیامی با قصد خداحافظی ارسال کرد، یک خداحافظی ساده بگویید.
        * **برای نمودارها:** اگر خواسته شد نمودار بکشید، توضیحات را بنویسید و کد پایتون را در یک بلوک با شناسه `python_graph` قرار دهید.
        """
        # (The detailed graph instructions are included in the actual system prompt)

    def _build_context_prompt(self, user_message: str) -> str:
        """Combine system prompt and conversation history into a single prompt."""
        parts = [self.system_prompt.strip()]
        # Include recent conversation (up to last 5 exchanges)
        for msg in self.conversation_history[-10:]:
            if msg["role"] == "user":
                parts.append(f"User: {msg['content']}")
            else:
                parts.append(f"Assistant: {msg['content']}")
        parts.append(f"User: {user_message}")
        return "\n\n".join(parts)

    def get_welcome_message(self):
        """Fetch a welcome message through the bridge."""
        self._is_running = True
        self.full_response_text = ""
        welcome_prompt = "یک پیام خوشامدگویی دوستانه، کوتاه، متفاوت و پویا برای یک دانش آموز نسل زد و آلفایی بدون استفاده از کلمه ولو بفرستید. فقط سلام و احوالپرسی و دعوت به پرسیدن سوال و انگیزه دادن به دانش آموز."
        self._send_via_bridge(welcome_prompt, is_welcome=True)

    def send_message(self, content):
        """Send user message (text only for now) through the bridge."""
        self._is_running = True
        self.full_response_text = ""
        # Extract text from content (list of strings or dicts)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and 'text' in item:
                    text_parts.append(item['text'])
                # Ignore images for now
            user_text = " ".join(text_parts)
        else:
            user_text = str(content)

        if not user_text:
            self.error_occurred.emit("پیام خالی است.", "")
            self.finished.emit()
            self._is_running = False
            return

        self._send_via_bridge(user_text, is_welcome=False)

    def _send_via_bridge(self, user_text: str, is_welcome: bool = False):
        """Internal method to handle bridge communication with retries."""
        if not self._is_running:
            return

        # Build full prompt with context (except for welcome, which is standalone)
        if is_welcome:
            prompt = self.system_prompt + "\n\n" + user_text
        else:
            prompt = self._build_context_prompt(user_text)

        for attempt in range(self.max_retries + 1):
            try:
                # Submit request to bridge
                request_id = self.bridge.submit_request(prompt)
                # Wait for response
                response_text = self.bridge.get_response(request_id, timeout_seconds=120)

                if response_text:
                    self.full_response_text = response_text
                    # Simulate streaming by splitting into chunks
                    words = response_text.split()
                    chunk_size = 4
                    for i in range(0, len(words), chunk_size):
                        if not self._is_running:
                            break
                        chunk = " ".join(words[i:i+chunk_size]) + " "
                        self.chunk_received.emit(chunk)
                        QThread.msleep(30)
                    # Update conversation history
                    if not is_welcome:
                        self.conversation_history.append({"role": "user", "content": user_text})
                        self.conversation_history.append({"role": "assistant", "content": response_text})
                    self.finished.emit()
                    return
                else:
                    raise Exception("Empty response from bridge")
            except Exception as e:
                if attempt < self.max_retries and self._is_running:
                    self.error_occurred.emit(
                        f"خطا در ارتباط با پل. تلاش مجدد ({attempt+1}/{self.max_retries})...",
                        str(e)
                    )
                    QThread.msleep(2000)  # Wait before retry
                else:
                    self.error_occurred.emit(
                        "خطا در ارتباط با پل مرورگر. لطفاً bridge_server.py و bridge.html را بررسی کنید.",
                        str(e)
                    )
                    self.finished.emit()
                    break
        self._is_running = False

    def stop(self):
        self._is_running = False
        self.conversation_history = []

# ============================================================================
# The rest of the code remains exactly the same as the original
# ============================================================================

class ChatHistoryManager:
    """Manages saving and loading chat history."""
    def __init__(self, filename="chat_history.json"):
        self.filename = filename

    def save_history(self, history):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving history: {e}")
            return False

    def load_history(self):
        if not os.path.exists(self.filename):
            return None
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            return None

class GraphGenerator(QObject):
    """Processes and displays Python graph code."""
    graph_ready = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str, str)

    def run_code(self, code_text, description_text):
        """
        Processes and displays Python graph code.
        """
        try:
            plt.close('all')
            fig_width_inches = 8
            fig_height_inches = 6
            dpi = 200

            font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "Vazirmatn-Regular.ttf")
            if os.path.exists(font_path):
                fm.fontManager.addfont(font_path)
                persian_font = fm.FontProperties(fname=font_path)
                plt.rcParams['font.family'] = persian_font.get_name()
                plt.rcParams['font.size'] = 12
            else:
                plt.rcParams['font.family'] = 'sans-serif'
                plt.rcParams['font.size'] = 12

            # Use a high-contrast style for readability on a dark background
            plt.style.use('seaborn-v0_8-darkgrid')

            # Override some style parameters for better readability
            plt.rcParams.update({
                'axes.unicode_minus': False,
                'axes.facecolor': '#2b2b2b',
                'figure.facecolor': '#2b2b2b',
                'text.color': '#e0e0e0',
                'axes.labelcolor': '#e0e0e0',
                'xtick.color': '#e0e0e0',
                'ytick.color': '#e0e0e0',
                'axes.edgecolor': '#e0e0e0',
                'grid.color': '#555555',
                'grid.linewidth': 0.8,
                'figure.titlesize': 14,
                'axes.titlesize': 14,
                'axes.labelsize': 12,
                'lines.linewidth': 2.5,
                'lines.markersize': 8
            })

            plt.ioff()
            fig, ax = plt.subplots(figsize=(fig_width_inches, fig_height_inches), dpi=dpi)

            match = re.search(r'```python_graph\n(.*?)```', code_text, re.DOTALL)
            if not match:
                match = re.search(r'```python\n(.*?)```', code_text, re.DOTALL)

            if not match:
                raise ValueError("Graph code block not found.")

            graph_code = match.group(1).strip()

            # Use exec with a limited scope to prevent unwanted side effects
            exec_globals = {'plt': plt, 'np': np, 'pd': pd, 'ax': ax, 'fig': fig}

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            exec(graph_code, exec_globals)

            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1)
            buf.seek(0)
            encoded_string = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
            plt.close(fig)

            self.graph_ready.emit(encoded_string, description_text)

        except Exception as e:
            self.error_occurred.emit("خطا در اجرای کد نمودار.", str(e))

class Worker(QRunnable):
    """A generic QRunnable to execute tasks in a Thread Pool."""
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.fn(*self.args, **self.kwargs)

# --- Main Application Class ---
class MathChatBotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ربات معلم ریاضی")
        self.setGeometry(100, 100, 800, 650)
        self.setMinimumSize(600, 500)

        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "Vazirmatn-Regular.ttf")
        if os.path.exists(font_path):
            self.vazirmatn_font_id = QFontDatabase.addApplicationFont(font_path)
            if self.vazirmatn_font_id == -1:
                 print("Warning: Vazirmatn font file could not be loaded.")
        else:
            print("Warning: Vazirmatn-Regular.ttf not found. Using default fonts.")

        self.threadpool = QThreadPool()

        self.bot_manager = BotManager()
        self.bot_manager.chunk_received.connect(self.append_bot_chunk_web)
        self.bot_manager.error_occurred.connect(self.display_error)
        self.bot_manager.finished.connect(self.response_finished)

        self.graph_generator = GraphGenerator()
        self.graph_generator.graph_ready.connect(self.append_graph_to_chat)
        self.graph_generator.error_occurred.connect(self.display_error)

        self.history_manager = ChatHistoryManager()
        self.chat_history_list = []
        self.image_path = None
        self.is_bot_processing = False
        self.current_bot_message_id = None
        self.current_bot_content_id = None
        self.is_page_ready = False
        self.js_queue = []

        self.setup_ui()
        # Now check bridge instead of Gemini
        if not self.bot_manager.setup_model():
            self.user_entry.setEnabled(False)
            self.send_button.setEnabled(False)

    def run_js_when_ready(self, script):
        if self.is_page_ready:
            self.history_view.page().runJavaScript(script)
        else:
            self.js_queue.append(script)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("QWidget { background-color: #222222; color: #E0E0E0; }")
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)

        self.new_chat_button = QPushButton("گفتگوی جدید")
        self.new_chat_button.setFont(QFont("Vazirmatn", 10))
        self.new_chat_button.setStyleSheet(self.get_button_style())
        self.new_chat_button.clicked.connect(self.new_chat)
        toolbar_layout.addWidget(self.new_chat_button)

        self.save_button = QPushButton("ذخیره گفتگو")
        self.save_button.setFont(QFont("Vazirmatn", 10))
        self.save_button.setStyleSheet(self.get_button_style())
        self.save_button.clicked.connect(self.save_chat_history)
        toolbar_layout.addWidget(self.save_button)

        self.load_button = QPushButton("بارگذاری گفتگو")
        self.load_button.setFont(QFont("Vazirmatn", 10))
        self.load_button.setStyleSheet(self.get_button_style())
        self.load_button.clicked.connect(self.load_chat_history_from_file)
        toolbar_layout.addWidget(self.load_button)

        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)

        self.history_view = QWebEngineView()
        self.history_view.setStyleSheet("""
            QWebEngineView {
                border: none;
                border-radius: 12px;
                background-color: #333333;
            }
        """)
        main_layout.addWidget(self.history_view)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.user_entry = QLineEdit()
        self.user_entry.setPlaceholderText("سوال یا مسئله ریاضی خود را بپرسید...")
        self.user_entry.setFont(QFont("Vazirmatn", 11))
        self.user_entry.setStyleSheet("""
            QLineEdit {
                border: 1px solid #404040;
                border-radius: 10px;
                padding: 10px 12px;
                background-color: #353535;
                color: #E8EAED;
                selection-background-color: #008B8B;
                font-family: 'Vazirmatn';
            }
            QLineEdit:focus {
                border: 1px solid #008B8B;
            }
        """)
        self.user_entry.setToolTip("سوال یا مسئله ریاضی خود را در اینجا بنویسید و Enter بزنید.")
        self.user_entry.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.user_entry)

        self.upload_button = QPushButton("🖼️")
        self.upload_button.setFont(QFont("Vazirmatn", 11, QFont.Weight.Bold))
        self.upload_button.setToolTip("آپلود تصویر مسئله ریاضی.")
        self.upload_button.setStyleSheet(self.get_send_button_style())
        self.upload_button.clicked.connect(self.upload_image)
        input_layout.addWidget(self.upload_button)

        self.send_button = QPushButton("ارسال")
        self.send_button.setFont(QFont("Vazirmatn", 11, QFont.Weight.Bold))
        self.send_button.setStyleSheet(self.get_send_button_style())
        self.send_button.setToolTip("پیام خود را ارسال کنید.")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        main_layout.addLayout(input_layout)

        self.status_label = QLabel("آماده دریافت پیام...")
        self.status_label.setFont(QFont("Vazirmatn", 9))
        self.status_label.setStyleSheet("color: #bbbbbb; margin-top: 5px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.status_label)

        self.history_view.setHtml(self.get_html_template(), QUrl("about:blank"))
        self.history_view.loadFinished.connect(self.on_page_load_finished)

    def get_button_style(self):
        return """
            QPushButton {
                background-color: #404040;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 8px;
                font-family: 'Vazirmatn';
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """

    def get_send_button_style(self):
        return """
            QPushButton {
                background-color: #008B8B;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 10px;
                font-family: 'Vazirmatn';
            }
            QPushButton:hover {
                background-color: #006b6b;
            }
            QPushButton:pressed {
                background-color: #004c4c;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #A0A0A0;
            }
        """

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب تصویر", "", "Image Files (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            self.user_entry.setText("تصویر انتخاب شد. حالا سوال خود را بپرسید.")
            self.user_entry.setFocus()
            self.upload_button.setEnabled(False)
            self.status_label.setText("تصویر آماده ارسال است.")

    def send_message(self, user_input=None):
        user_text = self.user_entry.text().strip()

        content_to_send = []
        user_message_for_display = ""

        if self.image_path:
            # Since bridge currently supports text only, we'll show a warning
            QMessageBox.warning(self, "پشتیبانی نشده", "ارسال تصویر در این نسخه از طریق پل پشتیبانی نمی‌شود.")
            self.reset_ui_for_new_input()
            return

        if user_text:
            content_to_send.append(user_text)
            user_message_for_display = user_text

        if not content_to_send:
            return

        if self.is_bot_processing:
            QMessageBox.information(self, "در حال پردازش", "لطفاً منتظر بمانید تا پاسخ قبلی تکمیل شود.")
            return

        self.append_full_message("شما", user_message_for_display, message_type="user")

        history_item = {'role': 'user', 'parts': [{'text': user_text}]}
        self.chat_history_list.append(history_item)

        self.user_entry.clear()
        self.image_path = None
        self.upload_button.setEnabled(True)
        self.set_ui_processing_state(True)
        self.status_label.setText("در حال پردازش درخواست...")
        self.append_full_message("معلم ریاضی", "", message_type="bot")

        worker = Worker(self.bot_manager.send_message, content_to_send)
        self.threadpool.start(worker)

    def perform_initial_setup(self):
        self.is_bot_processing = True
        self.status_label.setText("در حال دریافت پیام خوشامدگویی...")
        self.append_full_message("معلم ریاضی", "", message_type="bot")
        worker = Worker(self.bot_manager.get_welcome_message)
        self.threadpool.start(worker)

    def new_chat(self):
        self.chat_history_list = []
        self.bot_manager.conversation_history = []
        self.is_page_ready = False
        self.history_view.setHtml(self.get_html_template(), QUrl("about:blank"))
        # No need to reinitialize anything else; BotManager already has fresh history

    def save_chat_history(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره تاریخچه گفتگو", "chat_history.json", "JSON Files (*.json)")
        if file_path:
            clean_history = self.chat_history_list
            if self.history_manager.save_history(clean_history):
                QMessageBox.information(self, "موفق", "تاریخچه گفتگو با موفقیت ذخیره شد.")
            else:
                QMessageBox.warning(self, "خطا", "خطا در ذخیره تاریخچه.")

    def load_chat_history_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "بارگذاری تاریخچه گفتگو", "", "JSON Files (*.json)")
        if file_path:
            loaded_history = self.history_manager.load_history()
            if loaded_history:
                self.chat_history_list = loaded_history
                # Clear current BotManager history and rebuild from loaded
                self.bot_manager.conversation_history = []
                for msg in loaded_history:
                    if msg['role'] == 'user':
                        # Extract text from parts
                        text = ""
                        for part in msg['parts']:
                            if isinstance(part, dict) and 'text' in part:
                                text += part['text']
                            elif isinstance(part, str):
                                text += part
                        self.bot_manager.conversation_history.append({"role": "user", "content": text})
                    elif msg['role'] == 'model':
                        text = ""
                        for part in msg['parts']:
                            if isinstance(part, dict) and 'text' in part:
                                text += part['text']
                            elif isinstance(part, str):
                                text += part
                        self.bot_manager.conversation_history.append({"role": "assistant", "content": text})

                self.is_page_ready = False
                self.history_view.setHtml(self.get_html_template(), QUrl("about:blank"))
            else:
                QMessageBox.warning(self, "خطا", "فایل تاریخچه معتبر نیست.")

    def on_page_load_finished(self, ok):
        if ok:
            self.is_page_ready = True
            for script in self.js_queue:
                self.history_view.page().runJavaScript(script)
            self.js_queue.clear()

            if self.chat_history_list:
                for message in self.chat_history_list:
                    role = message['role']
                    message_type = "user" if role == "user" else "bot"
                    sender_name = "شما" if role == "user" else "معلم ریاضی"

                    content_parts = message['parts']
                    message_content = ""
                    for part in content_parts:
                        if isinstance(part, dict) and part.get('mime_type') and part.get('data'):
                            if part['mime_type'].startswith('image/'):
                                message_content += f"<br><img src='data:{part['mime_type']};base64,{part['data']}' style='max-width:200px; max-height:200px; border-radius:8px; margin-top:10px;' />"
                        elif isinstance(part, str):
                            message_content += part
                        elif isinstance(part, dict) and 'text' in part:
                            message_content += part['text']

                    self.append_full_message(sender_name, message_content, message_type)
            else:
                self.perform_initial_setup()

            self.history_view.page().runJavaScript("document.body.style.opacity = '1';")

    def set_ui_processing_state(self, processing):
        self.is_bot_processing = processing
        self.user_entry.setEnabled(not processing)
        self.send_button.setEnabled(not processing)
        self.upload_button.setEnabled(not processing)
        if not processing:
            self.user_entry.setPlaceholderText("سوال یا مسئله ریاضی دیگری بپرسید...")
            self.status_label.setText("آماده دریافت پیام...")
            self.user_entry.setFocus()
            self.current_bot_message_id = None
            self.current_bot_content_id = None
        else:
            self.user_entry.setPlaceholderText("ربات در حال پاسخگویی...")
            self.status_label.setText("در حال پردازش درخواست...")

    def response_finished(self, bot_response=None):
        if bot_response is None:
            bot_response = self.bot_manager.full_response_text

        # Regex to find the graph code block and extract the text before it
        match = re.search(r'(.*?)```python_graph\n(.*?)```', bot_response, re.DOTALL)
        if match:
            text_content = match.group(1).strip()
            code_content = match.group(2).strip()

            # Update the chat history with the full bot response
            self.chat_history_list.append({'role': 'model', 'parts': [{'text': bot_response}]})

            # First, display the text content
            self.finalize_bot_response(text_content, finalize_ui=False)

            # Then, run the graph generation in a separate thread
            self.set_ui_processing_state(True)
            self.status_label.setText("در حال تولید نمودار...")
            worker = Worker(self.graph_generator.run_code, f'```python_graph\n{code_content}```', text_content)
            self.threadpool.start(worker)
        else:
            # If no graph code is found, finalize the response normally
            self.finalize_bot_response(bot_response)

    def finalize_bot_response(self, bot_response, finalize_ui=True):
        if not self.current_bot_content_id: return

        # Split the text content into the main message and the label
        main_message = bot_response

        # If there's a graph, the first line is the label, the rest is the main message
        lines = bot_response.split('\n')
        if len(lines) > 1 and any("```python_graph" in s for s in self.bot_manager.full_response_text.splitlines()):
            main_message = "\n".join(lines[1:])

        formatted_html_final = self.format_message_to_html(main_message)
        escaped_html_final = self.javascript_escape_string(formatted_html_final)

        script = f"""
        var botContentDiv = document.getElementById('{self.current_bot_content_id}');
        if (botContentDiv) {{
            var typingIndicator = botContentDiv.querySelector('.typing-indicator');
            if (typingIndicator) {{ typingIndicator.remove(); }}
            botContentDiv.innerHTML = "{escaped_html_final}";
            botContentDiv.classList.remove('no-mathjax');
            if (typeof MathJax !== 'undefined' && MathJax.Hub) {{
                MathJax.Hub.Queue(["Typeset", MathJax.Hub, botContentDiv]);
            }}
            window.scrollTo(0, document.body.scrollHeight);
        }}
        """
        self.run_js_when_ready(script)

        if finalize_ui:
            self.chat_history_list.append({'role': 'model', 'parts': [{'text': bot_response}]})
            self.set_ui_processing_state(False)

            # Optional exit phrase handling
            gemini_exit_phrases = ["خداحافظ", "خدا نگهدار", "بای", "تا بعد", "پایان گفتگو", "goodbye", "farewell", "bye-bye", "see you later", "تمام شد"]
            if any(phrase.lower() in bot_response.lower() for phrase in gemini_exit_phrases):
                pass  # No automatic close

    def append_graph_to_chat(self, encoded_image, description_text):
        if not self.current_bot_content_id: return

        # Extract the first line to use as the label
        label_text = description_text.split('\n')[0]
        formatted_description_html = self.format_message_to_html(label_text)
        escaped_description = self.javascript_escape_string(formatted_description_html)

        script = f"""
        var botContentDiv = document.getElementById('{self.current_bot_content_id}');
        if (botContentDiv) {{
            var typingIndicator = botContentDiv.querySelector('.typing-indicator');
            if (typingIndicator) {{ typingIndicator.remove(); }}

            var graphHtml = `<img src="data:image/png;base64,{encoded_image}" class="graph-image" alt="Math Plot" />`;
            botContentDiv.innerHTML = botContentDiv.innerHTML + `<div class="graph-container">` + graphHtml + `<div class="graph-description">` + `{escaped_description}` + `</div></div>`;

            botContentDiv.classList.remove('no-mathjax');
            if (typeof MathJax !== 'undefined' && MathJax.Hub) {{
                MathJax.Hub.Queue(["Typeset", MathJax.Hub, botContentDiv]);
            }}

            window.scrollTo(0, document.body.scrollHeight);
        }}
        """
        self.run_js_when_ready(script)
        self.set_ui_processing_state(False)

    def display_error(self, error_message, error_detail=""):
        self.append_full_message("خطا", error_message, message_type="error")

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("خطا در برنامه")
        msg_box.setText(f"**خطا:** {error_message}")
        msg_box.setInformativeText("برای مشاهده جزئیات فنی بیشتر، روی دکمه 'جزئیات' کلیک کنید.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setDetailedText(error_detail)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                font-family: 'Vazirmatn';
                font-size: 11pt;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
            }
            QMessageBox QPushButton {
                background-color: #008B8B;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 5px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #006b6b;
            }
            QMessageBox QPushButton:pressed {
                background-color: #004c4c;
            }
            QTextEdit {
                background-color: #353535;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 5px;
            }
        """)
        msg_box.exec()

        self.set_ui_processing_state(False)

    def format_message_to_html(self, message_text):
        if not message_text or not message_text.strip(): return ""
        html_content = markdown.markdown(message_text, extensions=['fenced_code', 'tables', 'nl2br'])
        return html_content

    def javascript_escape_string(self, text):
        return text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')

    def append_full_message(self, sender, message_text, message_type="bot"):
        msg_id = f"msg_{int(time.time() * 1000)}_{random.randint(0, 100000)}"
        content_id = f"content_{msg_id}"

        sender_html = sender
        css_class = "bot-message"
        initial_content_html = ""

        if message_type == "user":
            css_class = "user-message"
            initial_content_html = self.format_message_to_html(message_text)
        elif message_type == "error":
            css_class = "error-message"
            initial_content_html = f"<p>{message_text}</p>"
        elif message_type == "bot":
            initial_content_html = """
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
            """
            self.current_bot_message_id = msg_id
            self.current_bot_content_id = content_id

        escaped_html = self.javascript_escape_string(initial_content_html)

        script = f"""
        var chatContainer = document.getElementById('chat-container');
        if (chatContainer) {{
            var messageHtml = `<div id="{msg_id}" class="message {css_class}"><span class="sender-name">{sender_html}:</span><div id="{content_id}" class="message-content no-mathjax">{escaped_html}</div></div>`;
            chatContainer.insertAdjacentHTML('beforeend', messageHtml);
            var el = document.getElementById('{content_id}');
            if (el && typeof MathJax !== 'undefined' && MathJax.Hub && messageHtml.indexOf('typing-indicator') === -1) {{
                MathJax.Hub.Queue(["Typeset", MathJax.Hub, el]);
            }}
            window.scrollTo(0, document.body.scrollHeight);
        }}
        """
        self.run_js_when_ready(script)

    def append_bot_chunk_web(self, chunk_text):
        if not self.current_bot_content_id: return

        if "```python_graph" in chunk_text:
            self.run_js_when_ready(f"""
                var botContentDiv = document.getElementById('{self.current_bot_content_id}');
                if (botContentDiv) {{
                    var typingIndicator = botContentDiv.querySelector('.typing-indicator');
                    if (typingIndicator) {{ typingIndicator.remove(); }}
                    botContentDiv.innerHTML = 'در حال ساخت نمودار...';
                    botContentDiv.classList.add('no-mathjax');
                    window.scrollTo(0, document.body.scrollHeight);
                }}
            """)
        else:
            escaped_chunk = self.javascript_escape_string(chunk_text)
            script = f"""
            var botContentDiv = document.getElementById('{self.current_bot_content_id}');
            if (botContentDiv) {{
                var typingIndicator = botContentDiv.querySelector('.typing-indicator');
                if (typingIndicator) {{ typingIndicator.remove(); }}
                botContentDiv.innerHTML += "{escaped_chunk}";
                botContentDiv.classList.remove('no-mathjax');
                if (typeof MathJax !== 'undefined' && MathJax.Hub) {{
                    MathJax.Hub.Queue(["Typeset", MathJax.Hub, botContentDiv]);
                }}
                window.scrollTo(0, document.body.scrollHeight);
            }}
            """
            self.run_js_when_ready(script)

    def get_html_template(self):
        return f"""
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <title>تاریخچه گفتگو</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.0.3/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
            <script type="text/x-mathjax-config">
            MathJax.Hub.Config({{
                tex2jax: {{
                    inlineMath: [['$','$'], ['\\\\(','\\\\)']],
                    displayMath: [['$$','$$'], ['\\\\[','\\\\]']],
                    processEscapes: true,
                    ignoreClass: "no-mathjax",
                    skipTags: ["script","noscript","style","textarea","pre","code","annotation","annotation-xml"]
                }},
                "HTML-CSS": {{
                    preferredFont: "TeX",
                    availableFonts: ["STIX","TeX"],
                    linebreaks: {{ automatic: true }},
                    styles: {{ ".MathJax_Display": {{ "text-align": "center !important", "direction": "ltr !important", "margin": "15px 0 !important" }} }},
                    scale: 100
                }},
                CommonHTML: {{ linebreaks: {{ automatic: true }}, scale: 100 }},
                SVG: {{ linebreaks: {{ automatic: true }}, scale: 100 }},
                menuSettings: {{ zoom: "Double-Click" }},
                showProcessingMessages: false,
                messageStyle: "none",
                errorSettings: {{
                    message: ["[Math Processing Error]"],
                    style: {{color: "#c0392b", "font-style": "italic", "background-color": "#444", "padding": "5px", "border-radius": "5px"}},
                    formatError: function (jax, err) {{ return "مشکل در فرمول: " + err.message + " (متن: " + jax.originalText + ")"; }}
                }}
            }});
            MathJax.Hub.Register.MessageHook("End Process", function (message) {{ window.scrollTo(0, document.body.scrollHeight); }});
            </script>
            <script>
            var mathjaxSources = [
                "https://cdn.jsdelivr.net/npm/mathjax@2.7.9/MathJax.js?config=TeX-MML-AM_CHTML",
                "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.9/MathJax.js?config=TeX-MML-AM_CHTML"
            ];
            function loadScript(url, callback) {{
                var script = document.createElement('script');
                script.type = 'text/javascript';
                script.async = true;
                script.src = url;
                script.onload = function() {{ if (callback) callback(true); }};
                script.onerror = function() {{ console.error("Failed to load script: " + url); if (callback) callback(false); }};
                document.head.appendChild(script);
            }}
            var currentSourceIndex = 0;
            function tryLoadMathJax() {{
                if (currentSourceIndex < mathjaxSources.length) {{
                    var url = mathjaxSources[currentSourceIndex];
                    loadScript(url, function(success) {{
                        if (!success) {{
                            currentSourceIndex++;
                            tryLoadMathJax();
                        }} else {{
                            console.log("MathJax loaded successfully from: " + url);
                        }}
                    }});
                }} else {{
                    console.error("All MathJax sources failed to load.");
                }}
            }}
            document.addEventListener('DOMContentLoaded', tryLoadMathJax);
            </script>
            <style>
            body {{
                font-family: 'Vazirmatn', 'Segoe UI', sans-serif;
                margin: 0; padding: 15px; background-color: #222222;
                overflow-y: auto; color: #E8EAED; font-size: 16px;
                line-height: 1.6; word-wrap: break-word; direction: rtl;
                opacity: 0;
            }}
            /* Custom Scrollbar */
            body::-webkit-scrollbar {{ width: 10px; }}
            body::-webkit-scrollbar-track {{ background: #2b2b2b; border-radius: 5px; }}
            body::-webkit-scrollbar-thumb {{ background: #555555; border-radius: 5px; }}
            body::-webkit-scrollbar-thumb:hover {{ background: #777777; }}

            .message {{
                margin-bottom: 20px; padding: 15px 20px; border-radius: 12px;
                max-width: 85%; word-wrap: break-word; line-height: 1.6;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3); position: relative;
                opacity: 0;
                transform: translateY(10px);
                animation: fadeIn 0.4s ease-out forwards;
            }}
            .user-message {{
                background-color: #008B8B; margin-left: auto; margin-right: 0;
                color: #ffffff; text-align: right;
            }}
            .bot-message {{
                background-color: #1a1a1a; margin-right: auto; margin-left: 0;
                color: #E8EAED; text-align: right;
                border-left: 4px solid #008B8B;
            }}
            .error-message {{
                background-color: #c0392b; color: #ffffff; margin-right: auto;
                margin-left: 0; text-align: right; border-left: 4px solid #e74c3c;
            }}
            .graph-message {{
                background-color: #333333; border-left: none; padding: 0;
                margin: 0 auto 20px auto; max-width: 95%;
                box-shadow: none;
                text-align: center;
            }}
            .graph-image {{
                max-width: 100%;
                height: auto;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            }}
            .graph-description {{
                margin-top: 10px;
                padding: 10px 15px;
                background-color: #353535;
                border-radius: 8px;
                text-align: right;
                font-style: italic;
                font-size: 0.9em;
                color: #B0B0B0;
            }}
            .sender-name {{ font-weight: 600; margin-bottom: 8px; display: block;
                font-size: 0.9em; opacity: 0.9; color: #cccccc;
            }}
            .user-message .sender-name {{ color: #f0f0f0; }}
            .message-content {{ font-size: 1.0em; direction: rtl; }}
            .message-content .MathJax_Display, .message-content .MathJax {{
                direction: ltr !important; text-align: center !important;
            }}
            .message-content p {{ margin: 0 0 12px 0 !important;
                line-height: 1.7 !important; text-align: right;
            }}
            .message-content p:last-child {{ margin-bottom: 0 !important; }}
            .message-content strong {{ font-weight: 700 !important; color: #ffffff !important; }}
            .user-message strong {{ color: #f0f0f0 !important; }}
            .message-content em {{ font-style: italic !important; color: #d0d0d0 !important; }}
            .message-content pre {{ background-color: #1a1a1a; padding: 10px;
                border-radius: 8px; overflow-x: auto; margin: 10px 0; direction: ltr;
                font-family: 'Fira Code', 'JetBrains Mono', 'Courier New', monospace;
            }}
            .message-content code {{ font-family: 'Fira Code', 'JetBrains Mono', 'Courier New', monospace;
                font-size: 0.9em; color: #c8c8c8;
            }}
            .message-content code:not([class*="language-"]) {{ background-color: #4a4a4a;
                padding: 2px 4px; border-radius: 4px; font-size: 0.85em;
            }}

            /* Typing Indicator CSS */
            .typing-indicator {{
                padding: 5px 10px;
                border-radius: 12px;
            }}
            .typing-indicator span {{
                display: inline-block;
                background-color: #E8EAED;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin: 0 2px;
                opacity: 0.6;
                animation: bounce 1.4s infinite ease-in-out;
            }}
            .typing-indicator span:nth-child(2) {{
                animation-delay: -1.2s;
            }}
            .typing-indicator span:nth-child(3) {{
                animation-delay: -1.0s;
            }}
            @keyframes bounce {{
                0%, 80%, 100% {{ transform: translateY(0); }}
                40% {{ transform: translateY(-8px); }}
            }}

            /* Fade-in animation */
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            </style>
        </head>
        <body>
            <div id="chat-container"></div>
        </body>
        </html>
        """

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")

        window = MathChatBotApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        input("Press Enter to exit...")
