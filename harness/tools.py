import os
import subprocess
from config import WORKSPACE_DIR, MAX_FILE_SIZE

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "워크스페이스 내 파일의 내용을 읽습니다.",
        "parameters": {"path": "읽을 파일의 상대 경로 (workspace/ 기준)"},
    },
    {
        "name": "list_files",
        "description": "워크스페이스 내 파일 목록을 반환합니다.",
        "parameters": {"path": "목록을 볼 디렉토리의 상대 경로 (선택, 기본값: workspace 루트)"},
    },
    {
        "name": "write_file",
        "description": "워크스페이스 내 파일에 내용을 씁니다. 사용자 승인이 필요합니다.",
        "parameters": {
            "path": "쓸 파일의 상대 경로 (workspace/ 기준)",
            "content": "파일에 쓸 내용",
        },
    },
    {
        "name": "run_test",
        "description": "워크스페이스 내 Python 테스트 파일을 실행합니다. 사용자 승인이 필요합니다.",
        "parameters": {"path": "실행할 테스트 파일의 상대 경로 (workspace/ 기준)"},
    },
]

TOOLS_NEEDING_APPROVAL = {"write_file", "run_test"}


def _resolve_path(relative_path: str) -> str:
    full = os.path.normpath(os.path.join(WORKSPACE_DIR, relative_path))
    if not full.startswith(WORKSPACE_DIR):
        raise PermissionError(f"경로 이탈: {relative_path}")
    return full


def read_file(path: str) -> dict:
    full = _resolve_path(path)
    if not os.path.isfile(full):
        return {"error": f"파일 없음: {path}"}
    if os.path.getsize(full) > MAX_FILE_SIZE:
        return {"error": f"파일 크기 초과: {path}"}
    with open(full, "r", encoding="utf-8") as f:
        return {"content": f.read(), "path": path}


def list_files(path: str = "") -> dict:
    full = _resolve_path(path) if path else WORKSPACE_DIR
    if not os.path.isdir(full):
        return {"error": f"디렉토리 없음: {path}"}
    entries = []
    for name in sorted(os.listdir(full)):
        fp = os.path.join(full, name)
        entries.append({
            "name": name,
            "type": "dir" if os.path.isdir(fp) else "file",
            "size": os.path.getsize(fp) if os.path.isfile(fp) else None,
        })
    return {"files": entries, "path": path or "."}


def write_file(path: str, content: str) -> dict:
    full = _resolve_path(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return {"success": True, "path": path, "size": len(content)}


def run_test(path: str) -> dict:
    full = _resolve_path(path)
    if not os.path.isfile(full):
        return {"error": f"파일 없음: {path}"}
    if not full.endswith(".py"):
        return {"error": "Python 파일만 실행 가능"}
    try:
        result = subprocess.run(
            ["python3", full],
            capture_output=True, text=True, timeout=30,
            cwd=WORKSPACE_DIR,
        )
        return {
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "실행 시간 초과 (30초)"}


TOOL_REGISTRY = {
    "read_file": read_file,
    "list_files": list_files,
    "write_file": write_file,
    "run_test": run_test,
}


def execute_tool(name: str, arguments: dict) -> dict:
    func = TOOL_REGISTRY.get(name)
    if not func:
        return {"error": f"알 수 없는 도구: {name}"}
    try:
        return func(**arguments)
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
