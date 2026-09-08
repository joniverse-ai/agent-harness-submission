# 학생 실습 안내

목표는 점수 하나를 얻는 데서 끝나지 않습니다. **자신의 에이전트가 무엇을 보고 어떤 도구를 실행했으며 왜 멈췄는지 설명하고, 한 가지 변경의 효과를 비교**합니다. 실행 준비는 [README](https://github.com/SunCreation/agent-terminal-benchmark/blob/main/README.md)를 따릅니다.

## 1. 기준 실행을 남기기

제공된 `harness_lab.local_agent:solve_task`로 연결과 평가 흐름을 확인합니다. 이어 자신의 `my_agent:solve_task`로 첫 결과를 남깁니다. 두 실행을 각각 제공 기준선과 내 기준선으로 표시하세요. 모델 ID, provider, `--max-steps`, `--max-seconds`, `--max-output-tokens`, 시도 수와 평가 버전을 기록합니다. 기본값은 작업별 40단계·300초, 모델 요청별 출력 토큰 상한 10,000입니다.

AI 개발 도우미에는 다음처럼 요청할 수 있습니다.

> 내 에이전트를 이 평가기에 연결해 줘. 실패 로그를 보고 개선할 부분 하나를 골라 같은 조건으로 다시 시험하자.

## 2. 어댑터 계약 이해하기

<details>
<summary>solve_task 입력·출력과 파일 경계</summary>

루트에 `my_agent.py`를 두고 다음 함수를 구현합니다.

```python
from pathlib import Path

async def solve_task(
    instruction: str,
    workspace: Path,
    logs_dir: Path,
    options: dict,
) -> dict:
    # 자신의 모델·도구 반복을 실행하고 실제 작업 파일을 남깁니다.
    # 아래 반환 구조는 예시이며, 종료 상태는 실제 실행 결과로 결정합니다.
    ...
```

| 입력 | 사용 방법 |
|---|---|
| `instruction` | 경로와 공개 계약이 준비된 해당 작업의 지시문 |
| `workspace` | 에이전트가 읽고 쓰는 작업공간. 다른 작업이나 상위 폴더를 탐색하지 않음 |
| `logs_dir` | 도구 요청·결과·종료 이유를 남길 기록 폴더 |
| `options` | `provider`, `model`, `max_steps`, `max_seconds`, `max_output_tokens`, `command_timeout`, `task_cwd` 등 실행 설정 |

작업별 시작 폴더는 `workspace / options['task_cwd']`입니다. 모든 작업을 무조건 `app/`에서 실행한다고 가정하지 마세요. 요청한 출력 파일을 실제 작업공간에 작성해야 합니다. 마지막 답변에 코드를 보여 주는 것만으로 파일 제출이 되지 않습니다.

반환값은 JSON으로 기록할 수 있는 딕셔너리입니다. 예를 들어 정상적으로 종료했다면 `status`, `answer`, `metrics`를 다음 구조로 반환할 수 있습니다.

```python
return {
    "status": "completed",
    "answer": final_answer,
    "metrics": {
        "usage_known": usage_is_known,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    },
}
```

시간·단계 제한으로 중단했다면 `completed`로 위장하지 말고 실제 상태를 남깁니다. 사용량을 모르면 `usage_known=False`로 표시하고 임의의 0을 성능 수치로 쓰지 않습니다. 채점은 함수가 반환된 뒤 별도로 실행됩니다.

[연결 예제](https://github.com/SunCreation/agent-terminal-benchmark/blob/main/examples/benchmark_agent.py)를 참고하세요. `my_agent.py` 외의 보조 코드가 필요하면 하나의 Python 패키지로 묶고 `my_agent_package.entry:solve_task`처럼 연결합니다. 실행 스냅샷은 선택된 최상위 모듈 또는 패키지의 Python 파일을 복사하므로 별도 형제 모듈이나 비코드 데이터에 의존할 때는 포함 여부를 확인해야 합니다.

학생 에이전트에는 instruction·작업공간만 작업 자료로 제공합니다. `.benchmark-cache/`, 실행 스냅샷의 `benchmark/upstream/`, `verifier/`, 참고 풀이를 탐색하거나 정답을 프롬프트에 넣으면 에이전트 능력 비교가 성립하지 않습니다. 준비된 입력·채점기·평가 manifest도 수정하지 않습니다.

</details>

## 3. 실패 한 건을 근거로 개선하기

<details>
<summary>수동 점검 순서와 비교 명령</summary>

1. `jobs/baseline/scoreboard/index.html`에서 pass·fail·error·pending을 확인합니다.
2. 해당 작업의 `result.json`에서 에이전트 상태와 예외 여부를 먼저 확인합니다.
3. `agent/` 기록에서 파일 읽기, 쓰기, 실행 요청과 실제 결과를 확인합니다.
4. `verifier/stdout.txt`에서 실패한 검사가 요구하는 동작을 확인합니다. 이 분석 결과로 일반적인 도구·반복 설계를 개선하며, 채점 코드나 참고 풀이를 모델 입력으로 사용하지 않습니다.
5. 원인을 실행 실패·출력 누락·형식 위반·잘못된 풀이·제한 도달 등으로 설명하고 변경 하나를 선택합니다.

예를 들어 도구 오류를 모델에 돌려주지 않은 것이 원인이면 오류 전달 방식을 개선합니다. 원인 확인 없이 프롬프트 길이나 재시도 수를 늘리는 실험은 해석하기 어렵습니다.

같은 모델과 제한으로 새 이름의 실행을 만듭니다. `YOUR_MODEL_ID`는 실제 모델 ID로 바꿉니다.

```sh
uv run python -m harness_lab.bench --name improved --agent my_agent:solve_task --provider openai --model YOUR_MODEL_ID --max-steps 40 --max-seconds 300
uv run python -m harness_lab.report jobs/improved --compare jobs/baseline --output reports/comparison
```

결과는 `reports/comparison/index.html`에서 확인합니다. 모델이나 제한도 바꿨다면 에이전트 설계만의 효과라고 주장하지 않습니다. 시도 수를 바꾸면 `report` 명령의 `--attempts`도 실제 값과 맞추세요.

</details>

`completed`는 에이전트가 종료했다는 뜻이지 정답이라는 뜻이 아닙니다. 10개 중 3개가 정상 완료·reward 1이면 점수는 30%입니다. 일부 검사만 통과한 작업은 이진 점수에서 실패이며, 에러나 미완료 작업을 분모에서 빼지 않습니다. v2 정정 사항은 [BENCHMARK_ERRATA](https://github.com/SunCreation/agent-terminal-benchmark/blob/main/BENCHMARK_ERRATA.md)를 기준으로 설명합니다.

## 4. 제출하기

다음 자료를 제출합니다.

- **구현:** 자신의 에이전트·어댑터 코드, 실행에 필요한 의존성, 제공 기준 구현에서 바꾼 부분.
- **재현 설정:** 저장소 커밋, 평가 ID·버전, provider·모델 ID, 실행 제한, 시도 수, 실행 명령. API 키는 제외.
- **결과:** baseline·improved의 요약 JSON 또는 CSV, 점수와 pass/fail/error/pending 개수. 필요한 작업 로그만 발췌.
- **회고:** 실패 사례 하나의 근거, 변경 가설과 실제 코드 변경, 좋아진 점·나빠진 점, 반복 실행 부족 등 해석의 한계.

전체 `jobs/`, 캐시, 계정 설정, 원본 참고 풀이를 제출물에 묶지 않습니다. 출력 로그에 키·개인정보가 섞이지 않았는지 확인하고, 토큰·비용이 미확인이라면 그대로 표시하세요. 점수가 오르지 않았더라도 실행 기록과 가설을 정확히 연결한 실험은 설명할 수 있습니다.
