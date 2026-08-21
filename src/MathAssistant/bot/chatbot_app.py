# src/MathAssistant/bot/chatbot_app.py

"""
Math Chat Bot - Production Grade Implementation
================================================
A professional PyQt6 desktop application with advanced features:
- Real-time streaming responses
- Multimodal support (text + images)
- Advanced memory management
- Graph visualization
- Chat history persistence
- Professional UI/UX

Author: Professional Development Team
Version: 2.0.0
License: MIT
"""

import sys
import os
import json
import re
import time
import random
import base64
import hashlib
import sqlite3
import asyncio
import uuid
import threading
import mimetypes
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty

# Third-party imports
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import pandas as pd
import numpy as np
import io
from PIL import Image as PILImage
from dotenv import load_dotenv

# PyQt6 imports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLineEdit, QPushButton, QLabel, QMessageBox,
                             QFileDialog, QTextEdit, QScrollArea, QFrame,
                             QGridLayout, QSpacerItem, QSizePolicy, QProgressBar,
                             QMenu, QSystemTrayIcon, QDialog, QComboBox,
                             QCheckBox, QSpinBox, QTabWidget, QSplitter)
from PyQt6.QtCore import (Qt, QThread, pyqtSignal, QObject, QUrl, QTimer,
                          QThreadPool, QRunnable, QSize, QPoint, QRect,
                          QPropertyAnimation, QEasingCurve, QSettings,
                          QByteArray, QBuffer, QIODevice, QMimeData, pyqtSlot)
from PyQt6.QtGui import (QFont, QFontDatabase, QIcon, QPixmap, QImage,
                        QPainter, QColor, QTextCursor, QKeySequence,
                        QShortcut, QAction, QPalette, QBrush, QClipboard)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

# Bridge client
from bridge_client import BridgeClient, ClientConfig, BridgeResponse, ResponseStatus

# Load environment variables
load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

class AppConfig:
    """Application configuration."""

    APP_NAME = "Math Chat Bot"
    APP_VERSION = "2.0.0"
    ORGANIZATION_NAME = "MathAssistant"

    # Window Settings
    DEFAULT_WIDTH = 900
    DEFAULT_HEIGHT = 700
    MIN_WIDTH = 600
    MIN_HEIGHT = 500

    # UI Settings
    FONT_FAMILY = "Vazirmatn"
    FONT_SIZE = 11
    DEFAULT_FONT_SIZE = 16

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = os.path.join(os.getcwd(), "assets")
    FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
    CACHE_DIR = os.path.join(ASSETS_DIR, "cache")
    DATA_DIR = os.path.join(ASSETS_DIR, "data")

    # Database
    DATABASE_PATH = os.path.join(DATA_DIR, "chat_history.db")

    # Bridge Server
    BRIDGE_URL = "http://127.0.0.1:5000"

    # Threading
    MAX_THREADS = 10
    THREAD_TIMEOUT = 5000  # ms

    # Memory
    MAX_SHORT_TERM_MEMORY = 20
    MAX_LONG_TERM_MEMORY = 100

    # Streaming
    CHUNK_SIZE = 4  # words per chunk
    CHUNK_DELAY = 30  # ms
    MAX_STREAM_TIME = 120  # seconds

    # Graph
    GRAPH_DPI = 200
    GRAPH_WIDTH = 8
    GRAPH_HEIGHT = 6

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        for directory in [cls.ASSETS_DIR, cls.FONTS_DIR, cls.CACHE_DIR, cls.DATA_DIR]:
            os.makedirs(directory, exist_ok=True)


# ============================================================================
# Data Models
# ============================================================================

class MessageRole(Enum):
    """Message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


class MessageType(Enum):
    """Message types."""
    TEXT = "text"
    IMAGE = "image"
    GRAPH = "graph"
    MULTIMODAL = "multimodal"
    CODE = "code"
    ERROR = "error"


@dataclass
class ChatMessage:
    """Represents a chat message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.USER
    content: str = ""
    message_type: MessageType = MessageType.TEXT
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    images: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "images": self.images
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            role=MessageRole(data.get("role", "user")),
            content=data.get("content", ""),
            message_type=MessageType(data.get("message_type", "text")),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
            images=data.get("images", [])
        )


