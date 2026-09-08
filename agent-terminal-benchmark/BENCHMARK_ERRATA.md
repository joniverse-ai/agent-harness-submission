# 로컬 평가 v2 정정 내역

2026-09-08. 고정 원본 `alibaba/terminal-bench-pro@874af409da6aafebccbf3bc5bb41a2fa4d78784d`의 두 문제에서 지시문·입력·채점 불일치를 확인했습니다. 벤치마크 전체가 잘못됐다는 주장은 아닙니다. 로컬 캐시의 SHA256와 크기는 고정 원본 manifest와 일치합니다.

원본 캐시는 수정하지 않고 준비·채점 단계에 명시적인 보정을 적용합니다. 새 평가 ID는 `terminal-bench-pro-local-port-v2`, port_version은 `2.0.0`입니다. 원본 커밋·난이도·10문제 목록은 유지합니다. v1과 점수를 직접 비교하지 않습니다.

## 스도쿠: 공개되지 않은 함수 계약

원본 instruction.md는 is_valid, solve_sudoku, find_empty를 지정하지만 추가 퍼즐 검사는 read_puzzle과 write_solution도 호출합니다. 첫 추가 검사는 호출하지도 않는 main의 전역 변수까지 수정합니다. 파일 읽기·쓰기는 요구된 기능이지만 이 특정 함수명은 공개된 요구사항이 아니었습니다.

두 모델 실행에서 19/22 중 실패 3건은 read_puzzle 누락에 따른 AttributeError였습니다. 새 복사본에 입출력 연결 함수만 추가하자 알고리즘을 바꾸지 않고 두 구현 모두 강화된 22개 검사를 통과했습니다. 이는 원인 확인 진단이지 모델 재실행이나 소급 점수 변경이 아닙니다.

수정 내용:

- 준비된 지시문에 read_puzzle(filename)의 9×9 정수 보드 반환, solve_sudoku(board)의 제자리 수정·bool 반환, write_solution(board, filename)의 파일 형식을 공개합니다.
- 불필요한 main.__globals__ 접근을 제거합니다. 특정 main 함수나 전역 변수는 요구하지 않습니다.
- 추가 퍼즐 세 검사에서 입력·풀이 파일이 없으면 실패합니다. 출력이 유효한 스도쿠인지와 원래 단서를 보존했는지를 모두 검사합니다. 이미 풀린 퍼즐의 출력도 확인합니다.
- 나머지 원본 검사는 보존합니다. 총 검사 수는 22개입니다.

## 블록체인: 입력과 고정 정답의 불일치

원본은 120개 거래의 원장을 제공하지만 마지막 검사는 그 원장에 없는 ID를 고정 정답으로 요구합니다. 원본 참고 풀이는 원장을 12개 거래로 새로 만들고 그 고정 ID에 오류를 넣은 뒤 풀이합니다. 따라서 이전 참고 풀이 304/304 통과는 원본 입력과 검사의 정합성을 보장하지 못했습니다. 입력 교체를 검증하지 않은 것은 로컬 실습 자료의 검증 누락이기도 합니다.

수정 내용:

- 정답은 해시로 검증한 원본 입력에서 계산합니다. 거래 순서대로 previous_hash, current_hash를 확인해 최초 오류의 ID·필드·원래 잘못된 값 전체를 비교합니다. 정답 ID만 다른 상수로 바꾸지 않습니다.
- 작업 원장이 원본과 같은 바이트인지 별도 검사합니다. 원장을 바꾸고 그 교체본에 맞춘 답을 제출해도 실패합니다.
- 참고 풀이의 원장 생성 단계를 제외하고 실제 분석 코드만 실행합니다.
- 원본 검사 1~9 유지, 10번 교정, 원장 불변 검사 추가로 총 11개입니다.

## 입력 보호와 검증

모든 문제에서 준비 직후 입력 해시를 기록하고 채점 시 변경·삭제를 검사합니다. 입력이 바뀌면 다른 검사가 통과해도 reward=0입니다. 이는 OS 보안 샌드박스는 아닙니다.

수정된 참고 풀이 경로는 10/10문제, 305/305검사를 통과했고 입력 변경은 0건입니다. 모델 점수가 아닙니다. 잘못된 거래·후속 오류·입력 교체·다른 유효 스도쿠 답·누락된 파일을 거부하는 회귀 검사도 추가했습니다. 자세한 검증 범위는 VALIDATION.md를 참고하세요.

이전 실행의 파일과 점수는 보존합니다. 수정된 지시문으로 새 작업공간에서 실행해야 v2의 모델 결과입니다. 알려진 다른 원본 검사 한계까지 모두 해결하거나 공식 컨테이너 환경을 재현한 것은 아닙니다.

## 원본 근거

- [스도쿠 지시문](https://github.com/alibaba/terminal-bench-pro/blob/874af409da6aafebccbf3bc5bb41a2fa4d78784d/python-sudoku-solver-backtracking/instruction.md)
- [스도쿠 채점 코드](https://github.com/alibaba/terminal-bench-pro/blob/874af409da6aafebccbf3bc5bb41a2fa4d78784d/python-sudoku-solver-backtracking/tests/test_outputs.py)
- [블록체인 고정 정답 검사](https://github.com/alibaba/terminal-bench-pro/blob/874af409da6aafebccbf3bc5bb41a2fa4d78784d/detect-corrupted-blockchain-transaction/tests/test_outputs.py#L96-L98)
- [입력을 교체하는 참고 풀이](https://github.com/alibaba/terminal-bench-pro/blob/874af409da6aafebccbf3bc5bb41a2fa4d78784d/detect-corrupted-blockchain-transaction/solution/solve.sh#L13-L95)
