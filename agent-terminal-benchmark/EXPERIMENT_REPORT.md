# 하네스 구현과 실험 보고서

## 제품과 구현
- 사용자 시나리오: 프로젝트 폴더의 Python 파일을 읽고 요약·수정. PRD 위치: `file/harness-design-kit/PRD.md`
- 구현 언어와 실행 방법: Python 3.9+, `cd harness && python3 app.py` → http://localhost:5001
- 직접 작성한 부분: config.py, tools.py, provider.py, session.py, app.py, templates/index.html, my_agent.py (벤치마크 어댑터)
- 참고한 부분: harness-lab의 Agent/LocalBenchmarkTools 프레임워크 (벤치마크 연결용)
- 모델·도구 반복: `app.py:run_agent_loop()` — 모델 호출 → `[USE_TOOL]` 파싱 → 승인 검사 → `execute_tool()` → 결과를 대화에 추가 → 재호출
- 오류·종료: `config.py:MAX_ITERATIONS=10`, `provider.py`의 timeout/connection 에러 처리
- 권한: `tools.py:TOOLS_NEEDING_APPROVAL`, `_resolve_path()`의 workspace 경로 제한
- 세션: `session.py`의 JSON 파일 기반 저장/로드
- Python 예시와 다른 설계 결정: Qwen3.5의 `<tool_call>` 태그 충돌 → `[USE_TOOL]`/`[/USE_TOOL]` 커스텀 태그 사용. `enable_thinking: false` 추가. 텍스트 파싱 방식 채택.

## 평가 조건
- 원본 commit: 874af409da6aafebccbf3bc5bb41a2fa4d78784d
- subset ID: terminal-bench-pro-local-port-v2
- manifest SHA256: 21f333a94929d6ce9cf0e184a8865ed5d5feca1cc33b3c6536b771ae2edb30a6
- 제공자와 모델: vLLM / cyankiwi/Qwen3.5-4B-AWQ-4bit (ngrok 경유)
- 코드 SHA256:
  - 기준: 62c60dbb45546080af82af9728a14acc7eb286d99dde49174df69e83ce918bad
  - 개선: 3517afedbcb46d4ff64a401fb74f347afcf98d1e4e5a59b88b64a5b5ee6aa327
- 실행 환경: macOS 26.6.2, ARM64 (Apple Silicon), Python 3.13.15
- 로컬 이식판 버전: 2.0.0
- 의존성: harness-lab (uv 관리), httpx, flask, requests
- 문항 수 10 / easy 2 / medium 4 / hard 4 / 문항당 반복 수 1
- 한도:
  - 기준: max_steps=20, max_seconds=300, command_timeout=10, max_output_tokens=10000
  - 개선: max_steps=30, max_seconds=300, command_timeout=10, max_output_tokens=4096
- 기준 실행 폴더: `jobs/baseline`
- 개선 실행 폴더: `jobs/improved`
- 채점 경로: harness-lab의 pytest 기반 verifier, 원본 test_outputs.py 사용

## 결과
모든 문제와 모든 시도를 포함합니다. 실패·오류·미완료를 구분합니다.

| 측정 | 통과/전체 | 쉬움(2) | 중간(4) | 어려움(4) | 실패 | 실행 오류 | 미완료 | 시간 | 입력 토큰 | 출력 토큰 | 비용 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 기준 | 0/10 | 0/2 | 0/4 | 0/4 | 7 | 3 | 0 | 1054s | 65,260 (7건) | 3,432 (7건) | 알 수 없음 |
| 개선 | 0/10 | 0/2 | 0/4 | 0/4 | 8 | 2 | 0 | 655s | 71,326 (8건) | 2,804 (8건) | 알 수 없음 |

토큰·비용: vLLM 로컬 서버이므로 API 비용 없음. 토큰 수는 API 응답의 usage 필드 기준 (error 시행은 미기록).

### 문항별 상세

