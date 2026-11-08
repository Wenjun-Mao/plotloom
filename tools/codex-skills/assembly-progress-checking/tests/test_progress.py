import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from progress import report, sha


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        def item(name, text):
            p = self.base / name
            p.write_text(text)
            return {'file': name, 'sha256': sha(p)}
        self.source = item('source', 'source-v1')
        self.media = item('media', 'media-v1')
        self.receipt = item('receipt', 'proof-v1')
        self.selection = item('selection', 'selected-v1')
        self.m = {'source': {**self.source, 'episodes': [{'id': 'E1', 'segments': ['a', 'b']}]},
                  'technical': [{'segmentId': 'a', 'status': 'PASS', 'media': self.media,
                                 'receipt': self.receipt}],
                  'selections': [{'segmentId': 'a', 'media': self.media, 'evidence': self.selection}]}

    def test_ordered_gaps_and_separate_status(self):
        row = report(self.m, self.base)['episodes'][0]
        self.assertEqual(row['technicalGaps'], ['b'])
        self.assertEqual(row['selectionGaps'], ['b'])
        self.assertEqual([r['segmentId'] for r in row['segments']], ['a', 'b'])

    def test_stale_receipt_and_removed_selected_file(self):
        (self.base / 'receipt').write_text('changed')
        (self.base / 'media').unlink()
        row = report(self.m, self.base)['episodes'][0]
        self.assertEqual(row['technicalCovered'], 0)
        self.assertEqual(row['selectedCovered'], 0)

    def test_source_change_and_duplicates(self):
        m = copy.deepcopy(self.m)
        m['selections'].append(copy.deepcopy(m['selections'][0]))
        with self.assertRaises(ValueError):
            report(m, self.base)
        (self.base / 'source').write_text('changed')
        with self.assertRaises(ValueError):
            report(self.m, self.base)

    def test_reordered_selection_rejected(self):
        m = copy.deepcopy(self.m)
        m['selections'] = [{**m['selections'][0], 'segmentId': 'b'}, m['selections'][0]]
        with self.assertRaises(ValueError):
            report(m, self.base)

    def test_stale_export_not_reused(self):
        m = copy.deepcopy(self.m)
        m['source']['episodes'][0]['segments'] = ['a']
        evidence = self.base / 'decision'
        evidence.write_text('decision')
        m['selections'][0]['evidence'] = {'file': 'decision', 'sha256': sha(evidence)}
        (self.base / 'selection').write_text(json.dumps({'selections': m['selections']}))
        self.selection = {'file': 'selection', 'sha256': sha(self.base / 'selection')}
        m['exports'] = [{'episodeId': 'E1', 'sourceSha256': self.source['sha256'],
                         'selectionSha256': self.selection['sha256'], 'selection': self.selection,
                         'receipt': self.receipt, 'media': self.media, 'segments': ['a'], 'proofs': []}]
        self.assertTrue(report(m, self.base)['exports'][0]['bindingsCurrent'])
        other = self.base / 'other'
        other.write_text('other media')
        changed = copy.deepcopy(m)
        changed['selections'][0]['media'] = {'file': 'other', 'sha256': sha(other)}
        self.assertFalse(report(changed, self.base)['exports'][0]['bindingsCurrent'])
        (self.base / 'receipt').write_text('stale')
        self.assertFalse(report(m, self.base)['exports'][0]['bindingsCurrent'])


if __name__ == '__main__':
    unittest.main()
