# Agent Terminal Benchmark

직접 만든 AI 에이전트를 10개 터미널 작업으로 평가하고, 실패 기록을 근거로 개선하는 실습용 저장소입니다. Python 3.13과 `uv`를 사용하며 Docker는 필요하지 않습니다. 내부 Python 패키지 이름은 `harness_lab`입니다.

이 저장소의 배포 버전 **v1.0.0**은 고정된 Terminal-Bench Pro 원본을 가져오는 **로컬 평가 v2**를 사용합니다. 배포 버전과 평가 버전은 별개입니다. 공식 컨테이너 벤치마크 점수가 아닙니다. [정정 내역](https://github.com/SunCreation/agent-terminal-benchmark/blob/main/BENCHMARK_ERRATA.md)과 [학생 실습 안내](https://github.com/SunCreation/agent-terminal-benchmark/blob/main/STUDENT_GUIDE.md)를 함께 읽으세요.

## AI 개발 도우미에게 요청하기

> 학생 안내를 읽고 실행 환경을 준비해 줘. 내 하네스를 연결하고 같은 조건으로 개선 전후를 비교하자.

<details>
<summary>직접 준비하고 첫 실행하기</summary>

저장소를 복제하고 `pyproject.toml`이 있는 루트에서 실행합니다. Python 3.13과 uv가 준비되어 있어야 합니다. Git을 쓰지 않는다면 [v1.0.0 배포 파일](https://github.com/SunCreation/agent-terminal-benchmark/releases/tag/v1.0.0)의 `agent-terminal-benchmark.zip`을 풀고 같은 루트에서 `uv sync --locked`부터 진행합니다.

```sh
git clone https://github.com/SunCreation/agent-terminal-benchmark.git
cd agent-terminal-benchmark
uv sync --locked
uv run python -m harness_lab.benchmark_source --prepare
```

마지막 명령은 고정 커밋의 원본 파일을 다운로드하고 SHA256·크기를 확인합니다. 처음 준비에는 인터넷이 필요합니다. 캐시에는 채점 코드와 참고 풀이도 있으므로 학생 에이전트에는 전달하지 않습니다.

**OpenAI 사용:** 같은 터미널에서 키를 숨김 입력합니다. 키 값이 화면에 표시되지 않는 것이 정상입니다.

```sh
export OPENAI_API_KEY="$(uv run python -c 'import getpass; print(getpass.getpass("OpenAI API key: "))')"
```

Windows PowerShell에서는 다음을 사용합니다.

```powershell
$env:OPENAI_API_KEY = uv run python -c "import getpass; print(getpass.getpass('OpenAI API key: '))"
```

다음의 `YOUR_MODEL_ID`는 사용 가능한 실제 모델 ID로 바꿉니다. 개발 도우미 로그인과 이 프로그램의 API 인증은 별개입니다. 실행은 선택한 모델의 API를 호출합니다.

```sh
uv run python -m harness_lab.bench --name provided-baseline --agent harness_lab.local_agent:solve_task --provider openai --model YOUR_MODEL_ID --max-steps 40 --max-seconds 300
```

**Ollama 사용:** 로컬 서비스와 도구 호출을 지원하는 모델이 준비되어 있다면 OpenAI 키 없이 실행할 수 있습니다. `ollama list`로 설치된 이름을 확인하고 `YOUR_LOCAL_MODEL`을 바꿉니다.

```sh
ollama list
uv run python -m harness_lab.bench --name provided-ollama --agent harness_lab.local_agent:solve_task --provider ollama --model YOUR_LOCAL_MODEL --max-steps 40 --max-seconds 300
```

한 실행은 10개 작업을 순서대로 평가합니다. 기본 제한은 작업별 **40단계·300초**, 모델 요청별 **출력 토큰 상한 10,000**입니다. `--max-steps`, `--max-seconds`, `--max-output-tokens`로 바꿀 수 있습니다. `--max-seconds`는 에이전트의 작업별 제한이며 준비·채점 시간까지 포함한 전체 실행 시간은 아닙니다. 기존 실행 이름을 재사용하지 말고 새 이름으로 기록을 보존하세요.

</details>

## 내 에이전트 연결하기

제공된 `harness_lab.local_agent:solve_task`는 바로 실행할 수 있는 기준 구현입니다. 자신의 설계를 평가하려면 **모델 호출·도구 실행·반복 종료를 자신의 구현으로 연결**해야 합니다. 제공 구현을 그대로 호출하는 어댑터는 연결 확인용이며 독자적인 에이전트 구현으로 구분하지 않습니다.

<details>
<summary>어댑터 복사와 학생 에이전트 실행</summary>

[연결 예제](https://github.com/SunCreation/agent-terminal-benchmark/blob/main/examples/benchmark_agent.py)를 루트의 `my_agent.py`로 복사한 뒤 자신의 코드에 연결합니다.

템플릿은 미구현 상태에서 `NotImplementedError`를 내도록 되어 있습니다. 복사한 다음 자신의 하네스를 연결하고 아래 두 번째 명령을 실행합니다.

```sh
uv run python -c "import shutil; shutil.copyfile('examples/benchmark_agent.py', 'my_agent.py')"
uv run python -m harness_lab.bench --name baseline --agent my_agent:solve_task --provider openai --model YOUR_MODEL_ID --max-steps 40 --max-seconds 300
```

`my_agent:solve_task`는 `my_agent.py`의 비동기 함수 `solve_task`를 뜻합니다. 함수 계약과 기록 방법은 [STUDENT_GUIDE](https://github.com/SunCreation/agent-terminal-benchmark/blob/main/STUDENT_GUIDE.md)에 설명되어 있습니다. Ollama를 연결할 때는 `--provider ollama --model YOUR_LOCAL_MODEL`로 바꿉니다.

```sh
uv run python -m harness_lab.bench --help
uv run python -m harness_lab.report jobs/baseline --output reports/baseline
```

`--dry-run`은 설정 확인용이며 모델 인증·실제 풀이 성공까지 확인하지 않습니다.

</details>

## 결과 읽기

실행별 결과는 `jobs/<실행이름>/`에 저장됩니다. `scoreboard/index.html`에서 현황을 보고, 작업별 `result.json`과 `agent/`, `verifier/` 기록으로 원인을 확인합니다.

| 항목 | 의미 |
|---|---|
| 이진 점수 | 정상 완료하고 채점 reward가 1인 작업 수 ÷ 예정된 전체 작업 수 |
| 상태 | pass·fail·error·pending을 구분. 에이전트 완료와 채점 성공은 별개 |
| 부분 검사 통과 | 예: 19/22는 실패 원인을 찾는 정보. 작업 점수 19/22점이 아님 |
| 여러 시도 | `--attempts`의 모든 시도를 분모에 포함한 평균. pass@k가 아님 |
| 사용량·비용 | 미확인 값은 0이 아님. 모델·제공자에 따라 수집되지 않을 수 있음 |

v2에서는 스도쿠의 누락된 I/O 계약을 공개하고 추가 퍼즐 검사를 강화했습니다. 블록체인은 원본 입력에서 정답을 계산하며 입력 교체를 거부합니다. 준비된 입력 파일의 변경 여부도 확인합니다. v1 점수와 직접 비교하지 마세요. `--self-check`는 참고 풀이로 채점 연결을 검증하는 운영자 기능이며 학생 에이전트 점수가 아닙니다.

## 제출과 공개 범위

제출물은 **자신의 구현, 실행 설정과 결과, 실패 근거와 개선 회고**입니다. 비교할 때 모델·제한·평가 버전을 맞추고 변경점을 적습니다. 자세한 목록은 [학생 안내](https://github.com/SunCreation/agent-terminal-benchmark/blob/main/STUDENT_GUIDE.md)를 따릅니다.

키는 환경 변수로만 전달하고 코드·프롬프트·로그에 기록하지 마세요. 로그에는 대화와 파일 내용이 들어갈 수 있으며 실행 스냅샷에는 원본 채점 자료도 포함됩니다. `jobs/`와 캐시 전체를 공개 저장소에 올리지 말고, 제출 전에 필요한 결과와 로그 발췌에서 개인정보·키·참고 풀이가 빠졌는지 확인합니다. 도구의 경로 검사는 운영체제 샌드박스가 아니므로 실습용 파일만 있는 환경에서 실행하세요.