| 문항 | 난이도 | 기준 상태 | 기준 시간 | 개선 상태 | 개선 시간 | 변화 |
|---|---|---|---|---|---|---|
| extract-paper-metadata-to-json | easy | fail | 15.6s | fail | 11.3s | 시간 단축, 동일 실패 |
| python-sudoku-solver-backtracking | easy | error | 70.2s | error | 78.5s | 동일 에러 |
| detect-corrupted-blockchain-transaction | medium | error | 280.2s | error | 300.2s | 동일 타임아웃 |
| implement-go-board-analyzer | medium | fail | 7.4s | fail | 27.2s | 더 많은 파일 읽기 시도 |
| python-sokoban-bfs-solver | medium | fail | 201.3s | fail | 139.6s | 시간 단축 |
| recover-encrypted-db-credentials | medium | fail | 5.9s | fail | 26.4s | 더 많은 탐색 시도 |
| advanced-json-to-rfc4180-csv-converter | hard | error | 301.0s | fail | 38.2s | error→fail 개선 |
| implement-depgraph-dependency-resolver | hard | fail | 9.0s | fail | 8.1s | 유사 |
| implement-lz77-file-compressor | hard | fail | 146.6s | fail | 12.9s | 대폭 시간 단축 |
| implement-nonogram-puzzle-solver | hard | fail | 16.9s | fail | 12.9s | 유사 |

## 실패 분석과 개선 가설

### 대표 실패: extract-paper-metadata-to-json
- 요청: 3개 논문 텍스트에서 메타데이터(제목, 저자, 년도 등)를 추출하여 JSON 파일로 저장
- 관찰한 도구 실행: list_files → read_file (paper1.txt만 읽음) → 응답 종료. write_file 미사용.
- 채점 결과: reward=0 (출력 파일 미생성)

### 추정 원인과 뒷받침 기록
1. **모델 능력 한계 (주요 원인)**: Qwen3.5-4B는 4B 파라미터의 소형 모델로, 복잡한 multi-step 추론과 코드 생성 능력이 제한적. 대부분의 태스크에서 파일을 1~2개 읽은 후 텍스트 응답만 생성하고 write_file을 호출하지 않음.
2. **프롬프트 준수 미흡**: CRITICAL RULES에서 write_file 사용을 강조했지만, 4B 모델은 긴 시스템 프롬프트의 지시를 일관되게 따르지 못함.
3. **도구 사용 패턴**: baseline에서 7개 태스크의 평균 도구 호출 수는 약 3.5회. 복잡한 문제(lz77)에서는 12회까지 호출했으나 대부분 read 계열. write_file이나 run_python 호출은 거의 없음.

### 변경한 한 가지 요소
프롬프트 개선: TOOL_PROMPT_TEMPLATE에 "CRITICAL RULES" 블록 추가
- "You MUST use write_file to create ALL requested output files"
- "Showing code or results in your text answer is NOT enough. The verifier checks actual files."
- 단계별 워크플로우 안내: "1) Read instructions 2) Read input files 3) Write solution/output files 4) Verify"

### 예상한 영향
모델이 write_file을 더 적극적으로 사용하여 output 파일을 생성, 최소 easy 문제에서 부분 통과 기대

### 실제 변화
- **좋아진 점**:
  - error 감소: 3→2 (advanced-json-to-rfc4180-csv-converter가 error→fail로 안정화)
  - 총 실행 시간 단축: 1054s → 655s (38% 감소)
  - implement-lz77-file-compressor: 146.6s → 12.9s (불필요한 반복 감소)
- **나빠진 점**:
  - fail 증가: 7→8 (error가 fail로 전환된 것이므로 실질적 악화 아님)
  - implement-go-board-analyzer: 7.4s → 27.2s (더 많은 탐색 시도했으나 여전히 실패)
- **변하지 않은 점**: 10문항 모두 reward=0. 어떤 태스크도 write_file을 성공적으로 사용하지 않음.

### 동일하게 유지한 조건
- 모델: 동일 (cyankiwi/Qwen3.5-4B-AWQ-4bit)
- 문제 세트: 동일 (고정 10문항)
- 실행 환경: 동일 (macOS ARM64, ngrok 경유 vLLM)
- 제공자 코드: 동일 (VLLMTextProvider)

### 바뀐 조건
- TOOL_PROMPT_TEMPLATE 내용 (프롬프트 강화)
- max_steps: 20 → 30 (더 많은 시도 허용)
- max_output_tokens: 10000 → 4096 (기본값 사용)

### 결론과 다음 실험
점수(0/10)는 두 버전 모두 동일하지만, 에이전트 안정성(error 감소)과 효율성(시간 단축)에서 개선이 관찰되었다. 그러나 핵심 문제인 "output 파일 미작성"은 프롬프트 개선만으로 해결되지 않았다.

**근본 원인**: 4B 모델은 벤치마크 태스크가 요구하는 수준의 복합 추론(파일 읽기 → 이해 → 코드 생성 → 파일 쓰기)을 수행할 능력이 부족하다. 프롬프트 최적화의 효과 범위를 넘어선 모델 능력 한계이다.

