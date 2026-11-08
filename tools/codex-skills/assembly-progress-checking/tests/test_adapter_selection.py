import copy
import tempfile
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from plotloom_adapter import choose_selections
from progress import sha


class AdapterSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'story'
        self.source.write_text('current')
        self.candidates = {}
        for sid in ['a', 'b']:
            packet = self.base / sid
            packet.mkdir()
            review = packet / 'clip-review.json'
            review.write_text('selected ' + sid)
            media = packet / 'media'
            media.write_text('media ' + sid)
            self.candidates[sid] = [({'file': media, 'nativeSha256': sha(media)}, review)]
        self.chosen = {'storyboardFile': str(self.source), 'storyboardSha256': sha(self.source), 'clips': []}

    def row(self, sid):
        clip, review = self.candidates[sid][0]
        return {'segmentId': sid, 'packet': str(review.parent), 'reviewSha256': sha(review),
                'nativeSha256': clip['nativeSha256']}

    def test_empty_partial_and_snapshot_binding(self):
        rows, errors = choose_selections(['a', 'b'], self.candidates, self.chosen, self.source)
        self.assertEqual(rows, [])
        self.assertEqual(errors, [])
        self.chosen['clips'] = [self.row('b')]
        rows, errors = choose_selections(['a', 'b'], self.candidates, self.chosen, self.source)
        self.assertEqual([r['segmentId'] for r in rows], ['b'])
        self.chosen['clips'][0]['nativeSha256'] = 'stale'
        self.assertEqual(choose_selections(['a', 'b'], self.candidates, self.chosen, self.source)[0], [])

    def test_conflict_and_duplicate_or_reordered_rows(self):
        self.candidates['a'].append(self.candidates['a'][0])
        rows, errors = choose_selections(['a', 'b'], self.candidates, None, self.source)
        self.assertEqual([r['segmentId'] for r in rows], ['b'])
        self.assertIn('conflicting', errors[0])
        self.chosen['clips'] = [self.row('b'), self.row('a')]
        with self.assertRaises(ValueError):
            choose_selections(['a', 'b'], self.candidates, self.chosen, self.source)
        self.chosen['clips'] = [self.row('b'), self.row('b')]
        with self.assertRaises(ValueError):
            choose_selections(['a', 'b'], self.candidates, self.chosen, self.source)


if __name__ == '__main__':
    unittest.main()
