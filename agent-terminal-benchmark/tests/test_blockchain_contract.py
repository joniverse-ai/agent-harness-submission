"""Offline regressions for the explicitly corrected local blockchain contract."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from harness_lab.benchmark_source import relocate
from harness_lab.blockchain_contract import _first_error, correct_verifier


TASK = Path(__file__).resolve().parents[1] / '.benchmark-cache/detect-corrupted-blockchain-transaction'


def transaction(identifier, previous='0' * 64):
    item = dict(transaction_id=identifier, sender='alice', receiver='bob',
                amount=12, timestamp='2026-01-01', previous_hash=previous)
    item['current_hash'] = hashlib.sha256(''.join(str(value) for value in item.values()).encode()).hexdigest()
    return item


def test_synthetic_hash_error_ordering():
    first = transaction('one')
    second = transaction('two', first['current_hash'])
    second['current_hash'] = 'f' * 64
    third = transaction('three', 'a' * 64)
    assert _first_error([first, second, third]) == ('two', 'current_hash', 'f' * 64)
    second['previous_hash'] = 'b' * 64
    assert _first_error([first, second, third]) == ('two', 'previous_hash', 'b' * 64)
    first['previous_hash'] = 'c' * 64
    assert _first_error([first, second]) == ('one', 'previous_hash', 'c' * 64)


@pytest.mark.parametrize('ledger', [[], [transaction('valid')]])
def test_valid_ledger_rejected(ledger):
    with pytest.raises(ValueError, match='no hash integrity error'):
        _first_error(ledger)


def task_material():
    # The integration fixture is the unmodified, SHA-verified upstream cache.
    # Unit tests above remain useful in a checkout before sources are fetched.
    if not (TASK / 'environment/blockchain_ledger.json').exists():
        pytest.skip('Fetch pinned benchmark sources to run upstream integration regressions')
    original = (TASK / 'environment/blockchain_ledger.json').read_bytes()
    manifest = json.loads((TASK.parents[1] / 'benchmark/tasks.json').read_text())
    spec = next(task for task in manifest['tasks'] if task['name'] == TASK.name)
    for relative in ('environment/blockchain_ledger.json', 'tests/test_outputs.py'):
        record = next(record for record in spec['source_files'] if record['path'] == relative)
        content = (TASK / relative).read_bytes()
        assert len(content) == record['size_bytes']
        assert hashlib.sha256(content).hexdigest() == record['sha256']
    return original, (TASK / 'tests/test_outputs.py').read_text()


@pytest.mark.parametrize('answer_kind', ['correct', 'old_id', 'later_error', 'wrong_value', 'replaced_ledger'])
def test_original_fixture_verification(tmp_path, answer_kind):
    original, source = task_material()
    workspace = tmp_path / 'workspace'
    (workspace / 'app').mkdir(parents=True)
    ledger = json.loads(original)
    assert len(ledger) == 120
    expected = _first_error(ledger)
    assert expected[:2] == ('tx_0067', 'current_hash')
    answer = list(expected)
    ledger_bytes = original
    if answer_kind == 'old_id':
        answer[0] = 'tx_010'
    elif answer_kind == 'later_error':
        answer = ['tx_0068', 'previous_hash', ledger[68]['previous_hash']]
    elif answer_kind == 'wrong_value':
        answer[2] = ledger[68]['previous_hash']
    elif answer_kind == 'replaced_ledger':
        # Even a replacement retaining the correct error must not pass.
        ledger_bytes = json.dumps(ledger[:68]).encode()
    (workspace / 'app/blockchain_ledger.json').write_bytes(ledger_bytes)
    (workspace / 'app/result.txt').write_text(','.join(answer))
    relocated = relocate(source, workspace)
    corrected = correct_verifier(relocated, TASK, workspace)
    assert corrected.split('def test_10_solution_accuracy')[0] == relocated.split('def test_10_solution_accuracy')[0]
    assert str(TASK) not in corrected
    verifier = tmp_path / 'test_corrected_outputs.py'
    verifier.write_text(corrected)
    result = subprocess.run([sys.executable, '-I', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                             '--rootdir', str(tmp_path), str(verifier)],
                            capture_output=True, text=True, timeout=30,
                            env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'})
    assert result.returncode == (0 if answer_kind == 'correct' else 1), result.stdout + result.stderr
    if answer_kind == 'correct':
        assert '11 passed' in result.stdout
        assert (workspace / 'app/blockchain_ledger.json').read_bytes() == original
    elif answer_kind == 'replaced_ledger':
        assert 'test_11_original_ledger_unchanged' in result.stdout
    assert (TASK / 'environment/blockchain_ledger.json').read_bytes() == original


def test_unrecognized_upstream_assertion_rejected(tmp_path):
    _, source = task_material()
    with pytest.raises(ValueError, match='Unrecognized upstream'):
        correct_verifier(source.replace('"tx_010"', '"different"'), TASK, tmp_path)
