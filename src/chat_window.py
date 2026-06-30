"""对话悬浮窗口 —— 侧边栏多对话 + 文件上传 + 聊天气泡"""
import html as _html
import os
import uuid
import shutil
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QLabel, QGraphicsDropShadowEffect,
    QListWidget, QListWidgetItem, QFileDialog, QMenu, QInputDialog,
    QMessageBox, QSplitter, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QColor, QImage, QPixmap, QPainter, QBrush, QPen


IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}


# ============================================================
#  样式表
# ============================================================

STYLESHEET = """
QWidget#chatWindow {
    background-color: transparent;
}

QFrame#mainContainer {
    background-color: #FFFFFF;
    border-radius: 14px;
    border: 1px solid #D1D1D6;
}

/* ---- 标题栏 ---- */
QFrame#titleBar {
    background-color: #FAFAFA;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    border-bottom: 1px solid #E5E5EA;
}

QLabel#titleLabel {
    color: #1A1A1A;
    font-size: 13px;
    font-weight: 600;
    padding-left: 10px;
}

QPushButton#minimizeBtn {
    background-color: transparent;
    color: #8E8E93;
    border: none;
    font-size: 15px;
    font-weight: bold;
    border-radius: 4px;
}
QPushButton#minimizeBtn:hover {
    background-color: #E5E5EA;
    color: #1A1A1A;
}

QPushButton#closeBtn {
    background-color: transparent;
    color: #8E8E93;
    border: none;
    font-size: 14px;
    font-weight: bold;
    border-radius: 4px;
}
QPushButton#closeBtn:hover {
    background-color: #E81123;
    color: #FFFFFF;
}

/* ---- 侧边栏 ---- */
QFrame#sidebar {
    background-color: #F5F5F7;
    border-right: 1px solid #E5E5EA;
    border-bottom-left-radius: 14px;
}

QPushButton#newConvBtn {
    background-color: #34C759;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    margin: 10px 10px 6px 10px;
}
QPushButton#newConvBtn:hover {
    background-color: #2DB84D;
}

QListWidget#convList {
    background-color: transparent;
    border: none;
    color: #1A1A1A;
    font-size: 13px;
    outline: none;
    padding: 4px 8px;
}
QListWidget#convList::item {
    padding: 9px 12px;
    border-radius: 8px;
    margin: 2px 0px;
}
QListWidget#convList::item:selected {
    background-color: #007AFF;
    color: #FFFFFF;
}
QListWidget#convList::item:hover {
    background-color: #E8E8ED;
}
QListWidget#convList::item:selected:hover {
    background-color: #0066D6;
}
QListWidget#convList::item:selected:!active {
    background-color: #007AFF;
    color: #FFFFFF;
}

/* ---- 对话区域 ---- */
QScrollArea#chatBox {
    background-color: #FFFFFF;
    border: none;
}

QWidget#chatContainer {
    background-color: #FFFFFF;
}

QLabel#userBubble {
    background-color: #007AFF;
    color: #FFFFFF;
    border-radius: 20px;
    padding: 10px 16px;
    font-size: 13px;
}

QLabel#botBubble {
    background-color: #F0F0F3;
    color: #1A1A1A;
    border-radius: 20px;
    padding: 10px 16px;
    font-size: 13px;
}

QLabel#fileCard {
    background-color: #F5F5F7;
    color: #1A1A1A;
    border: 1px solid #E5E5EA;
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 13px;
}

/* ---- 附件预览栏 ---- */
QFrame#attachPreview {
    background-color: #F9F9FB;
    border-top: 1px solid #E5E5EA;
    border-bottom: 1px solid #E5E5EA;
}

QLabel#previewChip {
    background-color: #FFFFFF;
    color: #1A1A1A;
    border: 1px solid #D1D1D6;
    border-radius: 8px;
    padding: 4px 6px 4px 10px;
    font-size: 12px;
}

QPushButton#chipRemoveBtn {
    background-color: transparent;
    color: #8E8E93;
    border: none;
    font-size: 14px;
    padding: 0px 4px;
    border-radius: 4px;
}
QPushButton#chipRemoveBtn:hover {
    color: #E81123;
    background-color: #F0F0F3;
}

/* ---- 输入容器 ---- */
QFrame#inputContainer {
    background-color: #F5F5F7;
    border-radius: 20px;
    border: 1px solid #E5E5EA;
    margin: 8px 12px 12px 12px;
}

QLineEdit#inputEdit {
    background-color: transparent;
    border: none;
    color: #1A1A1A;
    font-size: 14px;
    padding: 9px 4px 9px 8px;
    selection-background-color: #007AFF;
    selection-color: #FFFFFF;
}

QPushButton#attachBtn {
    background-color: transparent;
    color: #8E8E93;
    border: none;
    font-size: 18px;
    padding: 4px 2px 4px 10px;
    border-radius: 8px;
}
QPushButton#attachBtn:hover {
    color: #007AFF;
    background-color: #E8E8ED;
}

QPushButton#sendBtn {
    background-color: #007AFF;
    color: #FFFFFF;
    border: none;
    border-radius: 18px;
    padding: 7px 20px;
    font-size: 13px;
    font-weight: 600;
    margin: 4px 6px 4px 0px;
    min-width: 56px;
}
QPushButton#sendBtn:hover {
    background-color: #0066D6;
}
QPushButton#sendBtn:pressed {
    background-color: #0055B0;
}

/* ---- 滚动条 ---- */
QScrollBar:vertical {
    background-color: transparent;
    width: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #D1D1D6;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background-color: #B0B0B8;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background-color: transparent;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 6px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: #D1D1D6;
    border-radius: 3px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #B0B0B8;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background-color: transparent;
}

QSplitter::handle {
    background-color: #E5E5EA;
    width: 1px;
}
"""


