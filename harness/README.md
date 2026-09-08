# 개인 에이전트 하네스

vLLM (Qwen3.5-4B) 기반의 AI 에이전트 하네스. 자연어 요청 → 모델이 도구 선택 → 하네스가 검사·실행 → 결과 반환.

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# vLLM 서버 주소 설정 (환경변수 또는 config.py 수정)
export VLLM_BASE_URL="https://your-ngrok-url.ngrok-free.dev"
export VLLM_MODEL="cyankiwi/Qwen3.5-4B-AWQ-4bit"

# 서버 시작
python3 app.py
# → http://localhost:5001
```

## 구조

```
harness/
├── app.py           # Flask 웹 앱, 에이전트 루프
├── config.py        # 설정 (vLLM URL, 모델, 제한값)
├── provider.py      # vLLM API 호출, 텍스트 파싱
├── tools.py         # 도구 정의·실행, 경로 검사
├── session.py       # JSON 세션 저장/로드
├── requirements.txt # 의존성
├── templates/
│   └── index.html   # 채팅 UI
├── workspace/       # 에이전트 작업 폴더
│   ├── sample.py
│   ├── buggy.py
│   └── test_buggy.py
└── sessions/        # 세션 저장 (JSON)
```

## 도구

| 도구 | 설명 | 승인 필요 |
|---|---|---|
| read_file | workspace 내 파일 읽기 | 아니오 |
| list_files | workspace 내 파일 목록 | 아니오 |
| write_file | workspace 내 파일 쓰기 | 예 |
| run_test | Python 테스트 실행 | 예 |

## 설계 결정

- 도구 호출 방식: 텍스트 파싱 (`[USE_TOOL]`/`[/USE_TOOL]` 태그)
  - Qwen3.5의 `<tool_call>` 태그가 chat template에서 충돌하여 커스텀 태그 사용
- thinking 모드 비활성화: `chat_template_kwargs: {"enable_thinking": false}`
- 경로 보안: `os.path.normpath` + `startswith(WORKSPACE_DIR)`로 workspace 외부 접근 차단
- 세션 저장: JSON 파일 기반, 서버 재시작 시에도 대화 기록 유지

## 벤치마크

Terminal-Bench Pro 로컬 이식판 10문항 평가는 `agent-terminal-benchmark/` 디렉토리에서 실행.

```bash
cd agent-terminal-benchmark
VLLM_BASE_URL="..." VLLM_MODEL="..." OPENAI_API_KEY="dummy" \
  uv run python -m harness_lab.bench \
    --name baseline \
    --agent my_agent:solve_task \
    --provider openai \
    --model "cyankiwi/Qwen3.5-4B-AWQ-4bit" \
    --max-steps 20 --max-seconds 300
```
