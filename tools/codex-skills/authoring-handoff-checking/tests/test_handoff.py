import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import digest, evidence, pin, save
from review_results import ASPECTS, validate


class ReportContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.json'
        self.source.write_text(json.dumps({
            'outline': {'hook': 'The drawer is closed'},
            'script': {'opening': 'The drawer is closed', 'speaker': 'A', 'line': 'Stay here.'},
            'cut': {'view': 'A looks away; drawer offscreen', 'state': 'drawer remains closed', 'speaker': 'A', 'line': 'Stay here.'}
        }))
        self.case_file = self.root / 'case.json'
        case = {'schemaVersion': 1, 'skillVersion': '0.1.0', 'caseId': 'E01',
                'sources': {'s': pin(self.source)}, 'evidence': [evidence('s', '/'+x, x) for x in ('outline', 'script', 'cut')]}
        save(self.case_file, case)
        self.report = {'schemaVersion': 1, 'skillVersion': '0.1.0', 'caseId': 'E01', 'caseSha256': digest(self.case_file),
                       'reviewer': {'model': 'test', 'reasoning': 'high'}, 'decision': 'pass', 'summary': 'Scoped comparison',
                       'checks': [{'aspect': a, 'status': 'pass', 'notes': 'Compared', 'evidence': [{'id': 'script', 'pointer': ''}, {'id': 'cut', 'pointer': ''}]} for a in ASPECTS],
                       'findings': [], 'limitations': []}

    def tearDown(self):
        self.tmp.cleanup()

    def change_source(self, section, field, value):
        source = json.loads(self.source.read_text())
        source[section][field] = value
        self.source.write_text(json.dumps(source))
        case = json.loads(self.case_file.read_text())
        case['sources']['s'] = pin(self.source)
        self.case_file.write_text(json.dumps(case))
        self.report['caseSha256'] = digest(self.case_file)

    def finding(self, aspect, claim, left, right):
        r = copy.deepcopy(self.report)
        r['decision'] = 'fail'
        next(x for x in r['checks'] if x['aspect'] == aspect)['status'] = 'fail'
        r['findings'] = [{'aspect': aspect, 'severity': 'material', 'origin': 'source', 'claim': claim,
                          'evidence': [{'id': left[0], 'pointer': left[1]}, {'id': right[0], 'pointer': right[1]}]}]
        return r

    def test_current_case_and_offscreen_cutaway_can_pass(self):
        self.assertTrue(validate(self.case_file, self.report))

    def test_stale_source_fails(self):
        self.source.write_text(self.source.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'stale source'):
            validate(self.case_file, self.report)

    def test_hook_mismatch_finding_needs_both_sides(self):
        self.change_source('script', 'opening', 'The drawer opens')
        r = self.finding('hook', 'Opening contradicts the hook', ('outline', '/hook'), ('script', '/opening'))
        self.assertTrue(validate(self.case_file, r))
        r['findings'][0]['evidence'].pop()
        with self.assertRaisesRegex(ValueError, 'two evidence'):
            validate(self.case_file, r)

    def test_dialogue_mismatch_finding_requires_exact_valid_pointer(self):
        self.change_source('cut', 'speaker', 'B')
        r = self.finding('dialogue', 'Speaker or line differs', ('script', '/speaker'), ('cut', '/speaker'))
        self.assertTrue(validate(self.case_file, r))
        r['findings'][0]['evidence'][1]['pointer'] = '/missing'
        with self.assertRaises(KeyError):
            validate(self.case_file, r)

    def test_needs_review_cannot_hide_material_failure(self):
        r = self.finding('dialogue', 'Speaker differs', ('script', '/speaker'), ('cut', '/speaker'))
        r['decision'] = 'needs_review'
        next(x for x in r['checks'] if x['aspect'] == 'hook')['status'] = 'needs_review'
        with self.assertRaisesRegex(ValueError, 'cannot hide a material failure'):
            validate(self.case_file, r)

    def test_failed_check_and_material_finding_must_share_aspect(self):
        r = self.finding('dialogue', 'Speaker differs', ('script', '/speaker'), ('cut', '/speaker'))
        r['findings'][0]['aspect'] = 'hook'
        with self.assertRaisesRegex(ValueError, 'match by aspect'):
            validate(self.case_file, r)

    def test_pass_cannot_hide_uncertainty(self):
        self.report['checks'][0]['status'] = 'needs_review'
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            validate(self.case_file, self.report)


if __name__ == '__main__':
    unittest.main()
