<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PyQt-6.0+-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6">
  <img src="https://img.shields.io/badge/LangChain-Agent-00C853?style=for-the-badge&logo=langchain&logoColor=white" alt="LangChain">
  <img src="https://img.shields.io/badge/DeepSeek-API-536DFE?style=for-the-badge&logo=openai&logoColor=white" alt="DeepSeek">
  <img src="https://img.shields.io/badge/ChromaDB-Vector-FF6F00?style=for-the-badge&logo=chroma&logoColor=white" alt="ChromaDB">
</p>

<h1 align="center">🦊 Desktop Agent</h1>
<p align="center"><strong>基于 LangChain Agent + DeepSeek 的桌面 AI 助手</strong></p>
<p align="center">桌宠形态 · Agent 自主决策 · 联网搜索 · RAG 知识库 · 跨对话记忆</p>

<p align="center">
  <a href="#-演示">🎬 演示</a> •
  <a href="#-核心特性">✨ 特性</a> •
  <a href="#-快速开始">🚀 快速开始</a> •
  <a href="#-技术架构">🏗 架构</a> •
  <a href="#-项目结构">📂 结构</a> •
  <a href="#-技术挑战">🔧 挑战</a>
</p>

---

## 🎬 演示

> 📝 截图占位，使用前请替换为实际截图

```
┌─────────────────────────────────────────────────────┐
│  桌面助手                                    ─  ✕   │
├──────────┬──────────────────────────────────────────┤
│ + 新对话 │                                          │
│          │   🦊 今天东莞天气怎么样？                    │
│ 东莞天气 │                                          │
│ 你好     │   🔧 正在调用 web_search...               │
│ 你叫什么 │                                          │
│          │   🌤️ 东莞实时天气：                        │
│          │   当前 34°C，晴间多云，湿度 63%...          │
│          │                                          │
│          │   ───────────────────────────────────    │
│          │   输入消息，按回车发送...    [📎] [发送]   │
└──────────┴──────────────────────────────────────────┘
```

## ✨ 核心特性

<table>
<tr>
  <td width="50%">

### 🤖 Agent 自主工具调用

10 个 LangChain `@tool`，AI 自主决定何时调用、调用哪个，无需硬编码逻辑。

- 🔍 `web_search` — 联网搜索（天气/新闻/实时数据）
- 📚 `search_knowledge_base` — ChromaDB 语义检索本地文档
- 🧠 `recall_memory` / `save_memory` — 跨对话用户画像
- 📄 `read_uploaded_file` — 实时读取上传文件内容
- 💬 `search_chat_history` — 模糊搜索历史对话
- ⏰ `set_reminder` / `list_reminders` / `cancel_reminder` — 定时提醒

  </td>
  <td width="50%">

### ⚡ 流式输出

Token-by-token 实时渲染，50ms QTimer 驱动气泡刷新。工具调用时展示状态栏（"🔧 正在调用 web_search..."），工具返回后无缝切换回 token 流。

### 🌐 联网搜索 + 天气

wttr.in 快通道（天气，5s 超时）→ Bing 搜索（通用，6s 超时）→ DuckDuckGo 兜底。中文天气关键词自动识别。

### 📚 RAG 知识库

上传文件 → chardet 编码检测 → LangChain 按语法边界切片（20+ 语言）→ ChromaDB 向量化 → 语义检索。

  </td>
</tr>
</table>

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows / macOS / Linux

### 1. 克隆仓库

```bash
git clone https://github.com/你的用户名/desk-agent.git
cd desk-agent
```

### 2. 创建虚拟环境

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key
```

`.env` 文件内容：

```env
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_MODEL=deepseek-chat
```

> 💡 DeepSeek API Key 可在 [platform.deepseek.com](https://platform.deepseek.com) 免费获取

### 5. 启动

```bash
python main.py
```

## 🏗 技术架构

```
┌──────────────────────────────────────────────────────┐
│                     main.py                          │
│          (模块组装 · 信号桥 · 事件路由)                │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐    ┌─────────────────────────────┐ │
│  │  桌宠窗口     │    │        聊天窗口              │ │
│  │  pet_window  │    │       chat_window           │ │
│  │  GIF 动画    │    │  气泡渲染 · 流式显示         │ │
│  │  右键菜单    │    │  文件上传 · 多对话管理       │ │
│  └──────────────┘    └───────────┬─────────────────┘ │
│                                  │                   │
│                    threading.Thread + asyncio        │
│                    QObject 信号桥（跨线程安全）       │
│                                  │                   │
│  ┌───────────────────────────────┴────────────────┐  │
│  │              AgentManager (agent.py)            │  │
│  │  LangChain create_agent() · DeepSeek API        │  │
│  │  10 @tool · astream_events() · 状态机过滤       │  │
│  └────┬──────────┬──────────┬─────────────────────┘  │
│       │          │          │                        │
│  ┌────▼──┐ ┌────▼──┐ ┌─────▼──────┐                 │
│  │Memory │ │  KB   │ │ doc_parser │                 │
│  │SQLite │ │ChromaDB│ │ LangChain │                 │
│  │对话+  │ │向量检索│ │ loaders   │                 │
│  │记忆   │ │        │ │ + chardet │                 │
│  └───────┘ └───────┘ └───────────┘                 │
└──────────────────────────────────────────────────────┘
```

### 数据流

```
用户输入 → main.py
              │
              ├─ /开头 → commands.py（斜杠命令）
              └─ 其他 → AgentManager.run_stream()
                           │
                           ▼
                     LangChain Agent
                     自主决策 → 调工具 → 综合 → 回复
                           │
                           ▼ (token by token)
                     QObject 信号桥
                           │
                           ▼
                     ChatWindow 流式渲染
