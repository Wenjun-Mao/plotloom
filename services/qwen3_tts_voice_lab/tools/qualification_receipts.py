"""Exclusive one-operation receipts for operator qualification, not GPU leases."""

import json
import os
from pathlib import Path


def claim_receipt(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ValueError('qualification.receipt_exists_no_replay') from error
    with os.fdopen(descriptor, 'w') as receipt:
        json.dump({'status': 'claimed_before_preflight', 'generationCalls': 0}, receipt)
        receipt.write('\n')
        receipt.flush()
        os.fsync(receipt.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    # Failed preflight leaves the claim intact. Never erase it to grant another
    # invocation an implicit dispatch/restart; use an explicitly reviewed path.
