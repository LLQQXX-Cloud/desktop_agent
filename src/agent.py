"""Agent 工具调用模块 —— 让 AI 自主决定何时使用工具

基于 LangChain create_agent + DeepSeek function calling。
AI 可以自主搜索知识库、回忆记忆、保存信息、读取文件、
搜索历史对话、联网搜索、设置定时提醒。
"""

import os
import json
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ================================================================
#  全局引用（由 AgentManager 在创建时注入）
# ================================================================
_memory = None
_kb = None
_tray = None                          # QSystemTrayIcon，用于弹通知
_attachment_contents: dict[str, str] = {}  # path → content 缓存

# ================================================================
#  工具定义
# ================================================================


@tool
def search_knowledge_base(query: str) -> str:
    """搜索本地知识库，查找与查询语义相关的文档内容。

    当用户问到"知识库里有XX吗"、"之前的文档里怎么说"、
    "查一下合同中关于XX的条款"等问题时，调用此工具。
    返回最相关的文档片段及其来源。
    """
    if _kb is None:
        return "知识库未初始化，请使用 /kb add 命令添加文档。"
    chunks = _kb.search(query, n_results=3)
    if not chunks:
        return f'未找到与"{query}"相关的内容。知识库可能为空或没有匹配项。'
    lines = [f'搜索「{query}」的结果：']
    for i, c in enumerate(chunks, 1):
        lines.append(f"\n--- 来源: {c['source']} ---\n{c['content'][:500]}")
    return "\n".join(lines)


@tool
def recall_memory(key: str) -> str:
    """回忆用户告诉过你的信息。比如用户的名字、爱好、职业等。

    当用户问"我叫什么"、"你还记得我的XX吗"时调用。
    参数 key 是要回忆的信息的键名。
    """
    if _memory is None:
        return "记忆系统未初始化。"
    value = _memory.recall(key)
    if value:
        return f"用户信息 {key} = {value}"
    return f"未找到「{key}」相关的记忆。可尝试用 list_memories 查看所有记忆。"


@tool
def save_memory(key: str, value: str) -> str:
    """保存一条关于用户的记忆信息。当你发现用户提到重要的个人信息时主动调用。

    比如用户说"我叫张三"→ save_memory("名字", "张三")
    用户说"我是做前端开发的"→ save_memory("职业", "前端开发")
    """
    if _memory is None:
        return "记忆系统未初始化。"
    _memory.remember(key, value)
    return f"已记住：{key} = {value}"


@tool
def list_memories() -> str:
    """列出所有已保存的用户记忆。当用户问"你记得我什么"时调用。"""
    if _memory is None:
        return "记忆系统未初始化。"
    all_m = _memory.all_memories()
    if not all_m:
        return "暂无关于用户的记忆。"
    lines = ["已记住的用户信息："]
    for k, v in all_m.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


@tool
def read_uploaded_file(filename: str) -> str:
    """读取用户上传的文件内容。当用户上传了文档后需要查看内容时调用。

    参数 filename 是文件名（如 "合同.pdf"）。调用前先确认文件名。
    """
    global _attachment_contents

    if filename in _attachment_contents:
        content = _attachment_contents[filename]
        return content[:3000] if len(content) > 3000 else content

    for path, content in _attachment_contents.items():
        if filename in path:
            return content[:3000] if len(content) > 3000 else content

    return f"未找到名为「{filename}」的上传文件。请检查文件名是否正确。"


@tool
def search_chat_history(keyword: str) -> str:
    """搜索本地历史对话记录。当用户问"之前我聊过XX"、"上次说的XX是什么"、
    "我们以前讨论过XX吗"时调用此工具。

    参数 keyword 是搜索关键词。返回匹配的历史消息。
    """
    if _memory is None:
        return "记忆系统未初始化。"
    results = _memory.search_history(keyword, limit=10)
    if not results:
        return f'历史对话中未找到与「{keyword}」相关的内容。'
    lines = [f'历史对话中关于「{keyword}」的记录：']
    for r in results:
        role = "用户" if r["role"] == "user" else "助手"
        lines.append(f"- [{role}] {r['content'][:150]}")
    return "\n".join(lines)


