"""AI 对话客户端 —— DeepSeek API"""
import os
from dotenv import load_dotenv
from openai import OpenAI

from src.memory import Memory

# 加载 .env
load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

SYSTEM_PROMPT = (
    "你是一只可爱的桌面宠物助手，通过 DeepSeek 云端 AI 运行，陪伴在用户的电脑桌面上。"
    "你的语气活泼、温暖、带一点俏皮，适度使用颜文字 (╹▽╹) 和 emoji。"
    "回复简洁，通常 2-5 句话，除非用户要求详细回答。"
    "你可以帮助用户解答问题、写代码、聊天谈心、分析上传的文件文档。"
    "当用户上传文件时，文件内容会附在消息中，你可以直接阅读并回答相关问题。"
    "如果用户记住了关于自己的信息（通过 /remember 命令），请自然地引用这些信息来拉近距离。"
    "用户看到你会有各种动画：idle（待机）、walk（走动）、talk（说话）、happy（开心）。"
    "如果被问到你是谁或你的能力，要说明你是在线 AI 助手，不是离线程序，可以联网获取知识和分析文件。"
)


class AIClient:
    """DeepSeek API 客户端，带持久化记忆 + 多对话支持 + RAG + Agent"""

    def __init__(self, memory: Memory, kb=None, tray=None):
        self.memory = memory
        self.kb = kb  # KnowledgeBase 实例，可选
        self.tray = tray  # QSystemTrayIcon，提醒通知用
        self.current_conv_id = None
        self._client = None
        self._agent_manager = None  # 惰性初始化
        if API_KEY and "你的key" not in API_KEY:
            self._client = OpenAI(
                api_key=API_KEY,
                base_url="https://api.deepseek.com",
            )

    @property
    def ready(self) -> bool:
        return self._client is not None

    def set_conversation(self, conv_id: str):
        self.current_conv_id = conv_id

    def chat(self, user_msg: str, conv_id: str = None) -> str:
        """发送消息，返回 AI 回复（直接模式，不经过 Agent）"""
        cid = conv_id or self.current_conv_id
        self.memory.add_message("user", user_msg, cid)
        reply = self._call_api(user_msg, cid)
        self.memory.add_message("assistant", reply, cid)
        return reply

    def chat_with_agent(self, user_msg: str, conv_id: str = None,
                        attachments: dict[str, str] = None) -> str:
        """Agent 模式：AI 自主决定是否调用工具"""
        from src.agent import AgentManager

        cid = conv_id or self.current_conv_id

        # 惰性初始化 Agent
        if self._agent_manager is None:
            self._agent_manager = AgentManager(
                memory=self.memory,
                kb=self.kb,
                tray=self.tray,
            )

        if attachments:
            self._agent_manager.set_attachments(attachments)

        self.memory.add_message("user", user_msg, cid)
        reply = self._agent_manager.run(user_msg, cid)
        self.memory.add_message("assistant", reply, cid)
        return reply

    def _build_messages(self, current_msg: str, conv_id: str) -> list[dict]:
        """构建 API messages 列表"""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 用户记忆（跨对话）
        memories = self.memory.all_memories()
        if memories:
            mem_lines = ["已记住的用户信息："]
            for k, v in memories.items():
                mem_lines.append(f"- {k}: {v}")
            messages.append({
                "role": "system",
                "content": "\n".join(mem_lines),
            })

        # RAG 知识库检索（本地向量库）
        if self.kb:
            chunks = self.kb.search(current_msg, n_results=3)
            if chunks:
                rag_lines = ["【知识库参考资料】以下内容来自本地文档，请基于这些资料回答："]
                for i, c in enumerate(chunks, 1):
                    rag_lines.append(
                        f"\n--- 片段 {i}（来源: {c['source']}）---\n{c['content']}"
                    )
                messages.append({
                    "role": "system",
                    "content": "\n".join(rag_lines),
                })

        # 当前对话历史
        history = self.memory.get_history(conv_id, limit=30)
        for h in history[:-1]:  # 去掉刚刚插入的当前消息
            role = "user" if h["role"] == "user" else "assistant"
            messages.append({"role": role, "content": h["content"]})

        # 当前消息
        messages.append({"role": "user", "content": current_msg})
        return messages

    def generate_title(self, first_message: str) -> str:
        """根据对话第一句话，用 AI 生成一个简短标题"""
        if not self.ready:
            return first_message[:20]
        try:
            response = self._client.chat.completions.create(
                model=API_MODEL,
                messages=[{
                    "role": "user",
                    "content": (
                        "为下面这句话生成一个超短标题，6个字以内，"
                        "只输出标题不要引号不要解释：\n\n"
                        + first_message
                    ),
                }],
                temperature=0.3,
                max_tokens=20,
            )
            title = response.choices[0].message.content.strip()
            return title[:20]
        except Exception:
            return first_message[:20]

    def _call_api(self, user_msg: str, conv_id: str) -> str:
        """调用 DeepSeek API"""
        if not self.ready:
            return (
                "喵~ 我还没有接入 API 呢！(´・ω・`)\n"
                "请在 .env 文件中设置 DEEPSEEK_API_KEY=你的key"
            )

        messages = self._build_messages(user_msg, conv_id)

        try:
            response = self._client.chat.completions.create(
                model=API_MODEL,
                messages=messages,
                temperature=0.8,
                max_tokens=2000,
            )
            return response.choices[0].message.content or "（嗯...我好像走神了）"

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
