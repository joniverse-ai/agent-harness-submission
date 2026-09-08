"""Behavioral regressions for the local Sudoku correction; never edit cache."""
import ast
from pathlib import Path
import shutil

import pytest

from harness_lab.benchmark_source import relocate
from harness_lab.sudoku_contract import correct_verifier, supplement_instruction


CACHE = Path(__file__).resolve().parents[1] / '.benchmark-cache/python-sudoku-solver-backtracking'
CASES = ['test_easy_puzzle_can_be_solved', 'test_hard_puzzle_can_be_solved',
         'test_already_solved_puzzle']


@pytest.fixture
def source():
    path = CACHE / 'tests/test_outputs.py'
    if not path.exists():
        pytest.skip('Pinned upstream Sudoku source has not been fetched')
    return path.read_text()


@pytest.fixture
def trial(tmp_path, source):
    (tmp_path / 'app').mkdir()
    shutil.copytree(CACHE / 'environment/test_data', tmp_path / 'protected/test_data')
    namespace = {}
    exec(compile(relocate(correct_verifier(source), tmp_path), '<verifier>', 'exec'), namespace)
    return tmp_path, namespace


def test_instruction_contract_is_explicit_and_idempotent():
    original = 'Solve this puzzle.\n'
    corrected = supplement_instruction(original)
    for expected in ['read_puzzle(filename)', 'write_solution(board, filename)',
                     'in\n  place', 'import side effect', 'no particular main']:
        assert expected in corrected
    assert corrected.startswith(original.rstrip())
    assert supplement_instruction(corrected) == corrected


def test_only_three_original_test_bodies_change(source):
    corrected = correct_verifier(source)
    before = {n.name: ast.dump(n) for n in ast.parse(source).body
              if isinstance(n, ast.FunctionDef)}
    after = {n.name: ast.dump(n) for n in ast.parse(corrected).body
             if isinstance(n, ast.FunctionDef)}
    assert len([name for name in after if name.startswith('test_')]) == 22
    for name, body in before.items():
        if name not in CASES:
            assert after[name] == body
    assert 'main.__globals__' not in corrected
    assert correct_verifier(corrected) == corrected


def test_unknown_verifier_fails_closed():
    with pytest.raises(ValueError, match='three puzzle tests'):
        correct_verifier('def test_other(): pass\n')


def test_reference_solves_all_three_without_main(trial):
    root, namespace = trial
    shell = (CACHE / 'solution/solve.sh').read_text()
    code = shell.split("<< 'PYTHON_SCRIPT'\n", 1)[1].split('\nPYTHON_SCRIPT', 1)[0]
    # Keep only the public solver API. main is intentionally absent, proving
    # the correction no longer depends on a reference-specific CLI function.
    code = code.split('\ndef main():', 1)[0]
    (root / 'app/sudoku_solver.py').write_text(code)
    for name in CASES:
        namespace[name]()


@pytest.mark.parametrize('case', CASES)
def test_missing_solver_is_failure(trial, case):
    _, namespace = trial
    with pytest.raises(AssertionError, match='sudoku_solver.py is missing'):
        namespace[case]()


def test_missing_fixture_is_failure(trial):
    root, namespace = trial
    (root / 'app/sudoku_solver.py').write_text('')
    (root / 'protected/test_data/easy_puzzle.txt').unlink()
    with pytest.raises(AssertionError, match='fixture is missing'):
        namespace[CASES[0]]()


@pytest.mark.parametrize('case', CASES)
def test_other_valid_grid_is_rejected(trial, case):
    root, namespace = trial
    solved = (CACHE / 'environment/test_data/partial_filled.txt').read_text().split()
    # Digit permutation preserves every Sudoku rule but changes given clues.
    other = [[int(digit) % 9 + 1 for digit in row] for row in solved]
    assert namespace['validate_sudoku_solution'](other)[0]
    code = (
        'def read_puzzle(filename):\n'
        "    return [[int(c) for c in row.strip()] for row in open(filename) if row.strip()]\n"
        'def solve_sudoku(board):\n'
        f'    board[:] = {other!r}\n'
        '    return True\n'
        'def write_solution(board, filename):\n'
        "    open(filename, 'w').write('\\n'.join(''.join(map(str, row)) for row in board))\n"
    )
    (root / 'app/sudoku_solver.py').write_text(code)
    with pytest.raises(AssertionError, match='clues were changed'):
        namespace[case]()


def test_already_solved_requires_output_file(trial):
    root, namespace = trial
    (root / 'app/sudoku_solver.py').write_text(
        'def read_puzzle(filename): return []\n'
        'def solve_sudoku(board): return True\n'
        'def write_solution(board, filename): pass\n'
    )
    with pytest.raises(AssertionError, match='solution was not written'):
        namespace[CASES[2]]()