# ============================================================
#  _BubbleFrame — 手绘圆角气泡（不用 QSS border-radius，100% 可靠）
# ============================================================

class _BubbleFrame(QFrame):
    """自定义 QFrame，paintEvent 手绘圆角背景"""

    def __init__(self, bg_color: str, radius: int = 20, parent=None):
        super().__init__(parent)
        self._bg = QColor(bg_color)
        self._radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(self._bg))
        painter.drawRoundedRect(self.rect(), self._radius, self._radius)


# ============================================================
#  _ChatBox — 自动气泡 + 图片/文件渲染
# ============================================================

class _ChatBox(QScrollArea):
    """聊天气泡容器 — QScrollArea + _BubbleFrame(手绘圆角) 包 QLabel(文字)"""

    BUBBLE_MAX_RATIO = 0.78

    _USER_TEXT = "background:transparent; color:#FFFFFF; font-size:13px;"
    _BOT_TEXT  = "background:transparent; color:#1A1A1A; font-size:13px;"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("chatBox")

        self._container = QWidget()
        self._container.setObjectName("chatContainer")
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setContentsMargins(4, 8, 4, 8)
        self._layout.setSpacing(6)
        self._layout.addStretch()
        self.setWidget(self._container)

        self._stream_frame: QFrame | None = None

    # ---- 公开方法 ----

    def append_message(self, role: str, text: str):
        self._add_row(self._make_bubble(text, role == "user"), role == "user")

    def append_image(self, role: str, path: str):
        img = QImage(path)
        if img.isNull():
            self.append_message(role, f"[图片加载失败] {os.path.basename(path)}")
            return
        if img.width() > 260:
            img = img.scaledToWidth(260, Qt.TransformationMode.SmoothTransformation)
        label = QLabel()
        label.setPixmap(QPixmap.fromImage(img))
        label.setMaximumWidth(260)
        label.setStyleSheet("border-radius:12px;")
        self._add_row(label, role == "user")

    def append_file_card(self, role: str, filename: str, size_str: str):
        text = (f'📄 <b>{_html.escape(filename)}</b><br>'
                f'<span style="font-size:11px; color:#8E8E93;">'
                f'文件已保存 · {size_str}</span>')
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        label.setMaximumWidth(int(self.width() * self.BUBBLE_MAX_RATIO))
        label.setStyleSheet(
            "background-color:#F5F5F7; color:#1A1A1A; "
            "border:1px solid #E5E5EA; border-radius:12px; padding:10px 14px; font-size:13px;"
        )
        self._add_row(label, role == "user")

    def append(self, text: str):
        if text.startswith("你："):
            self.append_message("user", text[2:])
        elif text.startswith("助手："):
            self.append_message("assistant", text[3:])
        else:
            self._add_row(self._make_bubble(text, False), False)

    def clear(self):
        self._stream_frame = None
        self._clear_messages()

    # ---- 流式输出 ----

    def start_streaming(self):
        frame = self._make_bubble("▊", False)
        row = QHBoxLayout()
        row.setContentsMargins(8, 0, 8, 0)
        row.addWidget(frame)
        row.addStretch()
        self._layout.insertLayout(self._layout.count() - 1, row)
        self._stream_frame = frame
        self._scroll_to_bottom()

    def update_streaming(self, text: str, rich_text: bool = False):
        if not self._stream_frame:
            return
        inner = self._stream_frame.findChild(QLabel)
        if inner:
            inner.setTextFormat(Qt.TextFormat.RichText if rich_text else Qt.TextFormat.PlainText)
            inner.setText(text + "▊")
        self._scroll_to_bottom()

    def finish_streaming(self):
        if not self._stream_frame:
            return
        inner = self._stream_frame.findChild(QLabel)
        if inner:
            t = inner.text()
            inner.setTextFormat(Qt.TextFormat.PlainText)
            inner.setText(t[:-1] if t.endswith("▊") else t)
        self._stream_frame = None

    # ---- 内部 ----

    def _make_bubble(self, text: str, is_user: bool) -> _BubbleFrame:
        """_BubbleFrame（手绘圆角背景）包 QLabel（文字）"""
        frame = _BubbleFrame("#007AFF" if is_user else "#F0F0F3", radius=20)

        inner = QLabel(text)
        inner.setWordWrap(True)
        inner.setTextFormat(Qt.TextFormat.PlainText)
        inner.setMaximumWidth(int(self.width() * self.BUBBLE_MAX_RATIO) - 32)
        inner.setStyleSheet(self._USER_TEXT if is_user else self._BOT_TEXT)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.addWidget(inner)
        return frame

    def _add_row(self, widget: QWidget, is_user: bool):
        row = QHBoxLayout()
        row.setContentsMargins(8, 0, 8, 0)
        if is_user:
            row.addStretch()
            row.addWidget(widget)
        else:
            row.addWidget(widget)
            row.addStretch()
        self._layout.insertLayout(self._layout.count() - 1, row)
        self._scroll_to_bottom()

    def _clear_messages(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.layout():
                self._delayout(item.layout())
            elif item.widget():
                item.widget().deleteLater()

    def _delayout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._delayout(child.layout())

    def _scroll_to_bottom(self):
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_max = int(self.width() * self.BUBBLE_MAX_RATIO) - 32
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item and item.layout():
                row = item.layout()
                for j in range(row.count()):
                    w = row.itemAt(j)
                    if w and w.widget():
                        widget = w.widget()
                        # 更新 QFrame 内的 QLabel 最大宽度
                        inner = widget.findChild(QLabel)
                        if inner:
                            inner.setMaximumWidth(new_max)
                        # 如果是纯 QLabel（图片），更新 widget 自身
                        elif isinstance(widget, QLabel):
                            widget.setMaximumWidth(int(self.width() * self.BUBBLE_MAX_RATIO))


# ============================================================
#  _TitleBar — 可拖拽自定义标题栏
# ============================================================

class _TitleBar(QFrame):
    """无边框窗口的拖拽标题栏"""

    def __init__(self, parent_window: QWidget):
        super().__init__()
        self._win = parent_window
        self._drag_pos = None
        self.setObjectName("titleBar")
        self.setFixedHeight(36)
        self._build()

    def _build(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("  桌面助手")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        layout.addStretch()

        min_btn = QPushButton("─")
        min_btn.setObjectName("minimizeBtn")
        min_btn.setFixedSize(36, 28)
        min_btn.clicked.connect(lambda: self._win.showMinimized())
        layout.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(36, 28)
        close_btn.clicked.connect(lambda: self._win.hide())
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self._win.move(self._win.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


# ============================================================
#  ChatWindow
# ============================================================

class ChatWindow(QWidget):
    """现代聊天气泡悬浮窗口 + 侧边栏多对话 + 文件上传"""

    conversation_changed = pyqtSignal(str)
    message_ready = pyqtSignal(str, list)  # text, attachments

    def __init__(self, memory=None, upload_dir="_data/uploads"):
        super().__init__()
        self._memory = memory
        self._upload_dir = upload_dir
        self._current_conv_id = None
        self._pending_new_conv = False   # 点 + 新对话后等待用户发第一条消息
        self._pending_attachments: list[dict] = []  # 待发附件
        os.makedirs(upload_dir, exist_ok=True)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("chatWindow")
        self.setWindowTitle("桌面助手")
        self.resize(620, 500)
        self.setMinimumSize(460, 350)
        self.setStyleSheet(STYLESHEET)

        # ---- 主容器 ----
        self._main_container = QFrame()
        self._main_container.setObjectName("mainContainer")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 30))
        self._main_container.setGraphicsEffect(shadow)

        self._title_bar = _TitleBar(self)

        # ========== 侧边栏 ==========
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(140)
        sidebar.setMaximumWidth(300)

        self._new_conv_btn = QPushButton("+ 新对话")
        self._new_conv_btn.setObjectName("newConvBtn")
        self._new_conv_btn.clicked.connect(self._on_new_conversation)

        self._conv_list = QListWidget()
        self._conv_list.setObjectName("convList")
        self._conv_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._conv_list.customContextMenuRequested.connect(self._on_conv_context_menu)
        self._conv_list.itemClicked.connect(self._on_conv_clicked)
        self._conv_list.itemDoubleClicked.connect(self._on_conv_double_clicked)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_layout.addWidget(self._new_conv_btn)
        sidebar_layout.addWidget(self._conv_list)
        sidebar.setLayout(sidebar_layout)

        # ========== 右侧 ==========
        right_side = QFrame()

        # 聊天区
        self.chat_box = _ChatBox()
        self.chat_box.setObjectName("chatBox")

        # ---- 附件预览栏（初始隐藏）----
        self._attach_preview = QFrame()
        self._attach_preview.setObjectName("attachPreview")
        self._attach_preview.setFixedHeight(42)
        self._attach_preview.setVisible(False)
        self._attach_preview_layout = QHBoxLayout()
        self._attach_preview_layout.setContentsMargins(8, 4, 8, 4)
        self._attach_preview_layout.setSpacing(6)
        self._attach_preview_layout.addStretch()
        self._attach_preview.setLayout(self._attach_preview_layout)

        # ---- 输入区 ----
        self._input_container = QFrame()
        self._input_container.setObjectName("inputContainer")

        self._attach_btn = QPushButton("📎")
        self._attach_btn.setObjectName("attachBtn")
        self._attach_btn.setFixedSize(32, 32)
        self._attach_btn.setToolTip("添加文件或图片")
        self._attach_btn.clicked.connect(self._on_attach)

        self.input_edit = QLineEdit()
        self.input_edit.setObjectName("inputEdit")
        self.input_edit.setPlaceholderText("输入消息，按回车发送...")
        self.input_edit.returnPressed.connect(self.send_msg)

        self.send_btn = QPushButton("发送")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.clicked.connect(self.send_msg)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(0)
        input_layout.addWidget(self._attach_btn)
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.send_btn)
        self._input_container.setLayout(input_layout)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.chat_box, stretch=1)
        right_layout.addWidget(self._attach_preview)
        right_layout.addWidget(self._input_container)
        right_side.setLayout(right_layout)

        # ---- 左右分栏 ----
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(sidebar)
        splitter.addWidget(right_side)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([175, 445])

        # ---- 组装 ----
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(self._main_container)

        inner_layout = QVBoxLayout()
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)
        inner_layout.addWidget(self._title_bar)
        inner_layout.addWidget(splitter, stretch=1)
        self._main_container.setLayout(inner_layout)

    # ========== 公开属性 ==========

    @property
    def current_conversation_id(self) -> str | None:
        return self._current_conv_id

    @property
    def pending_attachments(self) -> list[dict]:
        """返回待发附件列表，供 main.py 在发送时读取"""
        return list(self._pending_attachments)

    # ========== 公开方法 ==========

    def send_msg(self):
        text = self.input_edit.text().strip()
        attachments = list(self._pending_attachments)

        if not text and not attachments:
            return

        # 确保有有效对话：不存在的就当场创建
        conv = None
        if self._current_conv_id and self._memory:
            conv = self._memory.get_conversation(self._current_conv_id)
        if not conv and self._memory:
            self._pending_new_conv = False
            cid = self._memory.create_conversation()
            self._current_conv_id = cid
            self._refresh_list()

        # 插入用户消息
        if text:
            self.chat_box.append(f"你：{text}")

        # 插入附件
        for att in attachments:
            if att["type"] == "image":
                self.chat_box.append_image("user", att["path"])
            else:
                self.chat_box.append_file_card("user", att["filename"], att["size_str"])

        # 清空待发
        self._clear_attachments()
        self.input_edit.clear()

        # 通知 main.py（带上文字和附件路径列表）
        self.message_ready.emit(text, attachments)

    def append_bot_msg(self, text):
        self.chat_box.append(f"助手：{text}")

    # ---- 流式输出（后台线程 → UI 逐字刷新）----
    def start_bot_stream(self):
        """开始流式回复：插入空气泡 + 启动刷新定时器"""
        self.chat_box.start_streaming()
        if not hasattr(self, '_stream_timer'):
            self._stream_timer = QTimer(self)
            self._stream_timer.timeout.connect(self._flush_stream)
        self._stream_buffer = ""
        self._thinking_status = ""
        self._stream_timer.start(50)  # 每 50ms 刷新一次

    def add_stream_token(self, token: str):
        """后台线程追加 token"""
        self._stream_buffer += token

    def _flush_stream(self):
        """定时器回调：刷新气泡内容（文本 + 状态栏）"""
        buffer = self._stream_buffer
        status = getattr(self, '_thinking_status', '')
        if status:
            # 状态栏用 HTML 渲染（灰色斜体），token 文本转义后拼接
            display = f'<span style="color:#8E8E93; font-style:italic;">{status}</span><br>'
            if buffer:
                display += _html.escape(buffer)
            self.chat_box.update_streaming(display, rich_text=True)
        elif buffer:
            self.chat_box.update_streaming(_html.escape(buffer), rich_text=False)

    def finish_bot_stream(self):
        """结束流式回复：定稿气泡"""
        if hasattr(self, '_stream_timer') and self._stream_timer.isActive():
            self._stream_timer.stop()
        self._thinking_status = ""
        # 最后刷一次：不带状态栏的纯净文本写入 _ChatBox._stream_buffer
        # 否则 finish_streaming 会拿到混着 <i> 标签的文本，被 html.escape 转义
        self._flush_stream()
        self.chat_box.finish_streaming()
        self._stream_buffer = ""

    def set_thinking_status(self, text: str):
        """更新状态栏文本（如「正在搜索...」）"""
        self._thinking_status = text
        self._flush_stream()

    def set_conversations(self, convs: list[dict], select_id: str = None):
        self._conv_list.clear()
        selected_item = None
        for c in convs:
            item = QListWidgetItem(c["title"])
            item.setData(Qt.ItemDataRole.UserRole, c["id"])
            item.setSizeHint(QSize(0, 36))
            if c["id"] == select_id:
                selected_item = item
                self._current_conv_id = c["id"]
            self._conv_list.addItem(item)
        if selected_item:
            self._conv_list.setCurrentItem(selected_item)
        elif self._conv_list.count() > 0:
            self._conv_list.item(0).setSelected(True)
            self._current_conv_id = self._conv_list.item(0).data(Qt.ItemDataRole.UserRole)

    def load_conversation(self, conv_id: str, history: list[dict]):
        self._current_conv_id = conv_id
        self.chat_box.clear()
        for h in history:
            name = "你" if h["role"] == "user" else "助手"
            self.chat_box.append(f"{name}：{h['content']}")

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    # ========== 附件预览栏 ==========

    def _on_attach(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "所有支持的文件 (*.png *.jpg *.jpeg *.gif *.webp *.bmp *.pdf *.txt *.doc *.docx *.xls *.xlsx *.zip);;"
            "图片 (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;"
            "所有文件 (*)"
        )
        if not file_paths:
            return

        for src in file_paths:
            if not os.path.isfile(src):
                continue

            size = os.path.getsize(src)
            if size > 10 * 1024 * 1024:
                QMessageBox.warning(self, "文件过大",
                                    f"{os.path.basename(src)} 超过 10MB 限制")
                continue

            ext = os.path.splitext(src)[1].lower()
            dst_name = f"{uuid.uuid4().hex[:8]}{ext}"
            dst = os.path.join(self._upload_dir, dst_name)
            shutil.copy2(src, dst)

            filename = os.path.basename(src)
            size_str = self._format_size(size)

            if ext in IMAGE_EXTENSIONS:
                self._add_attachment_chip("image", dst, filename, size_str)
            else:
                self._add_attachment_chip("file", dst, filename, size_str)

    def _add_attachment_chip(self, att_type: str, path: str, filename: str, size_str: str):
        """在预览栏添加一个附件 chip"""
        idx = len(self._pending_attachments)
        self._pending_attachments.append({
            "type": att_type, "path": path, "filename": filename, "size_str": size_str,
        })

        # 图标
        icon = "🖼️" if att_type == "image" else "📄"
        display_name = filename if len(filename) <= 12 else filename[:10] + "..."

        chip = QFrame()
        chip.setObjectName("previewChip")
        chip_layout = QHBoxLayout()
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.setSpacing(4)

        label = QLabel(f"{icon} {display_name}")
        label.setObjectName("previewChipLabel")

        remove_btn = QPushButton("✕")
        remove_btn.setObjectName("chipRemoveBtn")
        remove_btn.setFixedSize(20, 20)
        remove_btn.clicked.connect(lambda: self._remove_attachment(idx))

        chip_layout.addWidget(label)
        chip_layout.addWidget(remove_btn)
        chip.setLayout(chip_layout)

        # 插入到 stretch 之前
        count = self._attach_preview_layout.count()
        self._attach_preview_layout.insertWidget(count - 1, chip)
        self._attach_preview.setVisible(True)

    def _remove_attachment(self, idx: int):
        """移除指定附件"""
        if 0 <= idx < len(self._pending_attachments):
            # takeAt 同时移除布局项并返回，避免 deadlock
            item = self._attach_preview_layout.takeAt(idx)
            if item and item.widget():
                item.widget().deleteLater()
            self._pending_attachments.pop(idx)

        if not self._pending_attachments:
            self._attach_preview.setVisible(False)

    def _clear_attachments(self):
        """清空所有待发附件"""
        # takeAt 会从布局中移除，count() 递减，循环正常结束
        while self._attach_preview_layout.count() > 1:
            item = self._attach_preview_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._pending_attachments.clear()
        self._attach_preview.setVisible(False)

    # ========== 侧边栏交互 ==========

    def _on_new_conversation(self):
        # 不创建对话，只清空右边 + 显示问候语。用户发消息后才真正创建。
        self._pending_new_conv = True
        self._current_conv_id = None
        self._conv_list.clearSelection()
        self.chat_box.clear()
        self.show_greeting()

    def show_greeting(self):
        """新对话问候语（不存历史）"""
        self.chat_box.append_message("assistant", "我能帮你什么？(╹▽╹)")

    def _on_conv_clicked(self, item: QListWidgetItem):
        cid = item.data(Qt.ItemDataRole.UserRole)
        self._pending_new_conv = False
        if cid and cid != self._current_conv_id:
            self._current_conv_id = cid
            self.conversation_changed.emit(cid)

    def _on_conv_double_clicked(self, item: QListWidgetItem):
        cid = item.data(Qt.ItemDataRole.UserRole)
        if not cid or not self._memory:
            return
        conv = self._memory.get_conversation(cid)
        if not conv:
            return
        new_title, ok = QInputDialog.getText(
            self, "重命名对话", "新标题：", text=conv["title"]
        )
        if ok and new_title.strip():
            self._memory.rename_conversation(cid, new_title.strip())
            self._refresh_list()

    def _on_conv_context_menu(self, pos):
        item = self._conv_list.itemAt(pos)
        if not item:
            return
        cid = item.data(Qt.ItemDataRole.UserRole)
        if not cid:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")
        action = menu.exec(self._conv_list.mapToGlobal(pos))
        if action == rename_action:
            self._on_conv_double_clicked(item)
        elif action == delete_action:
            if self._memory:
                self._memory.delete_conversation(cid)
                # 删掉后统一回到新对话界面
                self._pending_new_conv = True
                self._current_conv_id = None
                self._refresh_list()
                self.chat_box.clear()
                self.show_greeting()

    def _refresh_list(self):
        if self._memory:
            convs = self._memory.list_conversations()
            self.set_conversations(convs, select_id=self._current_conv_id)

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
