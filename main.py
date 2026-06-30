"""桌面助手 —— 入口文件，组装所有模块"""
import os
import sys
import asyncio
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from src.chat_window import ChatWindow
from src.hotkey import HotkeyThread
from src.tray_manager import TrayManager, toggle_window
from src.pet_window import PetWindow
from src.ai_client import AIClient
from src.memory import Memory
from src.knowledge_base import KnowledgeBase
from src.commands import handle_command
from src.agent import AgentManager
from src import doc_parser


# ================================================================
#  辅助函数
# ================================================================

def _parse_attachments(attachments: list[dict]) -> tuple[str, dict[str, str]]:
    """解析附件列表 → (拼接文本, {filename: content})。同时将文本内容入库。"""
    parts: list[str] = []
    att_map: dict[str, str] = {}
    for att in attachments:
        content, error = doc_parser.parse_file(att["path"])
        if content:
            parts.append(f"[📄 {att['filename']}]\n{content}")
            att_map[att["filename"]] = content
        elif error:
            parts.append(f"[📄 {att['filename']}]\n⚠️ {error}")
            att_map[att["filename"]] = f"⚠️ {error}"
    joined = "\n\n---\n\n".join(parts) if parts else ""
    return joined, att_map


def _build_message(text: str, att_text: str) -> str:
    """组装发给 AI 的完整消息"""
    if not att_text:
        return text
    if text:
        return f"{att_text}\n\n---\n\n💬 用户消息:\n{text}"
    return f"{att_text}\n\n（用户上传了以上文件）"


# ================================================================
#  main
# ================================================================