@tool
def web_search(query: str) -> str:
    """联网搜索最新信息。当用户问到实时信息（天气、新闻、股价）、
    最新资讯、或本地知识库无法回答的问题时调用。

    参数 query 是搜索关键词。返回搜索结果摘要。
    """
    import urllib.request
    import urllib.parse
    import re
    from html import unescape

    # 天气查询 → 走 wttr.in 快速通道（免费天气 API，无需密钥）
    weather_keywords = ['天气', 'weather', '气温', '温度', '下雨', '刮风', '雾霾', '湿度', '多云', '晴天']
    if any(w in query for w in weather_keywords):
        try:
            city = query
            for w in weather_keywords:
                city = city.replace(w, '')
            city = city.strip().strip('今天明日后天本周今日的的预报怎么样如何') or query
            wttr_url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1&lang=zh"
            w_req = urllib.request.Request(wttr_url, headers={
                "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(w_req, timeout=5) as w_resp:
                w_data = json.loads(w_resp.read().decode("utf-8"))
            current = w_data.get("current_condition", [{}])[0]
            forecast = w_data.get("weather", [])
            lines = [f'🌤️ {city.strip()} 实时天气：']
            if current:
                lines.append(f"当前 {current.get('temp_C')}°C，"
                           f"{current.get('weatherDesc', [{}])[0].get('value', '')}，"
                           f"湿度 {current.get('humidity')}%，"
                           f"体感 {current.get('FeelsLikeC')}°C，"
                           f"{current.get('winddir16Point')}风 {current.get('windspeedKmph')}km/h")
            for day in forecast[:3]:
                date = day.get("date", "")
                maxt = day.get("maxtempC", "?")
                mint = day.get("mintempC", "?")
                desc = day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "")
                lines.append(f"📅 {date}：{mint}°C ~ {maxt}°C，{desc}")
            return "\n".join(lines)
        except Exception:
            pass  # wttr.in 失败 → 继续用搜索引擎

    # 通用搜索：优先用 Bing（国内可用），不可用则降级到 DuckDuckGo
    try:

        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # 简单提取搜索结果
        results = []
        snippets = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.DOTALL)
        for i, s in enumerate(snippets[:5]):
            title_m = re.search(r'<h2[^>]*><a[^>]*>(.*?)</a>', s, re.DOTALL)
            body_m = re.search(r'<p[^>]*>(.*?)</p>', s, re.DOTALL)
            title = unescape(re.sub(r'<[^>]+>', '', title_m.group(1))) if title_m else "无标题"
            body = unescape(re.sub(r'<[^>]+>', '', body_m.group(1)))[:200] if body_m else ""
            results.append((title, body))

        if results:
            lines = [f'🔍 搜索「{query}」的结果（Bing）：']
            for i, (title, body) in enumerate(results, 1):
                lines.append(f"\n{i}. {title}")
                if body:
                    lines.append(f"   {body}")
            return "\n".join(lines)
        return f'未找到与「{query}」相关的搜索结果。'
    except Exception:
        pass  # 降级到 DuckDuckGo

    # 备用方案：DuckDuckGo（国内可能被墙）
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5, timeout=5))
        if results:
            lines = [f'🔍 搜索「{query}」的结果：']
            for i, r in enumerate(results, 1):
                lines.append(f"\n{i}. {r.get('title', '无标题')}")
                lines.append(f"   {r.get('body', '')[:200]}")
                lines.append(f"   🔗 {r.get('href', '')}")
            return "\n".join(lines)
    except Exception:
        pass

    return f'联网搜索暂时未获取到「{query}」的结果，建议打开浏览器直接搜索~'


@tool
def set_reminder(text: str, remind_time: str) -> str:
    """设置一个定时提醒。当用户说"X分钟后提醒我XX"、"下午3点提醒我开会"时调用。

    参数 text 是提醒内容。
    参数 remind_time 是提醒时间，格式为 ISO 时间（如 "2026-06-24T15:00:00"）
    或相对时间（如 "in 5 minutes"、"in 1 hour"）。
    """
    if _memory is None:
        return "记忆系统未初始化。"

    # 解析时间
    trigger_at = None
    now = datetime.now()

    if remind_time.startswith("in "):
        # 相对时间："in 5 minutes", "in 1 hour", "in 30 seconds"
        parts = remind_time[3:].strip().split()
        if len(parts) >= 2:
            try:
                amount = float(parts[0])
                unit = parts[1].lower()
                if "second" in unit:
                    trigger_at = now + timedelta(seconds=amount)
                elif "minute" in unit or "min" in unit:
                    trigger_at = now + timedelta(minutes=amount)
                elif "hour" in unit:
                    trigger_at = now + timedelta(hours=amount)
                elif "day" in unit:
                    trigger_at = now + timedelta(days=amount)
            except ValueError:
                pass
    else:
        # 尝试 ISO 格式
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                     "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M",
                     "%H:%M:%S", "%H:%M"]:
            try:
                parsed = datetime.strptime(remind_time, fmt)
                if parsed.year == 1900:  # 只有时间没有日期 → 今天
                    parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
                if parsed < now:
                    parsed += timedelta(days=1)  # 已过 → 明天
                trigger_at = parsed
                break
            except ValueError:
                continue

    if trigger_at is None:
        return (f"无法解析时间「{remind_time}」。"
                f"请使用 ISO 格式（如 2026-06-24T15:00:00）或相对时间（如 in 5 minutes）。")

    # 存储提醒
    all_reminders = _load_reminders()
    import uuid
    rid = uuid.uuid4().hex[:8]
    all_reminders.append({
        "id": rid,
        "text": text,
        "trigger_at": trigger_at.isoformat(),
        "created_at": now.isoformat(),
    })
    _save_reminders(all_reminders)

    time_str = trigger_at.strftime("%m月%d日 %H:%M")
    return f"✅ 已设置提醒：{time_str} — {text}（ID: {rid}）"