@dataclass
class Conversation:
    """Represents a conversation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Conversation"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: List[ChatMessage] = field(default_factory=list)

    def add_message(self, message: ChatMessage):
        self.messages.append(message)
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [msg.to_dict() for msg in self.messages]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        conv = cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", "New Conversation"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time())
        )
        conv.messages = [ChatMessage.from_dict(msg) for msg in data.get("messages", [])]
        return conv


# ============================================================================
# Database Manager
# ============================================================================

class DatabaseManager:
    """Manages SQLite database for chat history."""

    def __init__(self, db_path: str = AppConfig.DATABASE_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata TEXT
                )
            ''')

            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            ''')

            # Images table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id TEXT PRIMARY KEY,
                    message_id TEXT,
                    image_data TEXT NOT NULL,
                    image_type TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                )
            ''')

            # Indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp
                ON messages(timestamp)
            ''')

            conn.commit()

    def save_conversation(self, conversation: Conversation) -> bool:
        """Save or update a conversation."""
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Save conversation
                cursor.execute('''
                    INSERT OR REPLACE INTO conversations
                    (id, title, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    conversation.id,
                    conversation.title,
                    conversation.created_at,
                    conversation.updated_at,
                    json.dumps({})
                ))

                # Save messages
                for msg in conversation.messages:
                    cursor.execute('''
                        INSERT OR REPLACE INTO messages
                        (id, conversation_id, role, content, message_type, timestamp, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        msg.id,
                        conversation.id,
                        msg.role.value,
                        msg.content,
                        msg.message_type.value,
                        msg.timestamp,
                        json.dumps(msg.metadata)
                    ))

                conn.commit()
                return True

        except Exception as e:
            print(f"Error saving conversation: {e}")
            return False

    def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load a conversation from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Load conversation
                cursor.execute('''
                    SELECT id, title, created_at, updated_at
                    FROM conversations
                    WHERE id = ?
                ''', (conversation_id,))

                conv_data = cursor.fetchone()
                if not conv_data:
                    return None

                conversation = Conversation(
                    id=conv_data[0],
                    title=conv_data[1],
                    created_at=conv_data[2],
                    updated_at=conv_data[3]
                )

                # Load messages
                cursor.execute('''
                    SELECT id, role, content, message_type, timestamp, metadata
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY timestamp ASC
                ''', (conversation_id,))

                for msg_data in cursor.fetchall():
                    message = ChatMessage(
                        id=msg_data[0],
                        role=MessageRole(msg_data[1]),
                        content=msg_data[2],
                        message_type=MessageType(msg_data[3]),
                        timestamp=msg_data[4],
                        metadata=json.loads(msg_data[5]) if msg_data[5] else {}
                    )
                    conversation.messages.append(message)

                return conversation

        except Exception as e:
            print(f"Error loading conversation: {e}")
            return None

    def get_recent_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of recent conversations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, title, created_at, updated_at,
                           (SELECT COUNT(*) FROM messages WHERE conversation_id = conversations.id) as msg_count
                    FROM conversations
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (limit,))

                return [
                    {
                        'id': row[0],
                        'title': row[1],
                        'created_at': row[2],
                        'updated_at': row[3],
                        'message_count': row[4]
                    }
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            print(f"Error getting conversations: {e}")
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
                cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))

                conn.commit()
                return True

        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False

    def search_messages(self, query: str, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for messages."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if conversation_id:
                    cursor.execute('''
                        SELECT m.id, m.role, m.content, m.timestamp, c.title
                        FROM messages m
                        JOIN conversations c ON m.conversation_id = c.id
                        WHERE m.conversation_id = ? AND m.content LIKE ?
                        ORDER BY m.timestamp DESC
                    ''', (conversation_id, f'%{query}%'))
                else:
                    cursor.execute('''
                        SELECT m.id, m.role, m.content, m.timestamp, c.title
                        FROM messages m
                        JOIN conversations c ON m.conversation_id = c.id
                        WHERE m.content LIKE ?
                        ORDER BY m.timestamp DESC
                    ''', (f'%{query}%',))

                return [
                    {
                        'id': row[0],
                        'role': row[1],
                        'content': row[2],
                        'timestamp': row[3],
                        'conversation_title': row[4]
                    }
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            print(f"Error searching messages: {e}")
            return []


# ============================================================================
# Memory Manager
# ============================================================================

class MemoryManager:
    """Manages short-term and long-term memory for conversations."""

    def __init__(self, short_term_limit: int = AppConfig.MAX_SHORT_TERM_MEMORY,
                 long_term_limit: int = AppConfig.MAX_LONG_TERM_MEMORY):
        self.short_term_limit = short_term_limit
        self.long_term_limit = long_term_limit
        self.short_term_memory: List[Dict[str, str]] = []
        self.long_term_memory: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add_to_short_term(self, role: str, content: str):
        """Add message to short-term memory."""
        with self._lock:
            self.short_term_memory.append({
                'role': role,
                'content': content,
                'timestamp': time.time()
            })

            # Trim if exceeds limit
            if len(self.short_term_memory) > self.short_term_limit:
                self.short_term_memory = self.short_term_memory[-self.short_term_limit:]

    def add_to_long_term(self, key: str, value: Any, importance: float = 1.0):
        """Add item to long-term memory."""
        with self._lock:
            self.long_term_memory[key] = {
                'value': value,
                'importance': importance,
                'timestamp': time.time(),
                'access_count': 0
            }

            # Trim if exceeds limit
            if len(self.long_term_memory) > self.long_term_limit:
                # Remove least important/accessed items
                sorted_items = sorted(
                    self.long_term_memory.items(),
                    key=lambda x: (x[1]['importance'], x[1]['access_count'])
                )
                for key_to_remove, _ in sorted_items[:len(self.long_term_memory) - self.long_term_limit]:
                    del self.long_term_memory[key_to_remove]

    def get_from_long_term(self, key: str) -> Optional[Any]:
        """Get item from long-term memory."""
        with self._lock:
            item = self.long_term_memory.get(key)
            if item:
                item['access_count'] += 1
                return item['value']
            return None

    def get_context_for_prompt(self) -> str:
        """Get formatted context for prompt."""
        context_parts = []

        # Add short-term memory
        for msg in self.short_term_memory[-10:]:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")

        # Add important long-term memory
        important_items = sorted(
            self.long_term_memory.items(),
            key=lambda x: x[1]['importance'],
            reverse=True
        )[:5]

        if important_items:
            context_parts.append("\n**Important context from previous conversations:**")
            for key, item in important_items:
                context_parts.append(f"- {key}: {item['value']}")

        return "\n".join(context_parts)

    def clear_short_term(self):
        """Clear short-term memory."""
        with self._lock:
            self.short_term_memory.clear()

    def clear_all(self):
        """Clear all memory."""
        with self._lock:
            self.short_term_memory.clear()
            self.long_term_memory.clear()

    def detect_topics(self, text: str) -> List[str]:
        """Detect topics from text for long-term memory."""
        topics = []

        # Mathematical concepts
        math_topics = {
            'equation': ['معادله', 'equation'],
            'integral': ['انتگرال', 'integral'],
            'derivative': ['مشتق', 'derivative'],
            'trigonometry': ['مثلثات', 'trigonometry'],
            'geometry': ['هندسه', 'geometry'],
            'algebra': ['جبر', 'algebra'],
            'probability': ['احتمال', 'probability'],
            'statistics': ['آمار', 'statistics'],
            'matrix': ['ماتریس', 'matrix'],
            'vector': ['بردار', 'vector'],
            'limit': ['حد', 'limit'],
            'function': ['تابع', 'function']
        }

        for topic, keywords in math_topics.items():
            if any(keyword in text.lower() for keyword in keywords):
                topics.append(topic)

        return topics[:5]

    def extract_important_info(self, text: str, response: str):
        """Extract important information from conversation."""
        topics = self.detect_topics(text)

        for topic in topics:
            # Extract relevant response snippet
            snippet = response[:200] if len(response) > 200 else response
            self.add_to_long_term(topic, snippet, importance=0.7)


# ============================================================================
# Bot Manager
# ============================================================================

class BotManager(QObject):
    """Manages communication with the AI through the bridge server."""

    # Signals
    chunk_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str, str)
    finished = pyqtSignal()
    processing_started = pyqtSignal()
    status_changed = pyqtSignal(str)
    graph_generated = pyqtSignal(str, str)  # image_base64, description

    def __init__(self, model_name: str = 'default', parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self.bridge = BridgeClient(base_url=AppConfig.BRIDGE_URL)
        self.memory_manager = MemoryManager()
        self.graph_generator = None  # Will be set by main app
        self.full_response_text = ""
        self._is_running = False
        self.retry_count = 0
        self.max_retries = 3
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = self._get_system_prompt()
        self.current_request_id: Optional[str] = None

        # Response cache
        self.response_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 3600  # 1 hour

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

        **برای نمودارها:**
        * اگر خواسته شد نمودار بکشید، توضیحات را بنویسید و کد پایتون را در یک بلوک با شناسه `python_graph` قرار دهید.
        * از دستور `plt.show()` استفاده نکنید.
        * فقط از matplotlib برای رسم نمودار استفاده کنید.
        * کد باید کامل و قابل اجرا باشد.
        """

    def setup_model(self) -> bool:
        """Check if the bridge server is available."""
        try:
            health = self.bridge.check_health()
            if health.get("status") == "healthy":
                self.status_changed.emit("Bridge server connected")
                return True
            else:
                self.error_occurred.emit(
                    "خطا در اتصال به سرور پل.",
                    "Bridge server is not running. Please start bridge_server.py first."
                )
                return False
        except Exception as e:
            self.error_occurred.emit(
                "خطا در اتصال به سرور پل.",
                str(e)
            )
            return False

    def _build_context_prompt(self, user_message: str) -> str:
        """Build prompt with memory context."""
        parts = [self.system_prompt.strip()]

        # Add memory context
        memory_context = self.memory_manager.get_context_for_prompt()
        if memory_context:
            parts.append(f"**Context:**\n{memory_context}")

        # Add recent conversation
        for msg in self.conversation_history[-10:]:
            if msg["role"] == "user":
                parts.append(f"User: {msg['content']}")
            else:
                parts.append(f"Assistant: {msg['content']}")

        parts.append(f"User: {user_message}")
        return "\n\n".join(parts)

    def _check_cache(self, prompt: str) -> Optional[str]:
        """Check if response is cached."""
        cache_key = hashlib.md5(prompt.encode()).hexdigest()

        cached = self.response_cache.get(cache_key)
        if cached and time.time() - cached['timestamp'] < self.cache_ttl:
            return cached['response']

        return None

    def _store_cache(self, prompt: str, response: str):
        """Store response in cache."""
        cache_key = hashlib.md5(prompt.encode()).hexdigest()

        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }

        # Clean old cache
        current_time = time.time()
        expired_keys = [
            key for key, value in self.response_cache.items()
            if current_time - value['timestamp'] > self.cache_ttl
        ]
        for key in expired_keys:
            del self.response_cache[key]

    def get_welcome_message(self):
        """Fetch a welcome message through the bridge."""
        self._is_running = True
        self.full_response_text = ""
        self.processing_started.emit()

        welcome_prompt = "یک پیام خوشامدگویی دوستانه، کوتاه، متفاوت و پویا برای یک دانش آموز نسل زد و آلفایی بدون استفاده از کلمه ولو بفرستید. فقط سلام و احوالپرسی و دعوت به پرسیدن سوال و انگیزه دادن به دانش آموز."

        self._send_via_bridge(welcome_prompt, is_welcome=True)

    def send_message(self, content: Union[str, List[Any]], images: Optional[List[str]] = None):
        """Send user message through the bridge."""
        self._is_running = True
        self.full_response_text = ""
        self.processing_started.emit()

        # Extract text content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and 'text' in item:
                    text_parts.append(item['text'])
            user_text = " ".join(text_parts)
        else:
            user_text = str(content)

        if not user_text and not images:
            self.error_occurred.emit("پیام خالی است.", "")
            self.finished.emit()
            self._is_running = False
            return

        # Add to short-term memory
        self.memory_manager.add_to_short_term('user', user_text)

        # Send based on content type
        if images:
            self._send_multimodal_via_bridge(user_text, images)
        else:
            self._send_via_bridge(user_text, is_welcome=False)

    def _send_via_bridge(self, user_text: str, is_welcome: bool = False):
        """Internal method to handle bridge communication."""
        if not self._is_running:
            return

        # Build prompt
        if is_welcome:
            prompt = self.system_prompt + "\n\n" + user_text
        else:
            prompt = self._build_context_prompt(user_text)

        # Check cache
        cached_response = self._check_cache(prompt)
        if cached_response:
            self._process_response(cached_response, user_text, is_welcome)
            return

        for attempt in range(self.max_retries + 1):
            try:
                # Submit request
                self.current_request_id = self.bridge.submit_request(
                    prompt,
                    priority="normal"
                )

                if not self.current_request_id:
                    raise Exception("Failed to submit request")

                # Wait for response
                response = self.bridge.wait_for_response(
                    self.current_request_id,
                    timeout_seconds=AppConfig.MAX_STREAM_TIME
                )

                if response and response.status == ResponseStatus.SUCCESS:
                    response_text = response.payload

                    # Store in cache
                    self._store_cache(prompt, response_text)

                    # Process response
                    self._process_response(response_text, user_text, is_welcome)
                    return
                else:
                    raise Exception("No response received")

            except Exception as e:
                if attempt < self.max_retries and self._is_running:
                    self.error_occurred.emit(
                        f"خطا در ارتباط با پل. تلاش مجدد ({attempt+1}/{self.max_retries})...",
                        str(e)
                    )
                    QThread.msleep(2000)
                else:
                    self.error_occurred.emit(
                        "خطا در ارتباط با پل مرورگر.",
                        str(e)
                    )
                    self.finished.emit()
                    break

        self._is_running = False

    def _send_multimodal_via_bridge(self, user_text: str, images: List[str]):
        """Send multimodal request."""
        if not self._is_running:
            return

        prompt = self._build_context_prompt(user_text)

        try:
            # Upload images first
            image_ids = []
            for image_path in images:
                image_id = self.bridge.upload_image(image_path)
                if image_id:
                    image_ids.append(image_id)

            if not image_ids:
                raise Exception("Failed to upload images")

            # Submit multimodal request
            self.current_request_id = self.bridge.submit_multimodal_request(
                user_text,
                images=image_ids
            )

            if not self.current_request_id:
                raise Exception("Failed to submit multimodal request")

            # Wait for response
            response = self.bridge.wait_for_response(
                self.current_request_id,
                timeout_seconds=AppConfig.MAX_STREAM_TIME
            )

            if response and response.status == ResponseStatus.SUCCESS:
                response_text = response.payload
                self._process_response(response_text, user_text, False)
            else:
                raise Exception("No response received")

        except Exception as e:
            self.error_occurred.emit(
                "خطا در پردازش تصویر",
                str(e)
            )
            self.finished.emit()

        self._is_running = False

    def _process_response(self, response_text: str, user_text: str, is_welcome: bool):
        """Process and stream response."""
        if not self._is_running:
            return

        self.full_response_text = response_text

        # Simulate streaming
        words = response_text.split()
        chunk_size = AppConfig.CHUNK_SIZE

        for i in range(0, len(words), chunk_size):
            if not self._is_running:
                break
            chunk = " ".join(words[i:i+chunk_size]) + " "
            self.chunk_received.emit(chunk)
            QThread.msleep(AppConfig.CHUNK_DELAY)

        # Update memory
        if not is_welcome:
            self.conversation_history.append({"role": "user", "content": user_text})
            self.conversation_history.append({"role": "assistant", "content": response_text})

            # Update memory
            self.memory_manager.add_to_short_term('assistant', response_text)
            self.memory_manager.extract_important_info(user_text, response_text)

        # Check for graph code
        if self._contains_graph_code(response_text):
            self._process_graph_code(response_text)
        else:
            self.finished.emit()

    def _contains_graph_code(self, text: str) -> bool:
        """Check if text contains graph code."""
        return bool(re.search(r'```python_graph\n(.*?)```', text, re.DOTALL))

    def _process_graph_code(self, text: str):
        """Extract and process graph code."""
        match = re.search(r'(.*?)```python_graph\n(.*?)```', text, re.DOTALL)
        if match:
            text_content = match.group(1).strip()
            code_content = match.group(2).strip()

            # Generate graph if graph_generator is available
            if self.graph_generator:
                self.graph_generator.generate_graph(code_content, text_content)
            else:
                self.finished.emit()

    def stop(self):
        """Stop processing."""
        self._is_running = False
        self.current_request_id = None

    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.memory_manager.clear_short_term()


