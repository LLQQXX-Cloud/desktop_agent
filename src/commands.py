"""命令处理模块 —— 斜杠命令 + 知识库索引"""
import os as _os

from src.memory import Memory
from src.knowledge_base import KnowledgeBase


def handle_command(cmd: str, memory: Memory, kb: KnowledgeBase = None) -> str:
    """处理斜杠命令，返回回复文本"""
    cmd = cmd.strip()

    if cmd == "/help":
        return _help()

    elif cmd == "/history":
        return _cmd_history(memory)

    elif cmd == "/clear":
        memory.clear_history()
        return "✅ 对话记录已清空。"

    elif cmd.startswith("/remember"):
        return _cmd_remember(memory, cmd)

    elif cmd.startswith("/forget"):
        k = cmd[len("/forget"):].strip()
        if k:
            memory.forget(k)
            return f"✅ 已忘记：{k}"
        return "格式: /forget 键"

    elif cmd.startswith("/recall"):
        k = cmd[len("/recall"):].strip()
        v = memory.recall(k)
        return f"{k} = {v}" if v else f"未找到「{k}」的记忆。"

    elif cmd == "/memories":
        all_m = memory.all_memories()
        if not all_m:
            return "暂无记忆。"
        lines = ["🧠 我的记忆："]
        for k, v in all_m.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    # ---- 知识库命令 ----
    elif cmd == "/kb list":
        return _cmd_kb_list(kb)

    elif cmd == "/kb clear":
        if not kb:
            return "知识库未初始化。"
        kb.clear()
        return "✅ 知识库已清空。"

    elif cmd.startswith("/kb add"):
        return _cmd_kb_add(kb, cmd)

    elif cmd.startswith("/kb search"):
        return _cmd_kb_search(kb, cmd)

    elif cmd.startswith("/kb remove"):
        return _cmd_kb_remove(kb, cmd)

    else:
        return f"未知命令: {cmd}\n输入 /help 查看可用命令"


# ================================================================
#  命令实现
# ================================================================

def _help() -> str:
    return (
        "可用命令：\n"
        "/help           — 显示帮助\n"
        "/history        — 显示最近对话\n"
        "/clear          — 清空对话记录\n"
        "/remember K=V  — 记住信息\n"
        "/forget K       — 忘记信息\n"
        "/recall K       — 回忆信息\n"
        "/memories       — 列出所有记忆\n"
        "/kb add <路径>  — 添加文档/文件夹到知识库\n"
        "/kb list        — 列出知识库文档\n"
        "/kb search <Q>  — 搜索知识库\n"
        "/kb remove <名> — 移除文档\n"
        "/kb clear       — 清空知识库"
    )


def _cmd_history(memory: Memory) -> str:
    h = memory.get_history(limit=10)
    if not h:
        return "暂无对话记录。"
    lines = ["📝 最近对话："]
    for m in h:
        role = "你" if m["role"] == "user" else "助手"
        lines.append(f"  {role}: {m['content'][:40]}")
    return "\n".join(lines)


def _cmd_remember(memory: Memory, cmd: str) -> str:
    parts = cmd[len("/remember"):].strip().split("=", 1)
    if len(parts) == 2:
        k, v = parts[0].strip(), parts[1].strip()
        memory.remember(k, v)
        return f"✅ 已记住：{k} = {v}"
    return "格式: /remember 键=值"


# ================================================================
#  知识库命令
# ================================================================

def _cmd_kb_list(kb: KnowledgeBase) -> str:
    if not kb:
        return "知识库未初始化。"
    sources = kb.list_sources()
    if not sources:
        return "📚 知识库为空。\n使用 /kb add <文件路径> 添加文档。"
    lines = ["📚 知识库文档："]
    for s in sources:
        lines.append(f"  📄 {s['source']}（{s['chunks']} 个片段）")
    return "\n".join(lines)


def _cmd_kb_add(kb: KnowledgeBase, cmd: str) -> str:
    if not kb:
        return "知识库未初始化。"
    path = cmd[len("/kb add"):].strip()
    if not path:
        return "用法: /kb add <文件或文件夹路径>"
    return _add_path(kb, path)


def _cmd_kb_search(kb: KnowledgeBase, cmd: str) -> str:
    if not kb:
        return "知识库未初始化。"
    query = cmd[len("/kb search"):].strip()
    if not query:
        return "用法: /kb search <查询内容>"
    chunks = kb.search(query, n_results=3)
    if not chunks:
        return "未找到相关内容。"
    lines = [f"🔍 搜索「{query}」的结果："]
    for i, c in enumerate(chunks, 1):
        lines.append(f"\n--- {i}. {c['source']} ---")
        lines.append(c["content"][:200])
    return "\n".join(lines)


def _cmd_kb_remove(kb: KnowledgeBase, cmd: str) -> str:
    if not kb:
        return "知识库未初始化。"
    source = cmd[len("/kb remove"):].strip()
    if not source:
        return "用法: /kb remove <文件名>"
    kb.remove_source(source)
    return f"✅ 已从知识库移除「{source}」。"


# ================================================================
#  文件索引辅助
# ================================================================

_SUPPORTED_EXTENSIONS = {
    '.txt', '.py', '.json', '.xml', '.csv', '.md', '.yaml', '.yml',
    '.ini', '.cfg', '.toml', '.log', '.html', '.css', '.js', '.ts',
    '.java', '.c', '.cpp', '.h', '.rs', '.go', '.sh', '.bat', '.ps1',
    '.sql', '.r', '.rb', '.php', '.swift', '.kt', '.scala', '.lua',
    '.docx', '.pdf', '.xlsx', '.xls',
}


def _add_path(kb: KnowledgeBase, path: str) -> str:
    """添加文件或文件夹到知识库"""
    if not _os.path.exists(path):
        return f"路径不存在: {path}"

    if _os.path.isfile(path):
        n = kb.add_file(path)
        if n:
            return f"✅ 已索引「{_os.path.basename(path)}」→ {n} 个片段"
        return f"⚠️ 无法解析「{_os.path.basename(path)}」（格式不支持或内容为空）"

    # 文件夹：遍历添加
    total_files = 0
    total_chunks = 0
    for root, _, files in _os.walk(path):
        for f in files:
            ext = _os.path.splitext(f)[1].lower()
            if ext in _SUPPORTED_EXTENSIONS:
                filepath = _os.path.join(root, f)
                n = kb.add_file(filepath)
                if n:
                    total_files += 1
                    total_chunks += n

    if total_files == 0:
        return "⚠️ 文件夹内未找到可解析的文档。"
    return f"✅ 已索引 {total_files} 个文件 → {total_chunks} 个片段"