```

### 为什么不用 QThread？

`QThread` 内部维护 Qt 线程局部存储，与 `asyncio.new_event_loop()` 冲突，导致 C++ 层 segfault（无 Python traceback）。解决方案：

```python
# ❌ QThread + asyncio → segfault
# ✅ threading.Thread + asyncio + QObject 信号桥
class _Bridge(QObject):
    token = pyqtSignal(str)

bridge = _Bridge()                    # 主线程创建
bridge.token.connect(ui_callback)     # Qt AutoConnection

def _run():
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_stream())

threading.Thread(target=_run).start()  # 工作线程
# bridge.emit(...) → Qt 自动跨线程排队到主线程
```

## 📂 项目结构

```
desk_agent/
├── main.py                  # 入口：模块组装 + QObject 信号桥
├── requirements.txt         # 依赖清单
├── .env.example             # API Key 模板
├── .gitignore
├── assets/
│   └── pet/                 # 桌宠 GIF 素材
│       ├── idle_1.gif
│       ├── idle_2.gif
│       ├── walk.gif
│       └── talk.gif
├── src/
│   ├── agent.py             # LangChain Agent 核心
│   │                        #   · 10 个 @tool 工具定义
│   │                        #   · AGENT_SYSTEM_PROMPT
│   │                        #   · AgentManager（同步 + 流式）
│   │                        #   · ReminderChecker 后台线程
│   ├── ai_client.py         # DeepSeek API 客户端
│   ├── chat_window.py       # PyQt6 聊天悬浮窗口
│   │                        #   · 气泡 HTML 渲染
│   │                        #   · 流式 token 显示（QTimer 50ms）
│   │                        #   · 文件拖拽上传 + 预览
│   │                        #   · 多对话侧边栏管理
│   ├── knowledge_base.py    # ChromaDB 向量知识库
│   │                        #   · LangChain TextSplitter
│   │                        #   · 20+ 语言按语法边界切分
│   │                        #   · 本地 embedding（all-MiniLM-L6-v2）
│   ├── memory.py            # SQLite 数据层
│   │                        #   · conversations 表（多对话）
│   │                        #   · history 表（聊天记录）
│   │                        #   · memories 表（跨对话用户画像）
│   ├── doc_parser.py        # 文档解析
│   │                        #   · LangChain PyPDFLoader
│   │                        #   · python-docx / openpyxl
│   │                        #   · chardet 自动编码检测
│   ├── pet_window.py        # 桌宠窗体（GIF 动画 + 右键菜单）
│   ├── tray_manager.py      # 系统托盘 + 右键菜单
│   ├── hotkey.py            # 全局热键（pynput）
│   └── commands.py          # 斜杠命令（/kb、/remember 等）
└── _data/                   # 运行数据（不入 git）
    ├── memory.db            #   SQLite 数据库
    ├── kb/                  #   ChromaDB 持久化目录
    └── uploads/             #   用户上传文件
```

## 🔧 技术挑战

| 挑战 | 根因 | 解决方案 |
|------|------|---------|
| **QThread + asyncio C++ segfault** | QThread 内部 Qt 线程状态与 asyncio event loop 冲突 | 改用 `threading.Thread` + `asyncio.new_event_loop()` + QObject 信号桥 |
| **流式回复混入模型推理文本** | DeepSeek 在 function calling 前生成 reasoning 文本 | 状态机（pre → tool → post），仅在 post 阶段流式输出 token |
| **DuckDuckGo 国内被墙 → 20s 阻塞** | DDG 超时 10s + Bing 超时 10s，UI 卡死 | wttr.in（天气快通道 5s）+ Bing 优先（6s）+ DDG 兜底 |
| **finish_streaming 被状态栏 HTML 污染** | `_flush_stream()` 将 `<i>` 标签写入 buffer，`html.escape()` 后变成乱码 | 定稿前清空思考状态，做一次纯净 flush |
| **Windows GBK 终端 + UTF-8 文件编码冲突** | 用户文件编码多样，硬编码 `utf-8 → gbk → latin-1` 不可靠 | chardet 自动检测 + 置信度 <0.6 多编码兜底 |

## 📝 依赖

| 分类 | 包 | 用途 |
|------|-----|------|
| GUI | PyQt6 | 无边框悬浮窗 + 桌宠动画 + 托盘 |
| AI 框架 | langchain, langchain-openai, langchain-community | Agent 工具调用 + 文档加载器 + 文本切分 |
| LLM | openai | DeepSeek API（OpenAI 兼容协议） |
| 向量库 | chromadb | 本地向量检索（all-MiniLM-L6-v2） |
| 文档 | python-docx, openpyxl, PyPDF2, chardet | 多格式解析 + 编码检测 |
| 配置 | python-dotenv | .env 管理 API Key |
| 桌宠 | Pillow | GIF 帧解析 |
| 热键 | pynput | 全局快捷键监听 |

## 🗺 路线图

- [ ] 语音输入 / 语音播报
- [ ] 多轮对话自动摘要（ConversationSummaryMemory）
- [ ] 桌面截图识别（视觉问答）
- [ ] 插件系统（用户自定义工具）
- [ ] macOS / Linux 完整适配

## 📄 License

MIT

---

<p align="center">
  <sub>Built with ❤️ and lots of ☕ | <a href="https://platform.deepseek.com">Powered by DeepSeek</a></sub>
</p>