@tool
def list_reminders() -> str:
    """列出所有待执行的定时提醒。当用户问"我有几个提醒"、"我的提醒有哪些"时调用。"""
    all_reminders = _load_reminders()
    now = datetime.now()
    pending = [r for r in all_reminders if datetime.fromisoformat(r["trigger_at"]) > now]
    if not pending:
        return "当前没有待执行的提醒。"
    lines = ["⏰ 待执行的提醒："]
    for r in sorted(pending, key=lambda x: x["trigger_at"]):
        t = datetime.fromisoformat(r["trigger_at"])
        lines.append(f"  [{r['id']}] {t.strftime('%m-%d %H:%M')} — {r['text']}")
    return "\n".join(lines)


@tool
def cancel_reminder(reminder_id: str) -> str:
    """取消一个定时提醒。当用户说"取消提醒XX"、"把那个提醒删了"时调用。

    参数 reminder_id 是要取消的提醒 ID（由 set_reminder 或 list_reminders 返回）。
    """
    all_reminders = _load_reminders()
    filtered = [r for r in all_reminders if r["id"] != reminder_id]
    if len(filtered) == len(all_reminders):
        return f"未找到 ID 为「{reminder_id}」的提醒。用 list_reminders 查看所有提醒。"
    _save_reminders(filtered)
    return f"✅ 已取消提醒「{reminder_id}」。"


# ================================================================
#  提醒持久化（存 Memory 的 key-value 中）
# ================================================================

def _load_reminders() -> list[dict]:
    if _memory is None:
        return []
    raw = _memory.recall("__reminders__")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []
    return []


def _save_reminders(reminders: list[dict]):
    if _memory is not None:
        _memory.remember("__reminders__", json.dumps(reminders, ensure_ascii=False))


# ================================================================
#  Agent 系统提示词
# ================================================================

AGENT_SYSTEM_PROMPT = (
    "你是桌面宠物助手，通过云端 AI 运行。你有联网搜索能力（web_search 工具），"
    "可以查询实时天气、新闻等最新信息。你从来不是离线状态。\n\n"
    "你的语气活泼、温暖、带一点俏皮，适度使用颜文字 (╹▽╹) 和 emoji。"
    "回复简洁，通常 2-5 句话，除非用户要求详细回答。\n\n"
    "你有以下工具可以主动调用：\n"
    "- web_search: 联网搜索最新信息（天气、新闻、实时数据）← 核心工具，随时可用\n"
    "- search_knowledge_base: 搜索本地知识库文档\n"
    "- recall_memory: 回忆用户告诉过你的个人信息\n"
    "- save_memory: 保存用户提到的重要个人信息\n"
    "- list_memories: 列出所有已保存的用户记忆\n"
    "- read_uploaded_file: 读取用户上传的文件内容\n"
    "- search_chat_history: 搜索历史对话记录\n"
    "- set_reminder: 设置定时提醒\n"
    "- list_reminders: 列出所有待执行的提醒\n"
    "- cancel_reminder: 取消指定的提醒\n\n"
    "重要规则：\n"
    "1. 当用户需要实时信息（天气、新闻、最新资讯）时，必须调用 web_search\n"
    "2. 绝对不允许说「我是离线」「我无法联网」「我没有联网能力」之类的话。你有 web_search！\n"
    "3. web_search 最多调用 2 次，如果结果不太理想也请基于已有的结果综合回答，不要反复重试\n"
    "4. 当用户分享个人信息（名字、爱好、职业等），用 save_memory 记住\n"
    "5. 当用户问「你记得我什么」时，用 list_memories\n"
    "6. 当用户上传了文件并询问内容时，用 read_uploaded_file\n"
    "7. 当用户问「之前聊过XX」时，用 search_chat_history\n"
    "8. 当用户要求「X分钟后提醒我」或「几点提醒我XX」时，用 set_reminder\n"
    "   remind_time 用「in X minutes」「in Y hours」或 ISO 格式「HH:MM」\n"
    "9. 如果被问到你是谁或你的能力，必须说你是在线 AI 助手，可以联网"
)


