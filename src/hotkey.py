"""全局快捷键监听"""
from PyQt6.QtCore import QThread, pyqtSignal
from pynput import keyboard

# 默认快捷键：Alt + A
WAKE_HOTKEY = {keyboard.Key.alt, keyboard.KeyCode(char='a')}
pressed_keys = set()


class HotkeyThread(QThread):
    """监听全局热键，触发时发送信号"""
    show_win_signal = pyqtSignal()

    def run(self):
        def on_key_press(key):
            pressed_keys.add(key)
            if all(k in pressed_keys for k in WAKE_HOTKEY):
                self.show_win_signal.emit()

        def on_key_release(key):
            if key in pressed_keys:
                pressed_keys.remove(key)

        listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
        listener.run()
