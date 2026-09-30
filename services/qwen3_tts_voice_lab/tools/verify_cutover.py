"""Read-only post-restart preservation proof against an exact idle backup."""

import argparse
import hashlib
import json
import sqlite3
import urllib.request

from preserve_cutover import rows
from pathlib import Path


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''): digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--backup-root', type=Path, required=True)
    parser.add_argument('--api-origin', required=True)
    args = parser.parse_args()
    baseline = rows(args.backup_root / 'voice_lab.sqlite3')
    metadata = json.loads((args.backup_root / 'preservation.json').read_text())
    with sqlite3.connect(args.data_root / 'voice_lab.sqlite3') as current:
        assert current.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert current.execute('PRAGMA user_version').fetchone()[0] == 3
        for table, value in baseline.items():
            columns = ','.join(f'"{column}"' for column in value['columns'])
            for old in value['rows']:
                live = current.execute(f'SELECT {columns} FROM "{table}" WHERE "{value["columns"][0]}"=?', (old[0],)).fetchone()
                assert live == old, f'preservation.changed:{table}:{old[0]}'
    assert all(sha(args.data_root / path) == digest for path, digest in metadata['wavHashes'].items())
    voices = baseline['voices']; columns = voices['columns']
    for value in voices['rows']:
        voice = dict(zip(columns, value))
        for kind in ('source', 'h3'):
            with urllib.request.urlopen(f'{args.api_origin}/api/voices/{voice["id"]}/audio?kind={kind}', timeout=10) as response:
                assert hashlib.sha256(response.read()).hexdigest() == voice[f'{kind}_sha256']
    print(json.dumps({'schemaVersion': 3, 'integrity': 'ok',
        'oldTableCounts': {table: len(value['rows']) for table, value in baseline.items()},
        'unchangedWavs': len(metadata['wavHashes']), 'unchangedPublishedVoices': len(voices['rows'])}))


if __name__ == '__main__': main()
