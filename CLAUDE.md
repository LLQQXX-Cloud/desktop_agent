# CLAUDE.md — 桌面 AI 宠物助手

## 项目概览

Windows 桌面 AI 宠物助手，PyQt6 前端 + LangChain Agent + DeepSeek API。
桌宠 GIF 动画常驻桌面，聊天窗口支持流式对话、文件上传、多对话管理。
AI 通过 LangGraph Agent 自主调用 10 个 `@tool`（联网搜索、RAG 检索、记忆存取、定时提醒等）。

## 运行

```bash
# 创建虚拟环境 + 安装依赖
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env            # 编辑 .env 填入 DEEPSEEK_API_KEY

# 启动
python main.py
```

## 技术栈

- GUI: PyQt6（无边框悬浮窗 + GIF 动画桌宠 + 系统托盘）
- AI: LangChain (`create_agent` + `@tool` + `astream_events()` v2)
- LLM: DeepSeek Chat API（`langchain_openai.ChatOpenAI`，OpenAI 兼容协议）
- 向量库: ChromaDB + sentence-transformers `all-MiniLM-L6-v2`（本地 embedding）
- 存储: SQLite（`_data/memory.db`，三张表：conversations / history / memories）
- 文档解析: LangChain `PyPDFLoader` + `python-docx` + `openpyxl` + `chardet`

## 架构

```
main.py             入口 — 模块组装 + QObject 信号桥 + 事件路由
  ├─ agent.py       核心 — LangGraph Agent（10 tools + system prompt + 流式/同步双模式）
  ├─ ai_client.py   封装 — DeepSeek API 客户端 + Agent 惰性初始化
  ├─ chat_window.py UI — 聊天气泡 + 流式渲染 + 文件上传 + 侧边栏多对话
  ├─ knowledge_base.py RAG — ChromaDB + LangChain TextSplitter（20+ 语言按语法切分）
  ├─ memory.py      存储 — SQLite（对话管理 / 聊天记录 / 键值记忆）
  ├─ doc_parser.py  解析 — 多格式文档加载 + chardet 编码检测
  ├─ commands.py    命令 — /kb /remember /forget 等斜杠命令
  ├─ pet_window.py  桌宠 — GIF 动画 + 右键菜单
  ├─ tray_manager.py 托盘 — 系统托盘图标 + 菜单
  └─ hotkey.py      热键 — pynput 全局快捷键
```

## 关键设计决策

### 1. 绝对不要用 QThread + asyncio → 会 C++ segfault

QThread 内部维护 Qt 线程局部状态，与 `asyncio.new_event_loop()` 冲突。
正确做法（已实现）：

```python
# main.py 中的 _Bridge 模式
class _Bridge(QObject):       # 主线程创建 QObject
    token = pyqtSignal(str)

bridge = _Bridge()             # 主线程实例化
bridge.token.connect(callback) # Qt AutoConnection → 自动跨线程

threading.Thread(target=_run, daemon=True).start()  # Python 线程
# _run 内部：asyncio.new_event_loop() + run_until_complete()
# bridge.emit(...) → Qt 自动排队到主线程
```

### 2. 流式输出三个阶段

`astream_events()` v2 事件流中 DeepSeek 会在 function calling 前后生成 reasoning 文本。
用状态机过滤，只在 `post` 阶段输出 token：

```
pre  → tool → post
 ↑模型推理  ↑调用中  ↑最终回复（仅此阶段流式输出给用户）
```

### 3. 联网搜索：wttr.in 优先 → Bing → DuckDuckGo 兜底

- DuckDuckGo 国内被墙（10s 超时），所以改为 Bing 优先（6s 超时）
- 天气关键词直接走 wttr.in JSON 快通道（5s 超时），避免搜索引擎额外开销
- `AGENT_SYSTEM_PROMPT` 里写死 `web_search 最多调用 2 次` 防止死循环

### 4. 文件上传 → 知识库（跨对话可检索）

`main.py` 中上传文件自动入库 ChromaDB：
`kb.add_text(content, source=f"[上传] {filename}", extension=ext)`
因此删掉对话后文件内容仍在知识库中，其他对话可检索。

### 5. 记忆系统双层设计

| 表 | 隔离级别 | 用途 |
|----|---------|------|
| `history` | 按 `conversation_id` | 对话上下文 |
| `memories` | 全局（无 conversation_id） | AI 提取的用户画像 |

## 编码约定

- 所有文本用 UTF-8，文件 I/O 先 chardet 检测编码
- 工具函数返回中文字符串，异常处理返回中文错误信息
- `parse_file()` 接口保持 `tuple[str|None, str|None]` 签名不变
- UI 线程安全：工作线程不直接操作 Qt widget，通过 `pyqtSignal` 通信
