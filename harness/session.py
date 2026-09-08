from typing import Optional
import json
import os
import uuid
from datetime import datetime
from config import SESSIONS_DIR


def new_session_id() -> str:
    return uuid.uuid4().hex[:8]


def _session_path(session_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{session_id}.json")


def save_session(session_id: str, conversation: list, metadata: dict = None):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    data = {
        "session_id": session_id,
        "updated_at": datetime.now().isoformat(),
        "metadata": metadata or {},
        "conversation": conversation,
    }
    with open(_session_path(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_session(session_id: str) -> Optional[dict]:
    path = _session_path(session_id)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_sessions() -> list:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    sessions = []
    for name in sorted(os.listdir(SESSIONS_DIR), reverse=True):
        if name.endswith(".json"):
            path = os.path.join(SESSIONS_DIR, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                first_msg = ""
                for msg in data.get("conversation", []):
                    if msg["role"] == "user":
                        first_msg = msg["content"][:50]
                        break
                sessions.append({
                    "session_id": data["session_id"],
                    "updated_at": data.get("updated_at", ""),
                    "preview": first_msg,
                })
            except Exception:
                continue
    return sessions
