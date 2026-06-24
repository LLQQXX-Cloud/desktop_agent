"""系统托盘管理"""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush, QPen
from PyQt6.QtCore import Qt


def toggle_window(window):
    """切换窗口显示 / 隐藏"""
    if window.isHidden():
        window.show()
        window.raise_()
        window.activateWindow()
    else:
        window.hide()


def _make_tray_icon() -> QIcon:
    """绘制托盘图标：白色圆角底 + 蓝色笑脸（模拟宠物）"""
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 白色圆角方形背景
    painter.setBrush(QBrush(QColor(255, 255, 255)))
    painter.setPen(QPen(QColor(200, 200, 210), 1))
    painter.drawRoundedRect(6, 6, 52, 52, 14, 14)

    # 蓝色眼睛
    painter.setBrush(QBrush(QColor(0, 122, 255)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(19, 26, 8, 8)
    painter.drawEllipse(37, 26, 8, 8)

    # 微笑弧线
    painter.setPen(QPen(QColor(0, 122, 255), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(23, 30, 18, 14, 0, -180 * 16)

    painter.end()
    return QIcon(pix)


class TrayManager:
    """管理托盘图标和菜单"""

    def __init__(self, app, chat_window, pet_window=None):
        self.app = app
        self.chat_window = chat_window
        self.pet_window = pet_window

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(_make_tray_icon())
        self.tray.setToolTip("桌面助手")

        self._build_menu()

        self.tray.activated.connect(self._on_activated)
        self.tray.show()

    def _build_menu(self):
        menu = QMenu()

        # --- 聊天窗口 ---
        self.chat_toggle_action = menu.addAction("隐藏聊天")
        self.chat_toggle_action.triggered.connect(
            lambda: toggle_window(self.chat_window)
        )

        # --- 桌宠显隐 ---
        if self.pet_window:
            self.pet_toggle_action = menu.addAction("隐藏桌宠")
            self.pet_toggle_action.triggered.connect(self._toggle_pet)

        menu.addSeparator()
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self.app.quit)

        # 菜单弹出前动态更新文字
        def on_about_to_show():
            if self.chat_window.isHidden():
                self.chat_toggle_action.setText("显示聊天")
            else:
                self.chat_toggle_action.setText("隐藏聊天")

            if self.pet_window:
                if self.pet_window.isHidden():
                    self.pet_toggle_action.setText("显示桌宠")
                else:
                    self.pet_toggle_action.setText("隐藏桌宠")

        menu.aboutToShow.connect(on_about_to_show)
        self.tray.setContextMenu(menu)

    def _toggle_pet(self):
        if self.pet_window:
            toggle_window(self.pet_window)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            toggle_window(self.chat_window)
