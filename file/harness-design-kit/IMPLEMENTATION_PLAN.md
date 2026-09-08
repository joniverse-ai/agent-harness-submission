# 구현 계획
## 시작 조건
D01~D07의 최초 범위와 계약·완료 조건을 정하고 학생이 구현을 요청했다. D08/D09는 미뤄도 된다.

## 1. 첫 수직 구현
사용자 요청 → vLLM 모델 → read_file 도구 → 모델에 결과 전달 → 웹 UI에 표시.
- 선택 작업/도구: read_file로 workspace/sample.py 읽기 및 요약
- 필요한 파일: config.py, tools.py, provider.py, app.py, templates/index.html
- 의존성: flask>=3.0, requests>=2.31
- 실행: `python3 app.py` → http://localhost:5001
- 완료 증거: 웹 UI에서 "sample.py를 읽어줘" 입력 → read_file 호출 → 파일 내용 기반 요약 응답

## 2. 범용 작업의 품질
- list_files 도구 추가, 경로 이탈 검사 (`_resolve_path`)
- 원문과 결과 대조: 모델 응답에 실제 파일 내용 근거 포함 확인
- 인자 오류: 잘못된 경로, 빈 문자열 등 에러 처리
- 반복 한도: MAX_ITERATIONS=10으로 무한 루프 방지

## 3. 코딩 작업과 권한
- write_file, run_test 도구 추가
- 승인 워크플로우: TOOLS_NEEDING_APPROVAL = {"write_file", "run_test"}
- 웹 UI에서 변경 내용 표시 → 승인/거절 버튼
- buggy.py의 의도적 결함 수정 → test_buggy.py 실행으로 검증
- 거절 시 파일 내용 불변 확인

## 4. 제품 기능
- 세션 저장: JSON 파일로 sessions/ 디렉토리에 저장
- 세션 이어가기: 기존 세션 선택 후 대화 이어가기
- 상태 표시: 각 단계(도구 호출, 결과, 승인 대기)를 UI에 실시간 표시

## 5. 고정 10문항 비교 실험
- my_agent.py 어댑터로 vLLM 에이전트를 harness-lab 평가 규격에 연결
- VLLMTextProvider 클래스: 텍스트 파싱 기반 도구 호출 추출
- baseline: 기본 프롬프트로 10문항 실행
- 실패 분석: 모델이 output 파일을 작성하지 않는 문제 발견
- improved: 프롬프트에 write_file 사용 강조 ("CRITICAL RULES") 추가
- 동일 10문항 재실행 후 비교

## 각 단계의 기록
| 단계 | 관련 요구·검증 ID | 구현한 변경 | 확인한 결과 | 남은 문제 |
|---|---|---|---|---|
| 1. 첫 수직 | R01-R03, A01 | config/tools/provider/app.py 생성 | 파일 읽기·요약 성공 | — |
| 2. 범용 품질 | R02-R03, A02, A05, A07 | list_files 추가, 경로 검사, 에러 처리 | 경로 이탈 차단, 없는 파일 에러 | — |
| 3. 코딩·권한 | R04-R05, A03-A04 | write_file/run_test, 승인 UI | 승인→적용→테스트, 거절→불변 | — |
| 4. 제품 기능 | R06, A08-A09 | session.py, JSON 저장 | 세션 이어가기 성공 | 재시작 후 pending_approvals 미복원 |
| 5. 벤치마크 | R08, A11-A12 | my_agent.py 어댑터 | baseline 0/10 → improved 실행 중 | 4B 모델 한계 |

설계 변경: Qwen3.5의 `<tool_call>` 태그 충돌 발견 → `[USE_TOOL]`/`[/USE_TOOL]` 커스텀 태그로 변경. INTERFACES.md 반영 완료.
