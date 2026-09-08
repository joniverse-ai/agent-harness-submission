import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify
from config import MAX_ITERATIONS
from provider import call_model, parse_tool_call, extract_text_before_tool
from tools import execute_tool, TOOLS_NEEDING_APPROVAL
from session import new_session_id, save_session, load_session, list_sessions

app = Flask(__name__)

active_sessions = {}  # type: dict
pending_approvals = {}  # type: dict


def get_conversation(session_id: str) -> list:
    if session_id not in active_sessions:
        saved = load_session(session_id)
        if saved:
            active_sessions[session_id] = saved["conversation"]
        else:
            active_sessions[session_id] = []
    return active_sessions[session_id]


def run_agent_loop(session_id: str) -> list:
    conversation = get_conversation(session_id)
    steps = []

    for i in range(MAX_ITERATIONS):
        response_text = call_model(conversation)

        if response_text.startswith("[오류]"):
            steps.append({"type": "error", "content": response_text})
            break

        tool_call = parse_tool_call(response_text)

        if not tool_call:
            conversation.append({"role": "assistant", "content": response_text})
            steps.append({"type": "answer", "content": response_text})
            save_session(session_id, conversation)
            break

        text_before = extract_text_before_tool(response_text)
        if text_before:
            steps.append({"type": "thinking", "content": text_before})

        tool_name = tool_call["name"]
        tool_args = tool_call["arguments"]

        if tool_name in TOOLS_NEEDING_APPROVAL:
            approval_id = f"{session_id}_{i}"
            pending_approvals[approval_id] = {
                "session_id": session_id,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "iteration": i,
                "response_text": response_text,
            }
            steps.append({
                "type": "approval_needed",
                "approval_id": approval_id,
                "tool_name": tool_name,
                "tool_args": tool_args,
            })
            conversation.append({"role": "assistant", "content": response_text})
            save_session(session_id, conversation)
            break

        steps.append({"type": "tool_call", "name": tool_name, "args": tool_args})
        result = execute_tool(tool_name, tool_args)
        steps.append({"type": "tool_result", "name": tool_name, "result": result})

        conversation.append({"role": "assistant", "content": response_text})
        conversation.append({
            "role": "user",
            "content": f"[도구 실행 결과] {tool_name}:\n{_format_result(result)}",
        })
        save_session(session_id, conversation)

    else:
        steps.append({"type": "error", "content": f"반복 한도 도달 ({MAX_ITERATIONS}회)"})

    return steps


def _format_result(result: dict) -> str:
    if "error" in result:
        return f"오류: {result['error']}"
    if "content" in result:
        content = result["content"]
        if len(content) > 3000:
            return content[:3000] + "\n... (잘림)"
        return content
    import json
    return json.dumps(result, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sessions", methods=["GET"])
def api_sessions():
    return jsonify(list_sessions())


@app.route("/api/sessions", methods=["POST"])
def api_new_session():
    sid = new_session_id()
    active_sessions[sid] = []
    save_session(sid, [])
    return jsonify({"session_id": sid})


@app.route("/api/sessions/<session_id>", methods=["GET"])
def api_get_session(session_id):
    conversation = get_conversation(session_id)
    return jsonify({"session_id": session_id, "conversation": conversation})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    session_id = data.get("session_id")
    message = data.get("message", "").strip()

    if not session_id or not message:
        return jsonify({"error": "session_id와 message 필요"}), 400

    conversation = get_conversation(session_id)
    conversation.append({"role": "user", "content": message})
    save_session(session_id, conversation)

    steps = run_agent_loop(session_id)
    return jsonify({"session_id": session_id, "steps": steps})


@app.route("/api/approve", methods=["POST"])
def api_approve():
    data = request.json
    approval_id = data.get("approval_id")
    approved = data.get("approved", False)

    if approval_id not in pending_approvals:
        return jsonify({"error": "승인 요청 없음 또는 만료"}), 404

    info = pending_approvals.pop(approval_id)
    session_id = info["session_id"]
    conversation = get_conversation(session_id)

    if not approved:
        conversation.append({
            "role": "user",
            "content": f"[사용자 거절] {info['tool_name']} 실행이 거절되었습니다.",
        })
        save_session(session_id, conversation)
        return jsonify({"steps": [{"type": "rejected", "tool_name": info["tool_name"]}]})

    result = execute_tool(info["tool_name"], info["tool_args"])
    conversation.append({
        "role": "user",
        "content": f"[도구 실행 결과] {info['tool_name']}:\n{_format_result(result)}",
    })
    save_session(session_id, conversation)

    steps = [
        {"type": "tool_result", "name": info["tool_name"], "result": result},
    ]
    continued = run_agent_loop(session_id)
    steps.extend(continued)
    return jsonify({"steps": steps})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
