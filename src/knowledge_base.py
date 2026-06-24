"""知识库模块 —— 基于 ChromaDB 的本地向量检索

提供文档索引、语义搜索、来源管理功能。
嵌入模型：sentence-transformers all-MiniLM-L6-v2（本地运行，首次自动下载）
文本切分：LangChain RecursiveCharacterTextSplitter
"""

import os
import uuid
import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

# ================================================================
#  文件扩展名 → LangChain Language 映射（支持按语法切分代码）
# ================================================================
_EXTENSION_TO_LANGUAGE: dict[str, Language] = {
    ".py":    Language.PYTHON,
    ".js":    Language.JS,
    ".ts":    Language.TS,
    ".java":  Language.JAVA,
    ".c":     Language.C,
    ".cpp":   Language.CPP,
    ".h":     Language.CPP,
    ".cs":    Language.CSHARP,
    ".go":    Language.GO,
    ".rs":    Language.RUST,
    ".rb":    Language.RUBY,
    ".php":   Language.PHP,
    ".swift": Language.SWIFT,
    ".kt":    Language.KOTLIN,
    ".scala": Language.SCALA,
    ".lua":   Language.LUA,
    ".r":     Language.R,
    ".sh":    Language.PYTHON,   # shell 用 Python 分隔符凑合
    ".bat":   Language.PYTHON,
    ".ps1":   Language.POWERSHELL,
    ".html":  Language.HTML,
    ".css":   Language.HTML,     # CSS 不是独立语言，用 HTML 分隔符
    ".md":    Language.MARKDOWN,
    ".sql":   Language.SOL,
    ".proto": Language.PROTO,
    ".rst":   Language.RST,
    ".tex":   Language.LATEX,
    ".lua":   Language.LUA,
    ".haskell": Language.HASKELL,
    ".elixir":  Language.ELIXIR,
    ".perl":    Language.PERL,
    ".cobol":   Language.COBOL,
    ".vb":      Language.VISUALBASIC6,
}


class KnowledgeBase:
    """本地向量知识库，持久化到 _data/kb/"""

    def __init__(self, persist_dir: str = "_data/kb"):
        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="documents",
        )

    # ================================================================
    #  添加文档
    # ================================================================

    def add_file(self, filepath: str, source_label: str = None) -> int:
        """解析文件 → 切片 → 向量化入库，返回切片数"""
        from src.doc_parser import parse_file

        content, error = parse_file(filepath)
        if error or not content:
            return 0

        source = source_label or os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1].lower()
        return self.add_text(content, source, ext)

    def add_text(self, text: str, source: str, extension: str = "") -> int:
        """纯文本内容切片入库，返回切片数。
        extension: 文件扩展名（如 ".py"），用于选择代码切分策略；为空则用通用切分。
        """
        chunks = self._split_text(text, extension)
        if not chunks:
            return 0

        ids = [f"{source}_{uuid.uuid4().hex[:8]}" for _ in chunks]
        metadatas = [{"source": source, "chunk_index": i} for i in range(len(chunks))]

        self._collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )
        return len(chunks)

    # ================================================================
    #  检索
    # ================================================================

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """语义搜索，返回 [{content, source, chunk_index}]"""
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(n_results, self._collection.count()),
        )

        chunks = []
        for i in range(len(results["documents"][0])):
            meta = results["metadatas"][0][i]
            chunks.append({
                "content": results["documents"][0][i],
                "source": meta.get("source", "未知"),
                "chunk_index": meta.get("chunk_index", 0),
            })
        return chunks

    # ================================================================
    #  管理
    # ================================================================

    @property
    def count(self) -> int:
        """知识库中的切片总数"""
        return self._collection.count()

    def list_sources(self) -> list[dict]:
        """列出所有已索引的文档来源及其片段数"""
        if self._collection.count() == 0:
            return []

        all_data = self._collection.get()
        source_counts: dict[str, int] = {}
        for meta in all_data["metadatas"]:
            src = meta.get("source", "未知")
            source_counts[src] = source_counts.get(src, 0) + 1

        return [
            {"source": src, "chunks": count}
            for src, count in sorted(source_counts.items())
        ]

    def remove_source(self, source: str):
        """按来源删除所有切片"""
        self._collection.delete(where={"source": source})

    def clear(self):
        """清空整个知识库"""
        self._client.delete_collection("documents")
        self._collection = self._client.get_or_create_collection(
            name="documents",
        )

    # ================================================================
    #  内部切分（LangChain）
    # ================================================================

    def _get_splitter(self, extension: str) -> RecursiveCharacterTextSplitter:
        """根据文件扩展名返回合适的切分器。

        - 代码文件 → 按函数/类边界切，不拦腰截断
        - Markdown  → 按标题/段落层级切
        - 普通文本  → 按段落→句子→字符逐级切
        """
        lang = _EXTENSION_TO_LANGUAGE.get(extension)

        if lang is not None:
            # 代码/标记语言：按语法结构切分
            return RecursiveCharacterTextSplitter.from_language(
                language=lang,
                chunk_size=500,
                chunk_overlap=50,
            )

        # 通用文本：中文友好的分隔符层级
        return RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=[
                "\n\n",    # 段落
                "\n",      # 行
                "。",      # 中文句号
                ". ",      # 英文句号
                "！",      # 中文感叹号
                "？",      # 中文问号
                "；",      # 中文分号
                "; ",      # 英文分号
                "，",      # 中文逗号
                ", ",      # 英文逗号
                " ",       # 空格
                "",        # 字符
            ],
            length_function=len,
            is_separator_regex=False,
        )

    def _split_text(self, text: str, extension: str = "") -> list[str]:
        """切分文本为 chunks，每块 ≤ 500 字符"""
        splitter = self._get_splitter(extension)
        chunks = splitter.split_text(text)

        # LangChain 的分隔符已在类初始化时烧入，这里只关心结果
        # 过滤掉空白块
        return [c.strip() for c in chunks if c.strip()]
