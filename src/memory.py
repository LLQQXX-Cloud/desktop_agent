"""数据记忆模块 —— SQLite 持久化存储 + 多轮对话管理"""
import sqlite3
import os
import uuid
from datetime import datetime


class Memory:
    """持久化记忆：多轮对话历史 + 用户键值记忆

    数据存在 _data/memory.db（SQLite），自动建表迁移。
    """

    def __init__(self, data_dir="_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.db_path = os.path.join(data_dir, "memory.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()

    # ================================================================
    #  建表 + 迁移
    # ================================================================

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                role            TEXT    NOT NULL,
                content         TEXT    NOT NULL,
                conversation_id TEXT    DEFAULT NULL REFERENCES conversations(id),
                created_at      TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        # 兼容旧表：给可能没有 conversation_id 的历史记录补上
        try:
            self.conn.execute(
                "ALTER TABLE history ADD COLUMN conversation_id TEXT REFERENCES conversations(id)"
            )
        except sqlite3.OperationalError:
            pass  # 列已存在
        self.conn.commit()

    # ================================================================
    #  对话管理
    # ================================================================

    def create_conversation(self, title: str = "新对话") -> str:
        cid = uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (cid, title, now, now)
        )
        self.conn.commit()
        return cid

    def list_conversations(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [
            {"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]}
            for r in rows
        ]

    def delete_conversation(self, conv_id: str):
        self.conn.execute("DELETE FROM history WHERE conversation_id = ?", (conv_id,))
        self.conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        self.conn.commit()

    def rename_conversation(self, conv_id: str, title: str):
        self.conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, datetime.now().isoformat(), conv_id)
        )
        self.conn.commit()

    def get_conversation(self, conv_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conv_id,)
        ).fetchone()
        if row:
            return {"id": row[0], "title": row[1], "created_at": row[2], "updated_at": row[3]}
        return None

    # ================================================================
    #  对话历史（带 conversation_id）
    # ================================================================

    def add_message(self, role: str, content: str, conv_id: str = None):
        self.conn.execute(
            "INSERT INTO history (role, content, conversation_id, created_at) VALUES (?, ?, ?, ?)",
            (role, content, conv_id, datetime.now().isoformat())
        )
        # 更新对话时间
        if conv_id:
            self.conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), conv_id)
            )
        self.conn.commit()

    def get_history(self, conv_id: str = None, limit: int = 50) -> list[dict]:
        if conv_id:
            rows = self.conn.execute(
                "SELECT role, content, created_at FROM history "
                "WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conv_id, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT role, content, created_at FROM history "
                "ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [
            {"role": r[0], "content": r[1], "time": r[2]}
            for r in reversed(rows)
        ]

    def clear_history(self, conv_id: str = None):
        if conv_id:
            self.conn.execute("DELETE FROM history WHERE conversation_id = ?", (conv_id,))
        else:
            self.conn.execute("DELETE FROM history")
        self.conn.commit()

    # ================================================================
    #  用户记忆（键值对）
    # ================================================================

    def remember(self, key: str, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO memories (key, value, updated_at) VALUES (?, ?, ?)",
            (key, str(value), datetime.now().isoformat())
        )
        self.conn.commit()

    def recall(self, key: str):
        row = self.conn.execute(
            "SELECT value FROM memories WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def forget(self, key: str):
        self.conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        self.conn.commit()

    def all_memories(self) -> dict:
        rows = self.conn.execute(
            "SELECT key, value FROM memories ORDER BY updated_at DESC"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    # ================================================================
    #  模糊搜索
    # ================================================================

    def search_history(self, keyword: str, conv_id: str = None, limit: int = 20) -> list[dict]:
        if conv_id:
            rows = self.conn.execute(
                "SELECT role, content, created_at FROM history "
                "WHERE content LIKE ? AND conversation_id = ? ORDER BY id DESC LIMIT ?",
                (f"%{keyword}%", conv_id, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT role, content, created_at FROM history "
                "WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{keyword}%", limit)
            ).fetchall()
        return [
            {"role": r[0], "content": r[1], "time": r[2]}
            for r in reversed(rows)
        ]