def main():
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)

    memory = Memory()
    kb = KnowledgeBase()
    ai = AIClient(memory, kb=kb)

    # ---- 桌宠 ----
    _pet_ref = [None]

    def build_pet_menu():
        pet = _pet_ref[0]
        return [
            ("隐藏聊天" if not chat.isHidden() else "显示聊天",
             lambda: toggle_window(chat)),
            ("隐藏桌宠" if not pet.isHidden() else "显示桌宠",
             lambda: pet.hide()),
            ("---", None),
            ("退出", qapp.quit),
        ]

    pet = PetWindow(scale=20, animations={
        "idle": ["assets/pet/idle_1.gif", "assets/pet/idle_2.gif",
                 "assets/pet/idle_3.gif"],
        "walk": "assets/pet/walk.gif",
        "talk": "assets/pet/talk.gif",
    }, menu_builder=build_pet_menu)
    _pet_ref[0] = pet

    # ---- 聊天窗 ----
    chat = ChatWindow(memory=memory)
    convs = memory.list_conversations()
    if convs:
        default_id = convs[0]["id"]
        chat.set_conversations(convs, select_id=default_id)
        ai.set_conversation(default_id)
        history = memory.get_history(default_id, limit=30)
        chat.load_conversation(default_id, history)
        if not history:
            chat.show_greeting()
    else:
        # 没有对话 → 直接新对话状态
        chat.set_conversations([])
        chat._pending_new_conv = True
        chat.show_greeting()

    def on_conversation_changed(cid: str):
        ai.set_conversation(cid)
        history = memory.get_history(cid, limit=30)
        chat.load_conversation(cid, history)
        if not history:
            chat.show_greeting()
    chat.conversation_changed.connect(on_conversation_changed)

    # ---- 发送消息 ----
    _sending = False

    def on_send():
        nonlocal _sending
        if _sending:
            return
        text = chat.input_edit.text().strip()
        attachments = list(chat.pending_attachments)
        if not text and not attachments:
            return

        _sending = True
        pet.set_state("talk")
        chat.send_msg()   # 这里会创建对话（如果是 pending 状态），必须在读 conv_id 之前
        conv_id = chat.current_conversation_id

        att_text, att_map = _parse_attachments(attachments)
        full_text = _build_message(text, att_text)

        # 文件内容自动入库（跨对话可检索）
        for filename, content in att_map.items():
            if content and not content.startswith("⚠️"):
                ext = os.path.splitext(filename)[1].lower()
                kb.add_text(content, source=f"[上传] {filename}", extension=ext)

        if text.startswith("/"):
            reply = handle_command(text, memory, kb)
            memory.add_message("assistant", reply, conv_id)
            chat.append_bot_msg(reply)
            pet.happy()
            _sending = False
            return

        # Agent 模式：Python 线程 + asyncio 流式输出
        memory.add_message("user", full_text, conv_id)
        chat.start_bot_stream()

        if ai._agent_manager is None:
            ai._agent_manager = AgentManager(memory=ai.memory, kb=ai.kb, tray=ai.tray)
        if att_map:
            ai._agent_manager.set_attachments(att_map)

        class _Bridge(QObject):
            token = pyqtSignal(str)
            tool_start = pyqtSignal(str)
            tool_end = pyqtSignal(str)
            done = pyqtSignal(str)
            fail = pyqtSignal(str)

        bridge = _Bridge()

        def _on_finished(reply: str):
            chat.finish_bot_stream()
            memory.add_message("assistant", reply, conv_id)
            conv = memory.get_conversation(conv_id)
            if conv and conv["title"] == "新对话":
                title = ai.generate_title(full_text[:80] or "文件对话")
                memory.rename_conversation(conv_id, title)
            # 每次回复完刷新侧边栏（updated_at 已更新，排序生效）
            chat.set_conversations(memory.list_conversations(), select_id=conv_id)
            pet.set_state("idle")
            nonlocal _sending
            _sending = False

        def _on_error(err: str):
            chat.finish_bot_stream()
            chat.append_bot_msg(err)
            memory.add_message("assistant", err, conv_id)
            pet.set_state("idle")
            nonlocal _sending
            _sending = False

        bridge.token.connect(lambda t: chat.add_stream_token(t))
        bridge.tool_start.connect(
            lambda name: chat.set_thinking_status(f"🔧 正在调用 {name}..."))
        bridge.tool_end.connect(
            lambda name: chat.set_thinking_status("正在整理回答..."))
        bridge.done.connect(_on_finished)
        bridge.fail.connect(_on_error)

        def _run():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_stream())
            except Exception as e:
                bridge.fail.emit(str(e))

        async def _stream():
            async for ev, data in ai._agent_manager.run_stream(full_text, conv_id):
                if ev == "token":
                    bridge.token.emit(data)
                elif ev == "tool_start":
                    bridge.tool_start.emit(data)
                elif ev == "tool_end":
                    bridge.tool_end.emit(data)
                elif ev == "done":
                    bridge.done.emit(data)
                elif ev == "error":
                    bridge.fail.emit(data)

        threading.Thread(target=_run, daemon=True).start()

    # 错误日志：发消息时的崩溃记录到文件
    import traceback as _tb

    def _safe_on_send():
        try:
            on_send()
        except Exception:
            with open("_crash.log", "w", encoding="utf-8") as f:
                _tb.print_exc(file=f)
            raise

    for sig in (chat.send_btn.clicked, chat.input_edit.returnPressed):
        try:
            sig.disconnect()
        except Exception:
            pass
        sig.connect(_safe_on_send)

    # ---- 托盘 & 热键 ----
    tray = TrayManager(qapp, chat, pet_window=pet)
    ai.tray = tray.tray
    pet.clicked.connect(lambda: toggle_window(chat))

    hotkey_thread = HotkeyThread()
    hotkey_thread.show_win_signal.connect(lambda: toggle_window(chat))
    try:
        hotkey_thread.start()
    except Exception as e:
        print(f"热键监听启动失败（可能需要管理员权限）: {e}")

    screen = chat.screen().availableGeometry()
    chat.move((screen.width() - chat.width()) // 2,
              (screen.height() - chat.height()) // 2)

    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
