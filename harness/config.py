import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

VLLM_BASE_URL = os.environ.get(
    "VLLM_BASE_URL", "https://imaging-chatter-stowaway.ngrok-free.dev"
)
VLLM_MODEL = os.environ.get("VLLM_MODEL", "cyankiwi/Qwen3.5-4B-AWQ-4bit")

MAX_ITERATIONS = 10
MAX_FILE_SIZE = 100_000  # bytes