# ============================================================================
# Graph Generator
# ============================================================================

class GraphGenerator(QObject):
    """Processes and displays Python graph code."""

    graph_ready = pyqtSignal(str, str)  # image_base64, description
    error_occurred = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_matplotlib()

    def _init_matplotlib(self):
        """Initialize matplotlib with Persian font support."""
        try:
            # Try to load Vazirmatn font
            font_path = os.path.join(AppConfig.FONTS_DIR, "Vazirmatn-Regular.ttf")
            if os.path.exists(font_path):
                fm.fontManager.addfont(font_path)
                persian_font = fm.FontProperties(fname=font_path)
                plt.rcParams['font.family'] = persian_font.get_name()
                plt.rcParams['font.size'] = 12
            else:
                plt.rcParams['font.family'] = 'sans-serif'
                plt.rcParams['font.size'] = 12

            # Configure style
            try:
                plt.style.use('seaborn-v0_8-darkgrid')
            except:
                plt.style.use('dark_background')

            # Override style parameters
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

        except Exception as e:
            print(f"Error initializing matplotlib: {e}")

    def generate_graph(self, code_text: str, description_text: str):
        """Generate graph from Python code."""
        try:
            plt.close('all')

            # Extract code
            match = re.search(r'```python\n(.*?)```', code_text, re.DOTALL)
            if not match:
                match = re.search(r'```python_graph\n(.*?)```', code_text, re.DOTALL)

            if not match:
                # Try without code block markers
                graph_code = code_text.strip()
            else:
                graph_code = match.group(1).strip()

            # Execute code
            exec_globals = {
                'plt': plt,
                'np': np,
                'pd': pd,
                'Figure': Figure,
                'FigureCanvasAgg': FigureCanvasAgg
            }

            # Create figure
            fig, ax = plt.subplots(
                figsize=(AppConfig.GRAPH_WIDTH, AppConfig.GRAPH_HEIGHT),
                dpi=AppConfig.GRAPH_DPI
            )

            exec_globals['fig'] = fig
            exec_globals['ax'] = ax

            # Execute code
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            exec(graph_code, exec_globals)

            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1)
            buf.seek(0)

            # Convert to base64
            encoded_string = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
            plt.close(fig)

            self.graph_ready.emit(encoded_string, description_text)

        except Exception as e:
            self.error_occurred.emit("خطا در اجرای کد نمودار.", str(e))


