from typing import Optional
import json
import re
import requests
from config import VLLM_BASE_URL, VLLM_MODEL
from tools import TOOL_DEFINITIONS

SYSTEM_PROMPT = """You are a helpful AI assistant that can use tools to help users.

## Available Tools
{tool_descriptions}

## How to Use Tools
When you need to use a tool, write EXACTLY this format:

[USE_TOOL]
{{"name": "tool_name", "arguments": {{"param": "value"}}}}
[/USE_TOOL]

## Rules
- Use tools ONLY when you need to read files or list directories.
- After receiving tool results, answer the user based on the results.
- For general questions that don't need tools, answer directly.
- Use only ONE tool at a time.
- Always respond in Korean to the user.
- Do NOT output any thinking process."""


def _build_tool_descriptions() -> str:
    lines = []
    for t in TOOL_DEFINITIONS:
        params = ", ".join(f'{k}: {v}' for k, v in t["parameters"].items())
        lines.append(f'- **{t["name"]}**({params}): {t["description"]}')
    return "\n".join(lines)


def _build_messages(conversation: list) -> list:
    system = SYSTEM_PROMPT.format(tool_descriptions=_build_tool_descriptions())
    messages = [{"role": "system", "content": system}]
    for msg in conversation:
        messages.append({"role": msg["role"], "content": msg["content"]})
    return messages


def call_model(conversation: list) -> str:
    messages = _build_messages(conversation)
    try:
        resp = requests.post(
            f"{VLLM_BASE_URL}/v1/chat/completions",
            json={
                "model": VLLM_MODEL,
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.3,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        if not content and msg.get("reasoning"):
            content = msg["reasoning"]
        return content or "[오류] 모델이 빈 응답을 반환함"
    except requests.exceptions.Timeout:
        return "[오류] 모델 응답 시간 초과"
    except requests.exceptions.ConnectionError:
        return "[오류] 모델 서버 연결 실패"
    except Exception as e:
        return f"[오류] 모델 호출 실패: {e}"


def parse_tool_call(text: str) -> Optional[dict]:
    pattern = r"\[USE_TOOL\]\s*(\{.*?\})\s*\[/USE_TOOL\]"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    try:
        call = json.loads(match.group(1))
        if "name" in call and "arguments" in call:
            return call
    except json.JSONDecodeError:
        pass
    return None


def extract_text_before_tool(text: str) -> str:
    pattern = r"\[USE_TOOL\]"
    match = re.search(pattern, text)
    if match:
        return text[:match.start()].strip()
    return text.strip()
