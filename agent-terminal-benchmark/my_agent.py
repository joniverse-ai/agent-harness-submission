"""Custom agent using vLLM (Qwen3.5-4B) with text-based tool parsing."""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict
from pathlib import Path

import httpx

from harness_lab.agent import (
    Agent, Limits, ModelReply, SessionStore, ToolRequest, ToolSpec,
)
from harness_lab.local_agent import LocalBenchmarkTools, SYSTEM


VLLM_BASE_URL = os.environ.get(
    "VLLM_BASE_URL", "https://imaging-chatter-stowaway.ngrok-free.dev"
)
VLLM_MODEL = os.environ.get("VLLM_MODEL", "cyankiwi/Qwen3.5-4B-AWQ-4bit")

TOOL_PROMPT_TEMPLATE = """You have access to the following tools:

{tool_descriptions}

When you need to use a tool, write EXACTLY this format (one tool per block):

[USE_TOOL]
{{"name": "tool_name", "arguments": {{"param": "value"}}}}
[/USE_TOOL]

CRITICAL RULES:
- You MUST use write_file to create ALL requested output files in the workspace.
- Showing code or results in your text answer is NOT enough. The verifier checks actual files.
- Read the task instructions carefully to find what output files are required.
- Use run_python to write helper scripts and execute them when the task requires computation.
- To solve coding tasks: write the solution code with write_file, then run it with run_python.
- Work step by step: 1) Read instructions 2) Read input files 3) Write solution/output files 4) Verify with run_python if needed.
- Use one tool at a time.
- When done, state what files you created as your final answer."""


def _build_tool_descriptions(tools: list[ToolSpec]) -> str:
    lines = []
    for t in tools:
        params = json.dumps(t.parameters, ensure_ascii=False)
        lines.append(f"- {t.name}: {t.description}\n  Parameters: {params}")
    return "\n".join(lines)


class VLLMTextProvider:
    """vLLM provider that uses text-based tool parsing instead of native function calling."""

    def __init__(self, base_url: str, model: str, max_output_tokens: int = 4096):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.client = httpx.AsyncClient(timeout=300)

    async def complete(self, messages: list[dict], tools: list[ToolSpec]) -> ModelReply:
        tool_descriptions = _build_tool_descriptions(tools)
        tool_instruction = TOOL_PROMPT_TEMPLATE.format(tool_descriptions=tool_descriptions)

        api_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")

            if role == "system":
                api_messages.append({
                    "role": "system",
                    "content": content + "\n\n" + tool_instruction,
                })
            elif role == "tool":
                api_messages.append({
                    "role": "user",
                    "content": f"[TOOL_RESULT] {msg.get('name', '')}:\n{content}",
                })
            elif role == "assistant":
                api_messages.append({"role": "assistant", "content": content})
            else:
                api_messages.append({"role": role, "content": content})

        resp = await self.client.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model,
                "messages": api_messages,
                "max_tokens": self.max_output_tokens,
                "temperature": 0.3,
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        resp.raise_for_status()
        data = resp.json()

        msg_data = data["choices"][0]["message"]
        text = msg_data.get("content") or ""

        usage_data = data.get("usage", {})
        usage = {}
        if usage_data.get("prompt_tokens"):
            usage["input_tokens"] = usage_data["prompt_tokens"]
        if usage_data.get("completion_tokens"):
            usage["output_tokens"] = usage_data["completion_tokens"]

        tool_requests = []
        pattern = r"\[USE_TOOL\]\s*(\{.*?\})\s*\[/USE_TOOL\]"
        for match in re.finditer(pattern, text, re.DOTALL):
            try:
                call = json.loads(match.group(1))
                if "name" in call and "arguments" in call:
                    tool_requests.append(
                        ToolRequest(
                            id="vllm-" + uuid.uuid4().hex[:8],
                            name=call["name"],
                            arguments=call["arguments"],
                        )
                    )
            except json.JSONDecodeError:
                continue

        clean_text = re.sub(pattern, "", text, flags=re.DOTALL).strip()

        return ModelReply(clean_text, tool_requests, usage, [])

    async def close(self):
        await self.client.aclose()


async def solve_task(
    instruction: str, workspace: Path, logs_dir: Path, options: dict
) -> dict:
    logs_dir.mkdir(parents=True, exist_ok=True)

    provider = VLLMTextProvider(
        VLLM_BASE_URL, VLLM_MODEL,
        max_output_tokens=options.get("max_output_tokens", 4096),
    )

    def trace(event):
        with (logs_dir / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    limits = Limits(
        max_steps=options["max_steps"],
        max_tool_calls=options["max_steps"] * 4,
        total_timeout_seconds=options["max_seconds"],
        tool_timeout_seconds=options.get("command_timeout", 10) + 2,
    )

    try:
        session = SessionStore(logs_dir / "sessions", "trial")
        settings = {
            "provider": "vllm",
            "model": VLLM_MODEL,
            "max_output_tokens": options.get("max_output_tokens", 4096),
            "workspace": str(workspace.resolve()),
            "task_cwd": options.get("task_cwd", "."),
        }
        result = await Agent(
            provider,
            LocalBenchmarkTools(workspace, options.get("command_timeout", 10)),
            limits, trace, SYSTEM,
        ).run(
            instruction + "\n\nLocal task working directory (relative to workspace): " + settings["task_cwd"],
            session=session, settings=settings,
        )
        return {
            "status": result.status,
            "answer": result.answer,
            "metrics": asdict(result.metrics),
        }
    finally:
        await provider.close()
