"""極簡多輪對話記憶 —— 樹德投資助理。

每位使用者在「記憶體」中保留最近 N 輪對話(一問一答),讓主管可以自然追問
(例如先問「台積電怎麼看?」再問「那風險呢?」bot 記得前文)。

刻意不接資料庫:符合「記住當次連續對話」的需求,程序重啟即清空,零維運。
若日後想長期永久記憶,再把這層換成外接儲存即可(介面不變)。
"""
from collections import deque
from threading import Lock

from config import Config

_store: dict[str, deque] = {}
_lock = Lock()


def _dq(user_id: str) -> deque:
    d = _store.get(user_id)
    if d is None:
        # 一輪 = user + assistant 兩則,故長度 ×2
        d = deque(maxlen=max(1, Config.MEMORY_TURNS) * 2)
        _store[user_id] = d
    return d


def history(user_id: str) -> list[dict]:
    """回傳給 Claude 的 messages 歷史(不含這次的新問題)。"""
    with _lock:
        return list(_dq(user_id))


def add_user(user_id: str, text: str) -> None:
    with _lock:
        _dq(user_id).append({"role": "user", "content": text})


def add_assistant(user_id: str, text: str) -> None:
    if not text:
        return
    with _lock:
        _dq(user_id).append({"role": "assistant", "content": text})


def clear(user_id: str) -> None:
    with _lock:
        _store.pop(user_id, None)


def has_history(user_id: str) -> bool:
    with _lock:
        return bool(_store.get(user_id))