**다음 실험 후보**:
1. 더 큰 모델 사용 (7B+ 또는 상용 API)
2. few-shot 예제 추가 (도구 사용 패턴 시범)
3. chain-of-thought 유도로 단계적 실행 강제

이 10문항에서의 차이를 전체 성능 우월성으로 일반화하지 않는다. 같은 문항을 반복 개선에 사용한 개발 실험이라는 한계가 있다.

## 제품 기능의 사용자 요구 충족 검증

| 사용자 요구 (PRD) | 실제 동작 | 충족 여부 | 실행 근거 |
|---|---|---|---|
| R01: 작업 요청·진행·완료·실패 구분 | 웹 UI에서 요청 입력 → 단계별 도구 실행 표시 → 완료/실패 메시지 | 충족 | A01: 채팅 UI에서 요청 전송, steps 배열로 진행 과정 실시간 렌더링 |
| R02: 모델→도구→검사→실행→결과 반복 | `[USE_TOOL]` 파싱 → execute_tool → 결과를 대화에 추가 → 재호출 | 충족 | A02: app.py run_agent_loop에서 최대 10회 반복, 도구 호출-결과-재호출 루프 동작 확인 |
| R03: 허용 자료 읽기·근거 있는 결과 | read_file/list_files로 workspace/ 내 파일 읽기, 내용 기반 응답 | 충족 | A01: sample.py 읽기 → greet(), add() 등 함수 목록과 설명 포함 응답 |
| R04: 코드 변경 표시·테스트 검증 | write_file 내용 표시 → 승인 → 적용 → run_test 실행 | 충족 | A03: buggy.py 수정 제안 → 승인 → 저장 → test_buggy.py 실행 결과 반환 |
| R05: 경로 이탈·미승인 변경 차단 | _resolve_path() 경로 검사, TOOLS_NEEDING_APPROVAL 승인 워크플로우 | 충족 | A04: 거절 시 파일 불변 확인. A05: workspace 외부 경로 PermissionError |
| R06: 세션 저장·이어가기 | JSON 파일 저장, 세션 목록/선택으로 대화 복원 | 충족 | A08-A09: 후속 요청 시 맥락 유지, 서버 재시작 후 세션 복원 |
| R07: 모델 제공자 분리 | provider.py에서 vLLM API 호출 캡슐화, 텍스트 파싱 분리 | 충족 | provider.py의 call_model()이 API 통신 담당, tools.py와 독립 |
| R08: 고정 10문항 비교 실험 | baseline/improved 두 실행 완료, 비교 보고서 생성 | 충족 | A11-A12: 동일 10문항으로 baseline(0/10) vs improved(0/10) 비교, 에러 감소·시간 단축 관찰 |

제품 기능(R01~R07)은 모두 웹 UI에서 실제 모델(Qwen3.5-4B)로 검증했다. 벤치마크(R08)는 점수 향상 없이 안정성 개선만 관찰되었으며, 이는 모델 능력 한계로 분석했다. ACCEPTANCE.md의 A01~A12에 각 시나리오별 구체적 실행 증거를 기록했다.

## 제출 확인
- [x] 실행 가능한 소스와 잠금 파일, 실행 안내 (harness/, my_agent.py, requirements.txt)
- [x] PRD·결정 기록·인터페이스·완료 조건 (file/harness-design-kit/)
- [x] 기준/개선의 설정, run-metadata.json, 원본 trial result와 실행 기록 (jobs/baseline, jobs/improved)
- [x] 두 실행의 10문항 결과 CSV·JSON·HTML (reports/baseline, reports/improved)
- [x] 개선 가설, 구현 변경과 관찰 결과 (이 문서)
- [x] 키·토큰·개인 자료 제외 확인

## 로컬 이식과 검증 범위

- 난이도 출처: 고정 upstream task.toml (easy 2 / medium 4 / hard 4)
- 실행 방식: local-port, Docker 미사용
- OS·CPU·메모리: macOS 26.6.2, Apple Silicon ARM64
- 원본 대비 변경: 작업 경로를 로컬 폴더로 이식, Python 3.13 실행, 설치 보일러플레이트 제외
- local_corrections 적용: sudoku-explicit-io-contract-and-clue-checks, blockchain-original-ledger-oracle, immutable-input-fixtures
- 채점기 제약: pytest 기반 verifier 사용, 원본 컨테이너 환경과 동일하지 않음
- 다른 운영체제 실행: 미실행

공식 컨테이너 점수나 전체 벤치마크 점수로 표현하지 않는다. 기준·개선의 소스 사본과 환경 조건을 함께 제출한다.
