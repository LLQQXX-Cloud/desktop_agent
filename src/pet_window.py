"""桌宠窗口 —— 支持多 GIF 状态和随机动画"""
import os
import random
from PyQt6.QtWidgets import QWidget, QLabel, QMenu
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QMovie
from PIL import Image as PILImage


class PetWindow(QWidget):
    """透明无边框宠物窗口，每状态支持多个 GIF，随机切换"""

    clicked = pyqtSignal()  # 左键单击

    def __init__(self, animations: dict = None, scale: int = 100,
                 menu_builder=None):
        """
        animations: {"idle": [...], "walk": "path", ...}
        scale: 缩放百分比
        menu_builder: 函数，返回右键菜单 [(label, callback), ...]，每次右键时调用
        """
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.scale = scale / 100.0
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.animations: dict[str, list[QMovie]] = {}
        self._movie_orig_sizes: dict[int, tuple] = {}  # id(movie) -> (w, h)
        self._anim_paths = animations or {}
        self._current_state = "idle"
        self._current_index = {}
        self._canvas_size = None
        self._is_emoji_fallback = False
        self._menu_builder = menu_builder
        self._drag_moved = False  # 初始化，避免右键时 AttributeError

        has_valid_gif = self._load_animations()

        if has_valid_gif:
            self._play("idle")  # 默认 idle_1
            # 随机小动作定时器：每 20~40 秒穿插一次
            self._action_timer = QTimer(self)
            self._action_timer.timeout.connect(self._random_action)
            self._schedule_next_action()
        else:
            self._emoji_fallback()

        self._drag_start = QPoint()
        self.show()

    # ========== 加载 ==========
    def _load_animations(self) -> bool:
        """返回是否有有效 GIF，同时确定统一画布尺寸"""
        has = False
        max_w, max_h = 0, 0
        for state, paths in self._anim_paths.items():
            if isinstance(paths, str):
                paths = [paths]
            movies = []
            for p in paths:
                if os.path.isfile(p):
                    movie = QMovie(p)
                    # 用 Pillow 读取真实尺寸（QMovie 未播放前尺寸不准）
                    try:
                        with PILImage.open(p) as img:
                            ow, oh = img.size
                    except Exception:
                        ow, oh = 0, 0
                    self._movie_orig_sizes[id(movie)] = (ow, oh)
                    max_w = max(max_w, ow)
                    max_h = max(max_h, oh)
                    movies.append(movie)
                    has = True
            if movies:
                self.animations[state] = movies
        # 固定画布 = 最大帧尺寸 × 缩放
        if has:
            self._canvas_size = (
                max(1, int(max_w * self.scale)),
                max(1, int(max_h * self.scale)),
            )
            self.label.setFixedSize(*self._canvas_size)
            self.setFixedSize(*self._canvas_size)
        return has

    # ========== 状态控制 ==========
    def set_state(self, state: str):
        """切换到指定状态，默认播第一个动画"""
        if self._is_emoji_fallback:
            return
        movies = self.animations.get(state)
        if not movies:
            return
        self._current_state = state
        self._current_index[state] = 0
        self._show_movie(movies[0])

    def set_state_random(self, state: str):
        """切换到指定状态，随机选动画（避免重复）"""
        if self._is_emoji_fallback:
            return
        movies = self.animations.get(state)
        if not movies:
            return
        if len(movies) > 1:
            prev = self._current_index.get(state)
            idx = random.choice([i for i in range(len(movies)) if i != prev])
            self._current_index[state] = idx
        else:
            self._current_index[state] = 0
        self._current_state = state
        self._show_movie(movies[self._current_index[state]])

    def state(self) -> str:
        return self._current_state

    def _play(self, state: str):
        """播放指定状态（不避重）"""
        movies = self.animations.get(state)
        if not movies:
            return
        self._current_state = state
        self._current_index[state] = self._current_index.get(state, 0)
        self._show_movie(movies[self._current_index[state]])

    def _show_movie(self, movie: QMovie):
        """播放动画，缩放到固定画布，保持比例居中"""
        if self._canvas_size:
            ow, oh = self._movie_orig_sizes.get(id(movie), (0, 0))
            if ow > 0 and oh > 0:
                cw, ch = self._canvas_size
                ratio = min(cw / ow, ch / oh)
                movie.setScaledSize(QSize(int(ow * ratio), int(oh * ratio)))
            else:
                movie.setScaledSize(QSize(*self._canvas_size))
        self.label.setMovie(movie)
        movie.start()

    # ========== 随机小动作 ==========
    def _schedule_next_action(self):
        """安排下一次随机动作（20~40 秒后）"""
        delay = random.randint(20000, 40000)
        self._action_timer.start(delay)

    def _random_action(self):
        """穿插一个小动作，然后回 idle_1"""
        self._action_timer.stop()
        if self._is_emoji_fallback or self._current_state != "idle":
            self._schedule_next_action()
            return

        roll = random.random()
        idle_count = len(self.animations.get("idle", []))

        if roll < 0.35 and idle_count > 1:
            # 35%: 切到其他待机动画（idle_2 / idle_3 ...）
            self.set_state_random("idle")
            QTimer.singleShot(3000, lambda: self.set_state("idle"))

        elif roll < 0.55 and "walk" in self.animations:
            # 20%: 走两步
            self.set_state("walk")
            dx = random.randint(-80, 80)
            dy = random.randint(-40, 40)
            self.move(self.x() + dx, self.y() + dy)
            QTimer.singleShot(1500, lambda: self.set_state("idle"))

        elif roll < 0.65 and "talk" in self.animations:
            # 10%: 自言自语一下
            self.set_state("talk")
            QTimer.singleShot(2000, lambda: self.set_state("idle"))

        elif roll < 0.70 and "happy" in self.animations:
            # 5%: 开心一下
            self.set_state("happy")
            QTimer.singleShot(2000, lambda: self.set_state("idle"))

        # else (30%): 什么都不做，继续 idle_1

        self._schedule_next_action()

    # ========== 降级方案 ==========
    def _emoji_fallback(self):
        self._is_emoji_fallback = True
        size = int(80 * self.scale)
        self.label.setText("🐱")
        self.label.setStyleSheet(f"font-size: {size}px; background: transparent; padding: 10px;")
        self.label.adjustSize()
        wh = int(100 * self.scale)
        self.resize(wh, wh)
        screen = self.screen().availableGeometry()
        self.move(screen.right() - wh - 50, screen.bottom() - wh - 50)

    # ========== 拖拽 & 点击 ==========
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_moved = False
            self.set_state("drag")

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_start') and self._drag_start is not None:
            delta = event.globalPosition().toPoint() - self.frameGeometry().topLeft() - self._drag_start
            if abs(delta.x()) > 3 or abs(delta.y()) > 3:
                self._drag_moved = True
            self.move(event.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._drag_moved:
                self.clicked.emit()
            if not self._is_emoji_fallback:
                self.set_state("idle")
        self._drag_start = None

    def contextMenuEvent(self, event):
        """右键菜单（每次动态生成）"""
        if not self._menu_builder:
            return
        items = self._menu_builder()
        if not items:
            return
        menu = QMenu(self)
        for label, callback in items:
            if label == "---":
                menu.addSeparator()
            else:
                menu.addAction(label, callback)
        menu.exec(event.globalPos())

    # ========== 外部触发的行为 ==========
    def say(self, text: str):
        if not self._is_emoji_fallback:
            self.set_state("talk")

    def happy(self):
        if not self._is_emoji_fallback:
            self.set_state("happy")
            QTimer.singleShot(2000, lambda: self.set_state("idle"))
