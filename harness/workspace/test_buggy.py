"""buggy.py 테스트"""
from buggy import is_even, reverse_string, find_max

def test_is_even():
    assert is_even(0) == True, "0은 짝수여야 함"
    assert is_even(2) == True
    assert is_even(3) == False

def test_reverse_string():
    assert reverse_string("hello") == "olleh"
    assert reverse_string("a") == "a"
    assert reverse_string("") == ""

def test_find_max():
    assert find_max([1, 3, 2]) == 3
    assert find_max([-1, -5, -2]) == -1
    assert find_max([42]) == 42

if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_"):
            try:
                func()
                print(f"PASS: {name}")
            except Exception as e:
                print(f"FAIL: {name} - {e}")
