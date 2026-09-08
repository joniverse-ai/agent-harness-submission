# 인터페이스 계약
상태: 구현 완료. Flask 웹 앱 기반 로컬 하네스.

## 제품의 작업 계약
| 동작 | 입력 | 출력 | 오류·경계 |
|---|---|---|---|
| 작업 시작 | POST /api/chat {session_id, message} | {steps: [...], done: bool} | 빈 메시지 → 에러, 없는 세션 → 자동 생성 |
| 세션 생성 | POST /api/sessions {} | {session_id, created_at} | — |
| 세션 목록 | GET /api/sessions | [{id, created_at, message_count}] | 빈 목록 가능 |
| 세션 조회 | GET /api/sessions/<id> | {messages: [...]} | 없는 세션 → 404 |
| 변경 승인 | POST /api/approve {session_id, approval_id, approved: bool} | {result: tool_result} | 만료/없는 approval_id → 에러 |

### 작업 상태 전이
queued → running → (waiting_approval ↔ running)* → completed/failed

거절 시: 도구 실행 중단, "사용자가 거절했습니다" 메시지를 모델에 전달, 모델이 다음 행동 결정. 파일 불변 보장.

### 구체적 계약: POST /api/chat
- 입력: `{session_id: string, message: string}`
- 정상 입력 예: `{"session_id": "abc123", "message": "sample.py 파일을 읽어서 요약해줘"}`
- 정상 출력 예:
```json
{
  "steps": [
    {"type": "assistant", "content": "파일을 읽어보겠습니다."},
    {"type": "tool_call", "name": "read_file", "arguments": {"path": "sample.py"}},
    {"type": "tool_result", "content": {"content": "def greet()...", "path": "sample.py"}},
    {"type": "assistant", "content": "이 파일에는 greet(), add() 등의 함수가 있습니다."}
  ],
  "done": true
}
```
- 오류 입력: `{"session_id": "", "message": ""}` → `{"error": "메시지가 비어있습니다"}`
- 승인 필요 시:
```json
{
  "steps": [...],
  "approval_needed": {"id": "appr_xyz", "tool": "write_file", "arguments": {...}},
  "done": false
}
```

## UI와 통신 매핑
- 선택한 방식: Flask 로컬 웹 (port 5001), 단일 페이지 앱
- HTTP 경로 매핑:
  - `GET /` → 메인 채팅 UI (index.html)
  - `GET /api/sessions` → 세션 목록 조회
  - `POST /api/sessions` → 새 세션 생성
  - `GET /api/sessions/<id>` → 세션 대화 기록
  - `POST /api/chat` → 작업 실행 (에이전트 루프)
  - `POST /api/approve` → 도구 승인/거절
- 진행 표시: 각 단계(도구 호출, 결과, 모델 응답)를 steps 배열로 반환, UI에서 순차 렌더링

## 모델 제공자 연결부
- 첫 제공자/모델: vLLM (cyankiwi/Qwen3.5-4B-AWQ-4bit), ngrok 경유
- 사용 API: OpenAI 호환 `/v1/chat/completions`
- 도구 호출 방식: 네이티브 function calling 대신 텍스트 파싱 (`[USE_TOOL]`/`[/USE_TOOL]` 커스텀 태그)
  - 이유: Qwen3.5의 `<tool_call>` 태그가 chat template에서 가로채여 null content 반환 문제 발생
- 추가 설정: `chat_template_kwargs: {"enable_thinking": false}` (Qwen3.5 thinking 모드 비활성화)
- 한 번에 도구 1개씩 처리
- 파싱 실패: 도구 호출 무시하고 텍스트만 전달
- 네트워크 오류: `[오류]` 접두사 메시지로 표시
- 제한: max_tokens=4096, temperature=0.3, timeout=120s

## 실행 도구 계약
| 도구 | 인자/반환 예 | 허용 범위 | 승인·오류 |
|---|---|---|---|
| read_file | `{path: "sample.py"}` → `{content: "...", path: "sample.py"}` | workspace/ 내 파일 | 자동 허용. 경로 이탈 → PermissionError, 없는 파일 → error, 크기 초과(100KB) → error |
| list_files | `{path: ""}` → `{files: [{name, type, size}], path: "."}` | workspace/ 내 디렉토리 | 자동 허용. 없는 디렉토리 → error |
| write_file | `{path: "fix.py", content: "..."}` → `{success: true, path, size}` | workspace/ 내 파일 | **승인 필요**. 경로 이탈 → PermissionError. 거절 시 파일 불변 |
| run_test | `{path: "test_buggy.py"}` → `{stdout, stderr, returncode}` | workspace/ 내 .py 파일 | **승인 필요**. 30초 타임아웃. python3로 실행 |

경로 검사: `_resolve_path()`가 `os.path.normpath` + `startswith(WORKSPACE_DIR)`로 경로 이탈 방지. 모델 지시와 무관하게 적용.