# ============================================================================
# Worker Threads
# ============================================================================

class WorkerSignals(QObject):
    """Defines signals available from a running worker thread."""

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)


class Worker(QRunnable):
    """Worker thread for executing tasks."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """Execute the function."""
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit((type(e), e, sys.exc_info()[2]))
        finally:
            self.signals.finished.emit()


# ============================================================================
# Main Application Window
# ============================================================================

class MathChatBotApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Ensure directories exist
        AppConfig.ensure_directories()

        # Initialize components
        self.db_manager = DatabaseManager()
        self.bot_manager = BotManager()
        self.graph_generator = GraphGenerator()
        self.bot_manager.graph_generator = self.graph_generator
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(AppConfig.MAX_THREADS)

        # Application state
        self.current_conversation: Optional[Conversation] = None
        self.chat_history_list: List[ChatMessage] = []
        self.image_paths: List[str] = []
        self.is_bot_processing = False
        self.current_bot_message_id: Optional[str] = None
        self.current_bot_content_id: Optional[str] = None
        self.is_page_ready = False
        self.js_queue: List[str] = []

        # Settings
        self.settings = QSettings(AppConfig.ORGANIZATION_NAME, AppConfig.APP_NAME)

        # Setup UI
        self.setup_ui()
        self.setup_connections()
        self.setup_shortcuts()
        self.load_settings()

        # Initialize
        self.init_application()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        self.setGeometry(
            100, 100,
            AppConfig.DEFAULT_WIDTH, AppConfig.DEFAULT_HEIGHT
        )
        self.setMinimumSize(AppConfig.MIN_WIDTH, AppConfig.MIN_HEIGHT)

        # Set window icon
        self.setWindowIcon(self.create_app_icon())

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet(self.get_main_style())

        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Setup components
        self.setup_toolbar(main_layout)
        self.setup_chat_view(main_layout)
        self.setup_input_area(main_layout)
        self.setup_status_bar()

    def setup_toolbar(self, parent_layout):
        """Setup toolbar."""
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)

        # New chat button
        self.new_chat_button = QPushButton("گفتگوی جدید")
        self.new_chat_button.clicked.connect(self.new_chat)
        self.style_button(self.new_chat_button)
        toolbar_layout.addWidget(self.new_chat_button)

        # History button
        self.history_button = QPushButton("تاریخچه")
        self.history_button.clicked.connect(self.show_history)
        self.style_button(self.history_button)
        toolbar_layout.addWidget(self.history_button)

        # Save button
        self.save_button = QPushButton("ذخیره")
        self.save_button.clicked.connect(self.save_chat)
        self.style_button(self.save_button)
        toolbar_layout.addWidget(self.save_button)

        # Export button
        self.export_button = QPushButton("خروجی")
        self.export_button.clicked.connect(self.export_chat)
        self.style_button(self.export_button)
        toolbar_layout.addWidget(self.export_button)

        # Settings button
        self.settings_button = QPushButton("تنظیمات")
        self.settings_button.clicked.connect(self.show_settings)
        self.style_button(self.settings_button)
        toolbar_layout.addWidget(self.settings_button)

        toolbar_layout.addStretch()

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("جستجو در گفتگو...")
        self.search_box.setMaximumWidth(200)
        self.search_box.returnPressed.connect(self.search_messages)
        self.style_input(self.search_box)
        toolbar_layout.addWidget(self.search_box)

        parent_layout.addLayout(toolbar_layout)

    def setup_chat_view(self, parent_layout):
        """Setup chat view."""
        # Create splitter for chat and side panel
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Chat view
        self.history_view = QWebEngineView()
        self.history_view.setHtml(self.get_html_template(), QUrl("about:blank"))
        self.history_view.loadFinished.connect(self.on_page_load_finished)
        self.main_splitter.addWidget(self.history_view)

        # Side panel
        self.side_panel = self.create_side_panel()
        self.side_panel.hide()
        self.main_splitter.addWidget(self.side_panel)

        # Set splitter sizes
        self.main_splitter.setSizes([700, 200])

        parent_layout.addWidget(self.main_splitter)

    def create_side_panel(self) -> QWidget:
        """Create side panel for conversation list."""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # Title
        title = QLabel("گفتگوهای اخیر")
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        layout.addWidget(title)

        # Conversation list
        self.conversation_list = QScrollArea()
        self.conversation_list.setWidgetResizable(True)
        self.conversation_list_widget = QWidget()
        self.conversation_list_layout = QVBoxLayout()
        self.conversation_list_widget.setLayout(self.conversation_list_layout)
        self.conversation_list.setWidget(self.conversation_list_widget)
        layout.addWidget(self.conversation_list)

        return panel

    def setup_input_area(self, parent_layout):
        """Setup input area."""
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        # Text input
        self.user_entry = QLineEdit()
        self.user_entry.setPlaceholderText("سوال یا مسئله ریاضی خود را بپرسید...")
        self.user_entry.setFont(QFont(AppConfig.FONT_FAMILY, AppConfig.FONT_SIZE))
        self.style_input(self.user_entry)
        self.user_entry.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.user_entry, 1)

        # Image upload button
        self.upload_button = QPushButton("📎")
        self.upload_button.setToolTip("پیوست تصویر")
        self.upload_button.clicked.connect(self.upload_image)
        self.style_button(self.upload_button)
        input_layout.addWidget(self.upload_button)

        # Send button
        self.send_button = QPushButton("ارسال")
        self.send_button.clicked.connect(self.send_message)
        self.style_button(self.send_button, primary=True)
        input_layout.addWidget(self.send_button)

        parent_layout.addLayout(input_layout)

        # Image preview area
        self.image_preview_layout = QHBoxLayout()
        parent_layout.addLayout(self.image_preview_layout)

    def setup_status_bar(self):
        """Setup status bar."""
        self.status_label = QLabel("آماده دریافت پیام...")
        self.status_label.setFont(QFont(AppConfig.FONT_FAMILY, 9))
        self.statusBar().addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(100)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)

    def setup_connections(self):
        """Setup signal connections."""
        # Bot manager signals
        self.bot_manager.chunk_received.connect(self.append_bot_chunk)
        self.bot_manager.error_occurred.connect(self.display_error)
        self.bot_manager.finished.connect(self.response_finished)
        self.bot_manager.processing_started.connect(self.processing_started)
        self.bot_manager.status_changed.connect(self.update_status)

        # Graph generator signals
        self.graph_generator.graph_ready.connect(self.append_graph_to_chat)
        self.graph_generator.error_occurred.connect(self.display_error)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+N"), self, self.new_chat)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_chat)
        QShortcut(QKeySequence("Ctrl+H"), self, self.show_history)
        QShortcut(QKeySequence("Escape"), self, self.clear_input)

    def load_settings(self):
        """Load application settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def save_settings(self):
        """Save application settings."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

    def init_application(self):
        """Initialize application."""
        # Check bridge connection
        if not self.bot_manager.setup_model():
            self.disable_input()

        # Load recent conversations
        self.load_recent_conversations()

        # Start new conversation or show welcome
        self.new_chat(show_welcome=True)

    # ========================================================================
    # Event Handlers
    # ========================================================================

    def send_message(self):
        """Send message to bot."""
        user_text = self.user_entry.text().strip()
        images_to_send = self.image_paths.copy()

        if not user_text and not images_to_send:
            return

        if self.is_bot_processing:
            QMessageBox.information(self, "در حال پردازش", "لطفاً منتظر بمانید تا پاسخ قبلی تکمیل شود.")
            return

        # Create message
        message = ChatMessage(
            role=MessageRole.USER,
            content=user_text,
            message_type=MessageType.TEXT if not images_to_send else MessageType.MULTIMODAL,
            images=images_to_send
        )

        # Add to conversation
        if self.current_conversation:
            self.current_conversation.add_message(message)
            self.chat_history_list.append(message)

        # Display message
        self.append_full_message("شما", user_text, message_type="user")

        # Display images if any
        for image_path in images_to_send:
            self.display_uploaded_image(image_path)

        # Clear input
        self.user_entry.clear()
        self.clear_image_previews()

        # Process message
        self.set_ui_processing_state(True)
        self.status_label.setText("در حال پردازش درخواست...")
        self.append_full_message("معلم ریاضی", "", message_type="bot")

        # Start worker thread
        worker = Worker(
            self.bot_manager.send_message,
            user_text,
            images_to_send if images_to_send else None
        )
        self.threadpool.start(worker)

    def new_chat(self):
        """Start a new conversation."""
        # Save current conversation
        if self.current_conversation and self.current_conversation.messages:
            self.db_manager.save_conversation(self.current_conversation)

        # Create new conversation
        self.current_conversation = Conversation()
        self.chat_history_list = []
        self.bot_manager.clear_conversation()

        # Clear chat view
        self.history_view.setHtml(self.get_html_template(), QUrl("about:blank"))

        # Show welcome message
        self.perform_initial_setup()

    def save_chat(self):
        """Save current conversation."""
        if not self.current_conversation or not self.current_conversation.messages:
            QMessageBox.information(self, "ذخیره", "گفتگویی برای ذخیره وجود ندارد.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره گفتگو",
            f"chat_{int(time.time())}.json",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(
                        self.current_conversation.to_dict(),
                        f,
                        ensure_ascii=False,
                        indent=4
                    )

                # Also save to database
                self.db_manager.save_conversation(self.current_conversation)

                QMessageBox.information(self, "موفق", "گفتگو با موفقیت ذخیره شد.")

            except Exception as e:
                QMessageBox.warning(self, "خطا", f"خطا در ذخیره گفتگو: {e}")

    def export_chat(self):
        """Export chat to different formats."""
        if not self.current_conversation or not self.current_conversation.messages:
            QMessageBox.information(self, "خروجی", "گفتگویی برای خروجی وجود ندارد.")
            return

        # Create export menu
        menu = QMenu(self)
        menu.addAction("خروجی HTML", self.export_as_html)
        menu.addAction("خروجی Markdown", self.export_as_markdown)

        menu.exec(self.export_button.mapToGlobal(QPoint(0, self.export_button.height())))

    def export_as_html(self):
        """Export conversation as HTML."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "خروجی HTML",
            f"chat_{int(time.time())}.html",
            "HTML Files (*.html)"
        )

        if file_path:
            html_content = self.generate_html_export()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            QMessageBox.information(self, "موفق", "خروجی HTML ذخیره شد.")

    def export_as_markdown(self):
        """Export conversation as Markdown."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "خروجی Markdown",
            f"chat_{int(time.time())}.md",
            "Markdown Files (*.md)"
        )

        if file_path:
            md_content = self.generate_markdown_export()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            QMessageBox.information(self, "موفق", "خروجی Markdown ذخیره شد.")

    def upload_image(self):
        """Upload image."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "انتخاب تصویر",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )

        for file_path in file_paths:
            if file_path not in self.image_paths:
                self.image_paths.append(file_path)
                self.display_image_preview(file_path)

    def show_history(self):
        """Show/hide history panel."""
        if self.side_panel.isVisible():
            self.side_panel.hide()
            self.main_splitter.setSizes([self.width(), 0])
        else:
            self.side_panel.show()
            self.main_splitter.setSizes([self.width() - 200, 200])
            self.load_recent_conversations()

    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()

    def search_messages(self):
        """Search in messages."""
        query = self.search_box.text().strip()
        if not query:
            return

        results = self.db_manager.search_messages(query)

        if results:
            message = f"نتایج جستجو برای '{query}':\n\n"
            for result in results[:10]:
                message += f"- {result['content'][:100]}...\n"

            QMessageBox.information(self, "نتایج جستجو", message)
        else:
            QMessageBox.information(self, "نتایج جستجو", "نتیجه‌ای یافت نشد.")

    # ========================================================================
    # UI Update Methods
    # ========================================================================

    def append_bot_chunk(self, chunk_text: str):
        """Append streaming chunk to bot message."""
        if not self.current_bot_content_id:
            return

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

    def append_full_message(self, sender: str, message_text: str, message_type: str = "bot"):
        """Append full message to chat."""
        msg_id = f"msg_{int(time.time() * 1000)}_{random.randint(0, 100000)}"
        content_id = f"content_{msg_id}"

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
            var messageHtml = `<div id="{msg_id}" class="message {css_class}">
                <span class="sender-name">{sender}:</span>
                <div id="{content_id}" class="message-content no-mathjax">{escaped_html}</div>
            </div>`;
            chatContainer.insertAdjacentHTML('beforeend', messageHtml);
            window.scrollTo(0, document.body.scrollHeight);
        }}
        """
        self.run_js_when_ready(script)

    def append_graph_to_chat(self, encoded_image: str, description_text: str):
        """Append graph image to chat."""
        if not self.current_bot_content_id:
            return

        label_text = description_text.split('\n')[0] if description_text else ""
        formatted_description_html = self.format_message_to_html(label_text)
        escaped_description = self.javascript_escape_string(formatted_description_html)

        script = f"""
        var botContentDiv = document.getElementById('{self.current_bot_content_id}');
        if (botContentDiv) {{
            var typingIndicator = botContentDiv.querySelector('.typing-indicator');
            if (typingIndicator) {{ typingIndicator.remove(); }}

            var graphHtml = `<img src="data:image/png;base64,{encoded_image}"
                class="graph-image" alt="Math Plot" />`;
            botContentDiv.innerHTML += `<div class="graph-container">` +
                graphHtml +
                `<div class="graph-description">{escaped_description}</div></div>`;

            botContentDiv.classList.remove('no-mathjax');
            if (typeof MathJax !== 'undefined' && MathJax.Hub) {{
                MathJax.Hub.Queue(["Typeset", MathJax.Hub, botContentDiv]);
            }}

            window.scrollTo(0, document.body.scrollHeight);
        }}
        """
        self.run_js_when_ready(script)
        self.set_ui_processing_state(False)

    def display_uploaded_image(self, image_path: str):
        """Display uploaded image in chat."""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()

            encoded_data = base64.b64encode(image_data).decode('utf-8')
            mime_type = self.get_mime_type(image_path)

            msg_id = f"img_msg_{int(time.time() * 1000)}"

            script = f"""
            var chatContainer = document.getElementById('chat-container');
            if (chatContainer) {{
                var imgHtml = `<div id="{msg_id}" class="message user-message">
                    <img src="data:{mime_type};base64,{encoded_data}"
                         class="uploaded-image" style="max-width: 300px; border-radius: 8px;" />
                </div>`;
                chatContainer.insertAdjacentHTML('beforeend', imgHtml);
                window.scrollTo(0, document.body.scrollHeight);
            }}
            """
            self.run_js_when_ready(script)

        except Exception as e:
            print(f"Error displaying image: {e}")

    def display_image_preview(self, image_path: str):
        """Display image preview."""
        try:
            preview_label = QLabel()
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                60, 60,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            preview_label.setPixmap(scaled_pixmap)
            preview_label.setToolTip(image_path)

            close_button = QPushButton("×")
            close_button.setFixedSize(20, 20)
            close_button.clicked.connect(
                lambda checked=False, path=image_path: self.remove_image(path)
            )

            container = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(preview_label)
            layout.addWidget(close_button)
            container.setLayout(layout)

            self.image_preview_layout.addWidget(container)

        except Exception as e:
            print(f"Error creating preview: {e}")

    def remove_image(self, image_path: str):
        """Remove image from upload list."""
        if image_path in self.image_paths:
            self.image_paths.remove(image_path)

        # Clear and rebuild previews
        self.clear_image_previews()
        for path in self.image_paths:
            self.display_image_preview(path)

    def clear_image_previews(self):
        """Clear all image previews."""
        while self.image_preview_layout.count():
            item = self.image_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.image_paths = []
        self.upload_button.setEnabled(True)

    def clear_input(self):
        """Clear input field."""
        self.user_entry.clear()
        self.clear_image_previews()

    def set_ui_processing_state(self, processing: bool):
        """Update UI processing state."""
        self.is_bot_processing = processing
        self.user_entry.setEnabled(not processing)
        self.send_button.setEnabled(not processing)
        self.upload_button.setEnabled(not processing)

        if processing:
            self.progress_bar.show()
            self.progress_bar.setRange(0, 0)
            self.user_entry.setPlaceholderText("ربات در حال پاسخگویی...")
        else:
            self.progress_bar.hide()
            self.user_entry.setPlaceholderText("سوال یا مسئله ریاضی خود را بپرسید...")
            self.user_entry.setFocus()
            self.current_bot_message_id = None
            self.current_bot_content_id = None

    def processing_started(self):
        """Handle processing started signal."""
        self.status_label.setText("در حال پردازش...")

    def response_finished(self, bot_response=None):
        """Handle response finished."""
        if bot_response is None:
            bot_response = self.bot_manager.full_response_text

        # Update conversation
        if self.current_conversation and bot_response:
            assistant_message = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=bot_response,
                message_type=MessageType.TEXT
            )
            self.current_conversation.add_message(assistant_message)

        # Finalize UI
        self.finalize_bot_response(bot_response)

    def finalize_bot_response(self, bot_response: str):
        """Finalize bot response display."""
        if not self.current_bot_content_id:
            return

        # Check for graph code
        match = re.search(r'(.*?)```python_graph\n(.*?)```', bot_response, re.DOTALL)
        if match:
            text_content = match.group(1).strip()
            code_content = match.group(2).strip()

            # Format and display text
            formatted_html = self.format_message_to_html(text_content)
            escaped_html = self.javascript_escape_string(formatted_html)

            script = f"""
            var botContentDiv = document.getElementById('{self.current_bot_content_id}');
            if (botContentDiv) {{
                var typingIndicator = botContentDiv.querySelector('.typing-indicator');
                if (typingIndicator) {{ typingIndicator.remove(); }}
                botContentDiv.innerHTML = "{escaped_html}";
                botContentDiv.classList.remove('no-mathjax');
                if (typeof MathJax !== 'undefined' && MathJax.Hub) {{
                    MathJax.Hub.Queue(["Typeset", MathJax.Hub, botContentDiv]);
                }}
                window.scrollTo(0, document.body.scrollHeight);
            }}
            """
            self.run_js_when_ready(script)

            # Generate graph
            self.status_label.setText("در حال تولید نمودار...")
            worker = Worker(
                self.graph_generator.generate_graph,
                f'```python_graph\n{code_content}```',
                text_content
            )
            self.threadpool.start(worker)
        else:
            # Format and display
            formatted_html = self.format_message_to_html(bot_response)
            escaped_html = self.javascript_escape_string(formatted_html)

            script = f"""
            var botContentDiv = document.getElementById('{self.current_bot_content_id}');
            if (botContentDiv) {{
                var typingIndicator = botContentDiv.querySelector('.typing-indicator');
                if (typingIndicator) {{ typingIndicator.remove(); }}
                botContentDiv.innerHTML = "{escaped_html}";
                botContentDiv.classList.remove('no-mathjax');
                if (typeof MathJax !== 'undefined' && MathJax.Hub) {{
                    MathJax.Hub.Queue(["Typeset", MathJax.Hub, botContentDiv]);
                }}
                window.scrollTo(0, document.body.scrollHeight);
            }}
            """
            self.run_js_when_ready(script)

            self.set_ui_processing_state(False)

    def display_error(self, error_message: str, error_detail: str = ""):
        """Display error message."""
        self.append_full_message("خطا", error_message, message_type="error")

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("خطا در برنامه")
        msg_box.setText(f"خطا: {error_message}")
        msg_box.setInformativeText("برای مشاهده جزئیات فنی بیشتر، روی دکمه 'جزئیات' کلیک کنید.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setDetailedText(error_detail)
        msg_box.setStyleSheet(self.get_dialog_style())
        msg_box.exec()

        self.set_ui_processing_state(False)

    def update_status(self, status: str):
        """Update status bar."""
        self.status_label.setText(status)

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def perform_initial_setup(self):
        """Perform initial setup."""
        self.is_bot_processing = True
        self.status_label.setText("در حال دریافت پیام خوشامدگویی...")
        self.append_full_message("معلم ریاضی", "", message_type="bot")

        worker = Worker(self.bot_manager.get_welcome_message)
        self.threadpool.start(worker)

    def load_recent_conversations(self):
        """Load recent conversations."""
        # Clear current list
        while self.conversation_list_layout.count():
            item = self.conversation_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Load conversations
        conversations = self.db_manager.get_recent_conversations()

        for conv in conversations:
            button = QPushButton(conv['title'])
            button.setToolTip(f"{conv['message_count']} پیام")
            button.clicked.connect(
                lambda checked=False, cid=conv['id']: self.load_conversation(cid)
            )
            self.style_button(button)
            self.conversation_list_layout.addWidget(button)

        # Add stretch at the end
        self.conversation_list_layout.addStretch()

    def load_conversation(self, conversation_id: str):
        """Load a specific conversation."""
        conversation = self.db_manager.load_conversation(conversation_id)

        if conversation:
            self.current_conversation = conversation
            self.chat_history_list = conversation.messages

            # Clear chat view
            self.is_page_ready = False
            self.js_queue.clear()
            self.history_view.setHtml(self.get_html_template(), QUrl("about:blank"))

            # Display messages after page loads
            QTimer.singleShot(500, lambda: self._display_loaded_messages(conversation))

    def _display_loaded_messages(self, conversation: Conversation):
        """Display loaded messages."""
        for message in conversation.messages:
            if message.role == MessageRole.USER:
                sender = "شما"
                msg_type = "user"
            else:
                sender = "معلم ریاضی"
                msg_type = "bot"

            self.append_full_message(sender, message.content, msg_type)

    def format_message_to_html(self, message_text: str) -> str:
        """Format message to HTML."""
        if not message_text or not message_text.strip():
            return ""

        html_content = markdown.markdown(
            message_text,
            extensions=['fenced_code', 'tables', 'nl2br']
        )
        return html_content

    def javascript_escape_string(self, text: str) -> str:
        """Escape string for JavaScript."""
        return text.replace('\\', '\\\\') \
                  .replace('"', '\\"') \
                  .replace("'", "\\'") \
                  .replace('\n', '\\n') \
                  .replace('\r', '\\r')

    def run_js_when_ready(self, script: str):
        """Run JavaScript when page is ready."""
        if self.is_page_ready:
            self.history_view.page().runJavaScript(script)
        else:
            self.js_queue.append(script)

    def on_page_load_finished(self, ok: bool):
        """Handle page load finished."""
        if ok:
            self.is_page_ready = True

            for script in self.js_queue:
                self.history_view.page().runJavaScript(script)

            self.js_queue.clear()
            self.history_view.page().runJavaScript("document.body.style.opacity = '1';")

    def get_mime_type(self, file_path: str) -> str:
        """Get MIME type for file."""
        mime_type = mimetypes.guess_type(file_path)[0]
        return mime_type or 'application/octet-stream'

    def disable_input(self):
        """Disable input fields."""
        self.user_entry.setEnabled(False)
        self.send_button.setEnabled(False)
        self.upload_button.setEnabled(False)

    def create_app_icon(self) -> QIcon:
        """Create application icon."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#008B8B"))

        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "M")
        painter.end()

        return QIcon(pixmap)

    def style_button(self, button: QPushButton, primary: bool = False):
        """Apply style to button."""
        if primary:
            style = """
                QPushButton {
                    background-color: #008B8B;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 10px;
                    font-family: 'Vazirmatn';
                    font-weight: bold;
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
        else:
            style = """
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
                QPushButton:pressed {
                    background-color: #333333;
                }
                QPushButton:disabled {
                    background-color: #303030;
                    color: #808080;
                }
            """

        button.setStyleSheet(style)

    def style_input(self, input_widget):
        """Apply style to input widget."""
        input_widget.setStyleSheet("""
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

    def get_main_style(self) -> str:
        """Get main style sheet."""
        return """
            QWidget {
                background-color: #222222;
                color: #E0E0E0;
            }
            QMainWindow {
                background-color: #222222;
            }
            QMenuBar {
                background-color: #333333;
                color: #E0E0E0;
            }
            QMenuBar::item:selected {
                background-color: #008B8B;
            }
            QMenu {
                background-color: #333333;
                color: #E0E0E0;
            }
            QMenu::item:selected {
                background-color: #008B8B;
            }
            QStatusBar {
                background-color: #333333;
                color: #E0E0E0;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #777777;
            }
        """

    def get_dialog_style(self) -> str:
        """Get dialog style."""
        return """
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
            QTextEdit {
                background-color: #353535;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 5px;
            }
        """

    def generate_html_export(self) -> str:
        """Generate HTML export."""
        if not self.current_conversation:
            return ""

        html_parts = [
            "<!DOCTYPE html>",
            '<html dir="rtl">',
            "<head>",
            '<meta charset="UTF-8">',
            "<title>Chat Export</title>",
            "<style>",
            "body { font-family: 'Vazirmatn', sans-serif; background: #222; color: #eee; padding: 20px; }",
            ".message { margin: 10px 0; padding: 15px; border-radius: 8px; }",
            ".user { background: #008B8B; text-align: right; }",
            ".assistant { background: #333; text-align: right; }",
            "</style>",
            "</head>",
            "<body>"
        ]

        for msg in self.current_conversation.messages:
            role_class = "user" if msg.role == MessageRole.USER else "assistant"
            sender = "شما" if msg.role == MessageRole.USER else "معلم ریاضی"
            html_parts.append(
                f'<div class="message {role_class}">'
                f'<strong>{sender}:</strong><br>'
                f'{self.format_message_to_html(msg.content)}'
                f'</div>'
            )

        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def generate_markdown_export(self) -> str:
        """Generate Markdown export."""
        if not self.current_conversation:
            return ""

        md_parts = [f"# {self.current_conversation.title}\n"]

        for msg in self.current_conversation.messages:
            role = "**شما:**" if msg.role == MessageRole.USER else "**معلم ریاضی:**"
            md_parts.append(f"{role}\n{msg.content}\n")

        return "\n".join(md_parts)

    def closeEvent(self, event):
        """Handle window close."""
        # Save settings
        self.save_settings()

        # Save current conversation
        if self.current_conversation and self.current_conversation.messages:
            self.db_manager.save_conversation(self.current_conversation)

        # Stop bot manager
        self.bot_manager.stop()

        # Wait for threads
        self.threadpool.waitForDone(AppConfig.THREAD_TIMEOUT)

        event.accept()

    def get_html_template(self) -> str:
        """Get HTML template for chat view."""
        return """
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <title>Chat History</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.0.3/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
            <script type="text/x-mathjax-config">
            MathJax.Hub.Config({
                tex2jax: {
                    inlineMath: [['$','$'], ['\\(','\\)']],
                    displayMath: [['$$','$$'], ['\\[','\\]']],
                    processEscapes: true,
                    ignoreClass: "no-mathjax",
                    skipTags: ["script","noscript","style","textarea","pre","code"]
                },
                "HTML-CSS": {
                    preferredFont: "TeX",
                    availableFonts: ["STIX","TeX"],
                    linebreaks: { automatic: true },
                    styles: {
                        ".MathJax_Display": {
                            "text-align": "center !important",
                            "direction": "ltr !important",
                            "margin": "15px 0 !important"
                        }
                    },
                    scale: 100
                },
                CommonHTML: { linebreaks: { automatic: true }, scale: 100 },
                SVG: { linebreaks: { automatic: true }, scale: 100 },
                menuSettings: { zoom: "Double-Click" },
                showProcessingMessages: false,
                messageStyle: "none"
            });
            </script>
            <script src="https://cdn.jsdelivr.net/npm/mathjax@2.7.9/MathJax.js?config=TeX-MML-AM_CHTML" async></script>
            <style>
            body {
                font-family: 'Vazirmatn', 'Segoe UI', sans-serif;
                margin: 0;
                padding: 15px;
                background-color: #222222;
                overflow-y: auto;
                color: #E8EAED;
                font-size: 16px;
                line-height: 1.6;
                word-wrap: break-word;
                direction: rtl;
                opacity: 0;
                transition: opacity 0.3s;
            }

            body::-webkit-scrollbar {
                width: 10px;
            }
            body::-webkit-scrollbar-track {
                background: #2b2b2b;
                border-radius: 5px;
            }
            body::-webkit-scrollbar-thumb {
                background: #555555;
                border-radius: 5px;
            }
            body::-webkit-scrollbar-thumb:hover {
                background: #777777;
            }

            .message {
                margin-bottom: 20px;
                padding: 15px 20px;
                border-radius: 12px;
                max-width: 85%;
                word-wrap: break-word;
                line-height: 1.6;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                position: relative;
                opacity: 0;
                transform: translateY(10px);
                animation: fadeIn 0.4s ease-out forwards;
            }

            .user-message {
                background-color: #008B8B;
                margin-left: auto;
                margin-right: 0;
                color: #ffffff;
                text-align: right;
            }

            .bot-message {
                background-color: #1a1a1a;
                margin-right: auto;
                margin-left: 0;
                color: #E8EAED;
                text-align: right;
                border-left: 4px solid #008B8B;
            }

            .error-message {
                background-color: #c0392b;
                color: #ffffff;
                margin-right: auto;
                margin-left: 0;
                text-align: right;
                border-left: 4px solid #e74c3c;
            }

            .graph-image {
                max-width: 100%;
                height: auto;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            }

            .graph-description {
                margin-top: 10px;
                padding: 10px 15px;
                background-color: #353535;
                border-radius: 8px;
                text-align: right;
                font-style: italic;
                font-size: 0.9em;
                color: #B0B0B0;
            }

            .uploaded-image {
                max-width: 300px;
                max-height: 300px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            }

            .sender-name {
                font-weight: 600;
                margin-bottom: 8px;
                display: block;
                font-size: 0.9em;
                opacity: 0.9;
                color: #cccccc;
            }

            .user-message .sender-name {
                color: #f0f0f0;
            }

            .message-content {
                font-size: 1.0em;
                direction: rtl;
            }

            .message-content .MathJax_Display,
            .message-content .MathJax {
                direction: ltr !important;
                text-align: center !important;
            }

            .message-content p {
                margin: 0 0 12px 0 !important;
                line-height: 1.7 !important;
                text-align: right;
            }

            .message-content p:last-child {
                margin-bottom: 0 !important;
            }

            .message-content strong {
                font-weight: 700 !important;
                color: #ffffff !important;
            }

            .user-message strong {
                color: #f0f0f0 !important;
            }

            .message-content pre {
                background-color: #1a1a1a;
                padding: 10px;
                border-radius: 8px;
                overflow-x: auto;
                margin: 10px 0;
                direction: ltr;
                font-family: 'Fira Code', 'Courier New', monospace;
            }

            .message-content code {
                font-family: 'Fira Code', 'Courier New', monospace;
                font-size: 0.9em;
                color: #c8c8c8;
            }

            .typing-indicator {
                padding: 5px 10px;
                border-radius: 12px;
            }

            .typing-indicator span {
                display: inline-block;
                background-color: #E8EAED;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin: 0 2px;
                opacity: 0.6;
                animation: bounce 1.4s infinite ease-in-out;
            }

            .typing-indicator span:nth-child(2) {
                animation-delay: -1.2s;
            }

            .typing-indicator span:nth-child(3) {
                animation-delay: -1.0s;
            }

            @keyframes bounce {
                0%, 80%, 100% {
                    transform: translateY(0);
                }
                40% {
                    transform: translateY(-8px);
                }
            }

            @keyframes fadeIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            </style>
        </head>
        <body>
            <div id="chat-container"></div>
        </body>
        </html>
        """


