"""Local correction for the pinned blockchain verifier's inconsistent oracle.

The upstream cache is never changed. Callers supply its verified task directory
and the already relocated verifier source. Expected data is derived from that
original fixture, never from the agent's mutable working copy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


def _first_error(ledger: list[dict]) -> tuple[str, str, str]:
    previous = '0' * 64
    for transaction in ledger:
        if transaction['previous_hash'] != previous:
            return transaction['transaction_id'], 'previous_hash', transaction['previous_hash']
        payload = ''.join(str(transaction[key]) for key in (
            'transaction_id', 'sender', 'receiver', 'amount', 'timestamp', 'previous_hash'))
        calculated = hashlib.sha256(payload.encode()).hexdigest()
        if calculated != transaction['current_hash']:
            return transaction['transaction_id'], 'current_hash', transaction['current_hash']
        previous = transaction['current_hash']
    raise ValueError('Original blockchain fixture contains no hash integrity error')


def correct_verifier(source: str, task_dir: Path, workspace: Path) -> str:
    """Preserve upstream checks 1–9, replace check 10 and require intact input."""
    original = (task_dir / 'environment/blockchain_ledger.json').read_bytes()
    expected = _first_error(json.loads(original))
    checksum = hashlib.sha256(original).hexdigest()
    # Fail closed if the pinned verifier changes instead of silently leaving its
    # contradictory assertion active or replacing unrelated upstream checks.
    pattern = (
        r'(?m)^def test_10_solution_accuracy\(result_content\):\n'
        r'    assert result_content\[0\] == "tx_010"\n'
        r'    assert result_content\[1\] == "current_hash"[ \t]*(?:\n)?\Z'
    )
    replacement = (
        'def test_10_solution_accuracy(result_content):\n'
        f'    assert tuple(result_content) == {expected!r}, "Expected the first error in the original ledger"\n'
    )
    corrected, count = re.subn(pattern, lambda match: replacement, source)
    if count != 1:
        raise ValueError('Unrecognized upstream blockchain solution_accuracy assertion')
    ledger_path = str(workspace.resolve() / 'app/blockchain_ledger.json')
    return corrected + (
        '\n\ndef test_11_original_ledger_unchanged():\n'
        '    from pathlib import Path\n'
        '    import hashlib\n'
        f'    ledger = Path({ledger_path!r})\n'
        '    assert ledger.is_file(), "Original ledger file missing"\n'
        f'    assert hashlib.sha256(ledger.read_bytes()).hexdigest() == {checksum!r}, "Original ledger was modified"\n'
    )
