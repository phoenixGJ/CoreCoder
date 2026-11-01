"""Session persistence - save and resume conversations.

Claude Code maintains session state via QueryEngine (1295 lines).
CoreCoder distills this to: JSON dump of messages + model config.
"""

import json
import re
import time
import uuid
from pathlib import Path

SESSIONS_DIR = Path(r"E:\github_project\CoreCoder") / ".corecoder" / "sessions"
_SAFE_SESSION_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_SESSION_ID_LEN = 100  # keep filenames comfortably under the OS limit


def _normalize_session_id(session_id: str | None) -> str:
    if not session_id:
        return _new_session_id()

    name = session_id.strip().replace("\\", "/").split("/")[-1]
    name = _SAFE_SESSION_RE.sub("-", name).strip(".-_")
    if len(name) > _MAX_SESSION_ID_LEN:
        name = name[:_MAX_SESSION_ID_LEN].strip(".-_")
    return name or _new_session_id()


def _new_session_id() -> str:
    return f"session_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _session_path(session_id: str) -> Path:
    path = (SESSIONS_DIR / f"{_normalize_session_id(session_id)}.json").resolve()
    root = SESSIONS_DIR.resolve()
    if root != path.parent:
        raise ValueError("Invalid session id")
    return path
# 新增代码（start）
def _jsonl_path(session_id: str) -> Path:
    path = (SESSIONS_DIR / f"{_normalize_session_id(session_id)}.jsonl").resolve()

    if path.parent != SESSIONS_DIR.resolve():
        raise ValueError("Invalid session id")

    return path


def _trim_incomplete_tail(path: Path) -> None:
    """删除异常中断时可能留下的不完整末行。"""
    if not path.exists():
        return

    with path.open("rb+") as f:
        f.seek(0, 2)
        size = f.tell()

        if size == 0:
            return

        f.seek(size - 1)
        if f.read(1) == b"\n":
            return

        pos = size

        while pos:
            n = min(4096, pos)
            pos -= n

            f.seek(pos)
            chunk = f.read(n)
            i = chunk.rfind(b"\n")

            if i != -1:
                f.truncate(pos + i + 1)
                return

        f.truncate(0)


class JsonlSessionWriter:
    """每次只向 JSONL 文件追加新增消息。"""

    def __init__(
        self,
        session_id=None,
        messages=None,
        model=None,
        revision=0,
    ):
        self.session_id = _normalize_session_id(session_id)
        self.path = _jsonl_path(self.session_id)

        _trim_incomplete_tail(self.path)

        exists = self.path.exists() and self.path.stat().st_size > 0

        # 已经保存到第几条消息
        self.saved_count = len(messages or []) if exists else 0
        self.saved_model = model if exists else None

        # 记录上下文压缩版本
        self.saved_revision = revision

    def save(
        self,
        messages: list[dict],
        model: str,
        revision: int = 0,
        force: bool = False,
    ) -> bool:

        _trim_incomplete_tail(self.path)

        exists = self.path.exists() and self.path.stat().st_size > 0

        # 空的新会话不自动保存
        if not exists and not messages and not force:
            return False

        # 没有新消息，也没有状态变化
        if (
            exists
            and not force
            and revision == self.saved_revision
            and len(messages) == self.saved_count
            and model == self.saved_model
        ):
            return False

        # 压缩后旧消息可能被修改，因此需要快照
        snapshot = (
            not exists
            or revision != self.saved_revision
            or len(messages) < self.saved_count
        )

        record = {
            "type": "snapshot" if snapshot else "append",
            "model": model,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "messages": (messages if snapshot else messages[self.saved_count :]),
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)

        # a 表示追加，而不是覆盖
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

        # 写入成功后再更新进度
        self.saved_count = len(messages)
        self.saved_model = model
        self.saved_revision = revision

        return True
# end

def save_session(
    messages: list[dict], model: str, session_id: str | None = None
) -> str:
    """Save conversation to disk. Returns the session ID."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    session_id = _normalize_session_id(session_id)

    data = {
        "id": session_id,
        "model": model,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "messages": messages,
    }

    path = _session_path(session_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return session_id

# 对load_session()函数进行了修改，优先读取 JSONL 文件，如果不存在则兼容旧的 JSON 文件。
def load_session(session_id: str) -> tuple[list[dict], str] | None:
    """优先读取 JSONL，兼容旧 JSON 会话。"""

    path = _jsonl_path(session_id)

    if path.exists():
        try:
            messages = []
            model = None

            with path.open("rb") as f:
                for line in f:
                    # 忽略崩溃留下的不完整末行
                    if not line.endswith(b"\n"):
                        break

                    record = json.loads(line)

                    if record["type"] == "snapshot":
                        messages = record["messages"]

                    elif record["type"] == "append":
                        """
                        append(x)：把 x 整体作为一个元素加入。
                        extend(x)：把 x 里的元素逐个加入。
                        """
                        messages.extend(record["messages"])

                    else:
                        return None

                    model = record["model"]

            if model is not None:
                return messages, model

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
        ):
            return None

    # 没有 JSONL 时，兼容原来的 JSON 文件
    legacy_path = _session_path(session_id)

    if not legacy_path.exists():
        return None

    try:
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
        return data["messages"], data["model"]

    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
    ):
        return None

# 修改了 list_sessions() 函数，优先列出 JSONL 会话，如果没有则兼容旧的 JSON 会话。
def list_sessions() -> list[dict]:
    """列出 JSONL 和旧 JSON 会话。"""
    if not SESSIONS_DIR.exists():
        return []

    paths = sorted(
        [
            *SESSIONS_DIR.glob("*.jsonl"),
            *SESSIONS_DIR.glob("*.json"),
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    sessions = []
    seen = set()

    for path in paths:
        if path.stem in seen:
            continue

        loaded = load_session(path.stem)

        if loaded is None:
            continue

        messages, model = loaded

        preview = next(
            (
                msg.get("content", "")[:80]
                for msg in messages
                if msg.get("role") == "user" and isinstance(msg.get("content"), str)
            ),
            "",
        )

        sessions.append(
            {
                "id": path.stem,
                "model": model,
                "saved_at": time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(path.stat().st_mtime),
                ),
                "preview": preview,
            }
        )

        seen.add(path.stem)

        if len(sessions) >= 20:
            break

    return sessions
