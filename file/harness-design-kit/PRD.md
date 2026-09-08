# 개인 에이전트 하네스 PRD
상태: 구현 완료.

## 제공된 제품 목표
사용자가 자연어로 작업을 요청하면 모델이 필요한 도구를 선택하고, 내 프로그램이 이를 검사·실행하여 결과를 다시 모델에 전달한다. 자료를 읽는 범용 작업과 코드를 수정하고 검증하는 코딩 작업을 모두 다룬다. 사용자는 진행 상황과 실패 이유를 확인할 수 있다.
PRD(Product Requirements Document)는 무엇을 누구를 위해 만들고 어떤 결과를 완료로 볼지 기록한다. 구현 방법의 모든 세부사항을 미리 고정하는 문서는 아니다.

## 학생이 완성한 사용자 이야기
D01 사용자/업무: CHOSEN — 프로젝트 폴더의 Python 파일을 읽고 요약
- 나는 **개발자**로서 **프로젝트 폴더의 Python 소스 코드**를 **읽고 요약·분석·수정**하고 싶다.
- 지금 불편한 점: 여러 파일을 하나씩 열어 확인하고 수정하는 반복 작업이 번거로움
- 실제로 성공했다고 판단할 결과: 에이전트가 파일을 읽어 요약을 제시하고, 버그 수정을 제안하면 승인 후 적용되어 테스트 통과
- 실습용 자료: workspace/ 내 sample.py, buggy.py, test_buggy.py

## 공통 요구사항
| ID | 제품이 해야 할 일 | 학생이 구체화한 내용 |
|---|---|---|
| R01 | 작업 요청을 받고 진행·완료·실패를 구분한다 | Flask 웹 UI에서 채팅 형태로 요청, 단계별 도구 실행 결과를 실시간 표시 |
| R02 | 모델→도구 요청→검사→실행→결과 반환을 직접 구현한다 | 최대 10회 반복, 120초 모델 응답 제한, 텍스트 파싱으로 `[USE_TOOL]` 태그 추출 |
| R03 | 허용한 자료를 읽고 근거를 확인할 수 있는 결과를 만든다 | read_file, list_files 도구로 workspace/ 내 파일 접근, 결과를 모델에 전달 |
| R04 | 코드 변경을 보여 주고 제한된 테스트로 검증한다 | write_file로 변경 내용 표시, run_test로 Python 테스트 실행 (30초 제한) |
| R05 | 권한 없는 경로·승인 없는 변경을 막는다 | workspace/ 외부 경로 차단 (_resolve_path), write_file/run_test는 웹 UI에서 승인 필요 |
| R06 | 실행 기록과 세션을 구분하고 이어갈 범위를 설명한다 | JSON 파일로 대화 기록 저장, 세션 ID로 구분, 서버 재시작 후에도 대화 맥락 유지 |
| R07 | 모델 제공자와 제품 내부 계약을 분리한다 | provider.py에서 vLLM API 호출 분리, 텍스트 파싱으로 도구 호출 추출 |
| R08 | 고정 10문항으로 기준 측정과 변경 후 측정을 수행하고 결과를 비교한다 | Terminal-Bench Pro 로컬 이식판 10문항, baseline vs improved 비교 실험 |

## 학생의 선택
D02 플랫폼: CHOSEN — 로컬 웹 (Flask, port 5001). 브라우저 UI로 대화형 인터페이스와 승인/거절 UX 구현.
D03 언어: CHOSEN — Python. vLLM/코랩 환경과 자연스럽게 연결.
D04 첫 provider: CHOSEN — vLLM (Qwen3.5-4B-AWQ-4bit), OpenAI 호환 API, ngrok 경유. 텍스트 파싱 방식(`[USE_TOOL]`/`[/USE_TOOL]`).
D05 첫 작업과 도구 범위: CHOSEN — read_file → list_files → write_file → run_test 순서 확장. workspace/ 폴더 한정.
D06 승인 방식: CHOSEN — 읽기(read_file, list_files)는 자동 허용, 쓰기/실행(write_file, run_test)은 변경 내용 표시 후 웹 UI에서 승인/거절.
D07 세션과 저장: CHOSEN — JSON 파일로 대화 기록 저장, 세션 이어가기 지원. 서버 재시작 시에도 기록 유지.
D08 추가 provider: DEFERRED — 첫 구현 완료 후 필요시 추가.
D09 확장 기능: DEFERRED — 핵심 기능 우선.

## 최초 범위와 제외 범위
최초 범위: D01~D07에 따른 Flask 웹 하네스 — 파일 읽기/쓰기/테스트, 승인 워크플로우, 세션 저장, vLLM 텍스트 파싱 기반 도구 호출
후속 범위: 추가 provider, 취소 기능, 동시 도구 실행
이번 버전에서 제외: 공개 원격 제어 서비스, 임의 시스템 전체 접근, 비밀키 공유, Docker 실행 환경
기본 제외: 원격 접속은 별도 설계 없이는 추가하지 않는다.

## 완료 기준
ACCEPTANCE.md의 공통 시나리오에 실제 증거를 남긴다. vLLM (Qwen3.5-4B) 모델에서 범용 작업과 코딩 작업을 확인하고, 오류·거절도 검증한다. 추가 provider는 DEFERRED. 저장 재개는 구현 완료.

## 벤치마크 실험
Docker 없이 실행하는 Terminal-Bench Pro 로컬 이식판의 고정 목록으로, 원본 easy 2·medium 4·hard 4를 사용한다. my_agent.py 어댑터로 vLLM 에이전트를 harness-lab 평가 규격에 연결. baseline(기본 프롬프트) → improved(출력 파일 작성 강조 프롬프트) 비교 실험 수행.
