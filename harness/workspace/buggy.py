"""의도적 결함이 있는 코드 - 코딩 작업 테스트용"""

def is_even(n: int) -> bool:
    # 버그: 0을 짝수로 판단하지 못함
    if n == 0:
        return False  # 버그! 0은 짝수
    return n % 2 == 0

def reverse_string(s: str) -> str:
    # 버그: 마지막 글자 누락
    return s[-2::-1]

def find_max(numbers: list) -> int:
    # 버그: 빈 리스트 처리 없음
    max_val = numbers[0]
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val
