"""AI 客户端 —— DeepSeek API 封装 + 标题生成"""
import os
from dotenv import load_dotenv
from openai import OpenAI

from src.memory import Memory

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


class AIClient:
    """DeepSeek API 客户端，负责 Agent 惰性初始化 + 标题生成"""

    def __init__(self, memory: Memory, kb=None, tray=None):
        self.memory = memory
        self.kb = kb
        self.tray = tray
        self.current_conv_id = None
        self._client = None
        self._agent_manager = None
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

    def generate_title(self, first_message: str) -> str:
        """根据对话第一句话，用 AI 生成简短标题"""
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
