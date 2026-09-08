"""샘플 Python 파일 - 에이전트 하네스 테스트용"""

def greet(name: str) -> str:
    return f"안녕하세요, {name}님!"

def add(a: int, b: int) -> int:
    return a + b

def fibonacci(n: int) -> list:
    if n <= 0:
        return []
    if n == 1:
        return [0]
    result = [0, 1]
    for i in range(2, n):
        result.append(result[-1] + result[-2])
    return result

class Calculator:
    def __init__(self):
        self.history = []

    def calculate(self, op: str, a: float, b: float) -> float:
        ops = {
            "add": a + b,
            "sub": a - b,
            "mul": a * b,
            "div": a / b if b != 0 else float("inf"),
        }
        result = ops.get(op, None)
        if result is None:
            raise ValueError(f"Unknown operation: {op}")
        self.history.append((op, a, b, result))
        return result

if __name__ == "__main__":
    print(greet("세계"))
    print(f"fibonacci(10) = {fibonacci(10)}")
    calc = Calculator()
    print(f"3 + 5 = {calc.calculate('add', 3, 5)}")
