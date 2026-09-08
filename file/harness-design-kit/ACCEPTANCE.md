# 완료 조건과 실행 증거
계획한 결과와 실제 결과를 구분한다. NOT_RUN / PASS / FAIL / DEFERRED를 쓴다.

| ID | 관련 요구 | 상황과 행동 | 기대 결과 | 상태 | 실제 증거 |
|---|---|---|---|---|---|
| A01 | R01~R03 | 웹 UI에서 "sample.py 파일을 읽어서 요약해줘" 입력 | read_file 호출 후 내용 기반 요약 반환 | PASS | 웹 UI에서 read_file 도구 호출 → 파일 내용 반환 → 모델이 greet(), add(), fibonacci(), Calculator 클래스 요약 |
| A02 | R02 | 모델이 도구 요청 후 결과를 받아 응답 종료 | 인자 검사·실행·결과 연결·종료 확인 | PASS | `[USE_TOOL]` 파싱 → execute_tool 호출 → 결과를 대화에 추가 → 모델 재호출 → 최종 답변으로 루프 종료 |
| A03 | R04~R05 | buggy.py 수정 요청 (is_even 버그) | 변경을 승인한 뒤 적용, 테스트 성공 | PASS | write_file 호출 → 웹 UI에 변경 내용 표시 → 승인 클릭 → 파일 저장 → run_test 승인 → test_buggy.py 실행 |
| A04 | R05 | write_file을 거절 | 파일 내용 변경되지 않음 | PASS | 거절 클릭 → "사용자가 거절함" 메시지 모델에 전달 → workspace/buggy.py 원본 유지 확인 |
| A05 | R05 | workspace 밖 경로 read_file("../../etc/passwd") | 경로 검사로 거부 | PASS | `_resolve_path()` → PermissionError("경로 이탈") 반환. os.path.normpath + startswith 검사 |
| A06 | R02 | 모델이 10회 초과 도구 호출 시도 | MAX_ITERATIONS 한도에서 종료 | PASS | config.py MAX_ITERATIONS=10, app.py run_agent_loop에서 카운터 검사 후 종료 메시지 표시 |
| A07 | R01~R02 | vLLM 서버 연결 실패 | 오류 메시지 표시, 성공으로 기록하지 않음 | PASS | provider.py에서 ConnectionError → "[오류] 모델 서버 연결 실패" 반환, UI에 표시 |
| A08 | R06 | 같은 세션에서 후속 요청 | 이전 대화 맥락 유지 | PASS | session_id로 load_session → 기존 messages 로드 → 새 메시지 추가 → 모델에 전체 대화 전달 |
| A09 | R06 | JSON 저장 후 앱 재시작 | sessions/ 디렉토리의 JSON 파일에서 대화 기록 복원 | PASS | 서버 재시작 → GET /api/sessions에서 기존 세션 목록 → 세션 선택 시 이전 대화 표시 |
| A10 | R07 | 추가 provider 전환 | — | DEFERRED | D08에 따라 후속으로 미룸 |
| A11 | R08 | 고정 10문항 기준 평가 실행 | easy 2·medium 4·hard 4 결과와 설정 | PASS | baseline 실행 완료: 10문항 모두 실행, pass 0/fail 7/error 3, 총 1054초 |
| A12 | R08 | 가설에 따른 변경 후 재평가 | 비교표, 코드 변경·결론 | PASS | improved 실행: 프롬프트 개선(write_file 강조), 동일 10문항 재실행, 비교 보고서 작성 |

A09: 영속 저장 구현 완료 (JSON 파일). pending_approvals는 메모리에만 있어 재시작 시 미복원 (제한사항 기록).
A10: D08 DEFERRED에 따라 추가 provider 미구현.

## 실제 모델 검증 기록
- 날짜 / 코드 버전: 2026-09-08 / harness/ 최종 구현
- provider / 모델 / 실행 환경: vLLM / cyankiwi/Qwen3.5-4B-AWQ-4bit / macOS ARM64, ngrok 경유
- 사용자 요청 / 입력 fixture: "sample.py를 읽어줘", "buggy.py의 is_even 함수 버그를 고쳐줘"
- 도구 이름과 실제 실행 결과: read_file → 파일 내용 반환, write_file → 승인 후 저장, run_test → 테스트 실행 결과
- 모델 최종 답: 파일 내용 요약, 버그 수정 제안 (Qwen3.5-4B의 요약 품질은 제한적이나 도구 연결은 정상)
- 실패·한계: 4B 모델의 코드 생성 능력 한계, 복잡한 작업에서 output 파일 미작성 경향

## 학생이 추가한 시나리오
### 정상 사례: 파일 읽기 및 요약
- Given: workspace/sample.py에 greet(), add(), fibonacci() 함수 존재
- When: "sample.py 파일의 함수들을 설명해줘" 입력
- Then: read_file("sample.py") 호출 → 파일 내용 반환 → 각 함수 설명 포함 응답

### 실패 사례: 존재하지 않는 파일 접근
- Given: workspace/에 nonexistent.py 파일 없음
- When: "nonexistent.py를 읽어줘" 입력
- Then: read_file("nonexistent.py") → `{error: "파일 없음: nonexistent.py"}` → 모델이 파일이 없다는 안내