# ============================================================================
# Settings Dialog
# ============================================================================

class SettingsDialog(QDialog):
    """Settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # General tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        general_tab.setLayout(general_layout)

        # Font size
        font_size_label = QLabel("اندازه فونت:")
        general_layout.addWidget(font_size_label)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setValue(AppConfig.FONT_SIZE)
        general_layout.addWidget(self.font_size_spin)

        # Auto save
        self.auto_save_check = QCheckBox("ذخیره خودکار گفتگوها")
        self.auto_save_check.setChecked(True)
        general_layout.addWidget(self.auto_save_check)

        general_layout.addStretch()
        tabs.addTab(general_tab, "عمومی")

        # Bridge tab
        bridge_tab = QWidget()
        bridge_layout = QVBoxLayout()
        bridge_tab.setLayout(bridge_layout)

        bridge_url_label = QLabel("آدرس Bridge Server:")
        bridge_layout.addWidget(bridge_url_label)

        self.bridge_url_input = QLineEdit(AppConfig.BRIDGE_URL)
        bridge_layout.addWidget(self.bridge_url_input)

        bridge_layout.addStretch()
        tabs.addTab(bridge_tab, "Bridge")

        # Buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton("ذخیره")
        save_button.clicked.connect(self.accept)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("انصراف")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName(AppConfig.APP_NAME)
        app.setApplicationVersion(AppConfig.APP_VERSION)
        app.setOrganizationName(AppConfig.ORGANIZATION_NAME)
        app.setStyle("Fusion")

        # Create and show window
        window = MathChatBotApp()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