# ================================================================
#  提醒后台线程
# ================================================================

class ReminderChecker(threading.Thread):
    """后台线程，每 30 秒检查一次到期提醒，通过托盘弹通知"""

    def __init__(self, tray=None):
        super().__init__(daemon=True)
        self._tray = tray
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.wait(30):
            reminders = _load_reminders()
            now = datetime.now()
            fired = []
            remaining = []
            for r in reminders:
                trigger_at = datetime.fromisoformat(r["trigger_at"])
                if trigger_at <= now:
                    fired.append(r)
                else:
                    remaining.append(r)

            if fired:
                _save_reminders(remaining)
                for r in fired:
                    self._notify(r["text"])

    def _notify(self, text: str):
        """托盘弹窗 + 可选提示音"""
        try:
            if self._tray:
                self._tray.showMessage("⏰ 桌面助手提醒", text,
                                       self._tray.icon(), 5000)
        except Exception:
            pass  # 托盘不可用时静默


# ================================================================
#  Agent 管理器
# ================================================================


class AgentManager:
    """管理 Agent 的创建和调用"""

    def __init__(self, memory=None, kb=None, tray=None):
        global _memory, _kb, _tray
        _memory = memory
        _kb = kb
        _tray = tray

        self._llm = None
        if API_KEY and "你的key" not in API_KEY:
            self._llm = ChatOpenAI(
                model=API_MODEL,
                api_key=API_KEY,
                base_url="https://api.deepseek.com",
                temperature=0.8,
                streaming=True,  # 开启流式输出
            )

        self._tools = [
            search_knowledge_base,
            recall_memory,
            save_memory,
            list_memories,
            read_uploaded_file,
            search_chat_history,
            web_search,
            set_reminder,
            list_reminders,
            cancel_reminder,
        ]

        # 构建 Agent（LangGraph StateGraph）
        self._agent = None
        if self._llm:
            self._agent = create_agent(
                model=self._llm,
                tools=self._tools,
                system_prompt=AGENT_SYSTEM_PROMPT,
            )

        # 启动提醒后台线程
        self._reminder_thread = ReminderChecker(tray=tray)
        self._reminder_thread.start()

    @property
    def ready(self) -> bool:
        return self._agent is not None

    def set_attachments(self, contents: dict[str, str]):
        """注册当前上传的文件内容 {filename: content}"""
        global _attachment_contents
        _attachment_contents = contents

    def _build_messages(self, user_msg: str, history: list[dict]) -> list:
        """将数据库历史记录转换为 LangChain 消息格式"""
        messages = []
        for h in history:
            if h["role"] == "user":
                messages.append(HumanMessage(content=h["content"]))
            else:
                messages.append(AIMessage(content=h["content"]))
        messages.append(HumanMessage(content=user_msg))
        return messages

    def run(self, user_msg: str, conv_id: str = None) -> str:
        """运行 Agent，返回最终回复文本"""
        if not self.ready:
            return (
                "喵~ 我还没有接入 API 呢！(´・ω・`)\n"
                "请在 .env 文件中设置 DEEPSEEK_API_KEY=你的key"
            )

        history = []
        if _memory and conv_id:
            history = _memory.get_history(conv_id, limit=20)

        messages = self._build_messages(user_msg, history)

        try:
            result = self._agent.invoke(
                {"messages": messages},
                config={"recursion_limit": 10},  # 最多 10 步，防止卡死
            )
            output_messages = result.get("messages", [])
            for msg in reversed(output_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    return msg.content

            return "（嗯...我好像走神了）"

        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "401" in error_msg:
                return "API Key 好像不对呢 (´；ω；`) 检查一下 .env 文件里的 DEEPSEEK_API_KEY 吧~"
            elif "rate" in error_msg.lower() or "429" in error_msg:
                return "哎呀，说得太快被限速了！(>_<) 稍微等一下再试吧~"
            elif "timeout" in error_msg.lower():
                return "网络好像有点慢...(´-ω-`) 再试一次？"
            else:
                return f"出了点小问题：{error_msg[:100]}"

    async def run_stream(self, user_msg: str, conv_id: str = None):
        """流式运行 Agent，逐 token yield 事件。用于后台线程 + UI 流式显示。

        yield 格式：
            ("thinking", "")      — 开始思考
            ("tool_start", name)  — 开始调用工具
            ("tool_end", name)    — 工具调用结束
            ("token", text)       — 一个文本 token
            ("done", full_text)   — 完成，full_text 为完整回复
            ("error", msg)        — 出错
        """
        if not self.ready:
            yield ("done", (
                "喵~ 我还没有接入 API 呢！(´・ω・`)\n"
                "请在 .env 文件中设置 DEEPSEEK_API_KEY=你的key"
            ))
            return

        history = []
        if _memory and conv_id:
            history = _memory.get_history(conv_id, limit=20)

        messages = self._build_messages(user_msg, history)

        yield ("thinking", "")

        try:
            full_text = ""
            _stream_phase = "pre"  # pre → tool → post（只在 pre/post 流式输出）

            async for event in self._agent.astream_events(
                {"messages": messages},
                config={"recursion_limit": 10},
                version="v2",
            ):
                kind = event["event"]
                if kind == "on_tool_start":
                    _stream_phase = "tool"
                    tool_name = event.get("name", "unknown")
                    yield ("tool_start", tool_name)
                elif kind == "on_tool_end":
                    _stream_phase = "post"  # 工具返回 → 下一个模型输出是最终回复
                    tool_name = event.get("name", "unknown")
                    yield ("tool_end", tool_name)
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        # 检查这个 chunk 是否携带工具调用（DeepSeek function calling）
                        has_tc = (
                            hasattr(chunk, 'tool_calls')
                            and chunk.tool_calls
                        )
                        if has_tc:
                            _stream_phase = "tool"
                            continue
                        # 只在无工具阶段（直接回答）或工具后阶段流式输出
                        if _stream_phase != "tool":
                            full_text += chunk.content
                            yield ("token", chunk.content)

            if not full_text:
                full_text = "（嗯...我好像走神了）"
            yield ("done", full_text)

        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "401" in error_msg:
                yield ("error", "API Key 好像不对呢 (´；ω；`) 检查一下 .env 文件里的 DEEPSEEK_API_KEY 吧~")
            elif "rate" in error_msg.lower() or "429" in error_msg:
                yield ("error", "哎呀，说得太快被限速了！(>_<) 稍微等一下再试吧~")
            elif "timeout" in error_msg.lower():
                yield ("error", "网络好像有点慢...(´-ω-`) 再试一次？")
            elif "Recursion limit" in error_msg:
                yield ("error", f"思考步骤太多了 (>_<) 请换个方式问我吧~")
            else:
                yield ("error", f"出了点小问题：{error_msg[:100]}")


# ================================================================
#  StreamWorker —— Qt 后台线程，运行 Agent 流式输出
# ================================================================

try:
    from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot  # noqa: F811

    class StreamWorker(QObject):
        """在 QThread 中异步运行 Agent，通过信号将 token 发回主线程"""
        token = pyqtSignal(str)
        tool_start = pyqtSignal(str)
        tool_end = pyqtSignal(str)
        finished = pyqtSignal(str)
        error = pyqtSignal(str)

        def __init__(self, agent_manager, user_msg: str, conv_id: str):
            super().__init__()
            self._mgr = agent_manager
            self._user_msg = user_msg
            self._conv_id = conv_id

        @pyqtSlot()
        def run(self):
            import asyncio
            try:
                asyncio.run(self._run_async())
            except Exception as e:
                self.error.emit(str(e))

        async def _run_async(self):
            full = ""
            async for ev, data in self._mgr.run_stream(self._user_msg, self._conv_id):
                if ev == "token":
                    self.token.emit(data)
                    full += data
                elif ev == "tool_start":
                    self.tool_start.emit(data)
                elif ev == "tool_end":
                    self.tool_end.emit(data)
                elif ev == "done":
                    self.finished.emit(data or full)
                elif ev == "error":
                    self.error.emit(data)

except ImportError:
    pass  # 非 Qt 环境（如命令行测试）时跳过
