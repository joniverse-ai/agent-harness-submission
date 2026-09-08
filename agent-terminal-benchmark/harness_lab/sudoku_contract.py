"""Auditable local corrections to the pinned Sudoku instruction and verifier."""
from __future__ import annotations

import ast


SUPPLEMENT = """

Local clarification of the solver's public interface:
- sudoku_solver.py must be importable without running the CLI, exiting the process,
  or reading/writing the default puzzle files as an import side effect.
- read_puzzle(filename) reads the given path and returns a mutable 9-by-9 list of
  integer lists, with 0 representing an empty cell.
- solve_sudoku(board) uses recursive backtracking, modifies that same board in
  place, and returns True if solved or False if no solution exists. Preserve all
  nonzero clues, and accept an already solved valid board.
- write_solution(board, filename) writes that board to the given path as nine
  lines of nine digits without separators. Its return value is not prescribed.
- A main function with an if __name__ == '__main__' entry guard is recommended,
  but no particular main function or global input/output variable is required.
The existing requirement to report an unsolvable puzzle and exit still applies;
no exact error message or exception class is prescribed.
"""


def supplement_instruction(text: str) -> str:
    """Expose the I/O contract without leaking fixtures or reference solutions."""
    return text if SUPPLEMENT in text else text.rstrip() + SUPPLEMENT


_CASES = {
    'test_easy_puzzle_can_be_solved': ('easy_puzzle.txt', 10),
    'test_hard_puzzle_can_be_solved': ('hard_puzzle.txt', 30),
    'test_already_solved_puzzle': ('partial_filled.txt', 5),
}

_HELPER = '''

# Local Sudoku contract correction: validate every additional puzzle completely.
def _check_additional_sudoku_puzzle(filename, timeout):
    import sys
    solver_path = '/app/sudoku_solver.py'
    fixture_path = os.path.join('/protected/test_data', filename)
    assert os.path.isfile(solver_path), "Required sudoku_solver.py is missing"
    assert os.path.isfile(fixture_path), f"Required Sudoku fixture is missing: {filename}"
    puzzle_grid = read_sudoku_grid(fixture_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(solver_path, tmpdir)
        puzzle_path = os.path.join(tmpdir, 'puzzle.txt')
        solution_path = os.path.join(tmpdir, 'solution.txt')
        shutil.copy(fixture_path, puzzle_path)
        solver_script = os.path.join(tmpdir, 'solve.py')
        script = (
            "import sudoku_solver\\n"
            f"board = sudoku_solver.read_puzzle({puzzle_path!r})\\n"
            "assert sudoku_solver.solve_sudoku(board) is True, 'Puzzle was not solved'\\n"
            f"sudoku_solver.write_solution(board, {solution_path!r})\\n"
        )
        with open(solver_script, 'w') as stream:
            stream.write(script)
        result = subprocess.run([sys.executable, solver_script], cwd=tmpdir,
                                capture_output=True, text=True, timeout=timeout)
        assert result.returncode == 0, f"Sudoku solver failed: {result.stderr}"
        assert os.path.isfile(solution_path), "Additional puzzle solution was not written"
        grid = read_sudoku_grid(solution_path)
        valid, message = validate_sudoku_solution(grid)
        assert valid, f"Additional puzzle solution is invalid: {message}"
        matches, message = check_solution_matches_puzzle(puzzle_grid, grid)
        assert matches, f"Additional puzzle clues were changed: {message}"
'''


def correct_verifier(source: str) -> str:
    """Replace only the three extra-puzzle tests, retaining their names/count."""
    if '# Local Sudoku contract correction:' in source:
        return source
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in _CASES]
    if len(functions) != 3 or {node.name for node in functions} != set(_CASES):
        raise ValueError('Unexpected upstream Sudoku verifier: three puzzle tests required')
    lines = source.splitlines(keepends=True)
    for node in sorted(functions, key=lambda item: item.lineno, reverse=True):
        filename, timeout = _CASES[node.name]
        lines[node.lineno - 1:node.end_lineno] = [
            f'def {node.name}():\n',
            f'    _check_additional_sudoku_puzzle({filename!r}, {timeout})\n',
        ]
    return ''.join(lines) + _HELPER
