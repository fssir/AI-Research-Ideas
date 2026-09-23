"""CC0-1.0. Additional regression tests; no real Idea or research execution."""
import copy
import json
import unittest
from unittest.mock import patch
import test_platform as f

c, p = f.c, f.p


class AuditBoundaryTests(unittest.TestCase):
    def test_creation_time_requires_seconds(self):
        with self.assertRaises(ValueError):
            c.parse_time('2026-09-22T12:34+03:00')

    def test_cached_blob_still_respects_each_read_limit(self):
        snap = f.snapshot({'x.md': b'12345'})
        self.assertEqual(snap.read('x.md', 10), b'12345')
        # Model an API entry with omitted/unknown size; actual bytes remain known.
        entry = snap.entries['x.md']
        snap.entries['x.md'] = c.Entry(entry.sha, entry.mode, 0)
        with self.assertRaises(ValueError):
            snap.read('x.md', 2)

    def test_aggregate_markdown_rejected_before_merge(self):
        base = f.snapshot({f.DIR + '/a.md': b'a' * 20})
        head = base.changed({f.DIR + '/b.md': b'b' * 20})
        with patch.object(c, 'MAX_TEXT', 30):
            with self.assertRaises(ValueError):
                c.authorize(base, base, head, f.registry(), f.USER, f.BODY)

    def test_exact_aggregate_markdown_limit_allowed(self):
        base = f.snapshot({f.DIR + '/a.md': b'a' * 20})
        head = base.changed({f.DIR + '/b.md': b'b' * 10})
        with patch.object(c, 'MAX_TEXT', 30):
            self.assertTrue(c.authorize(base, base, head, f.registry(), f.USER, f.BODY))

    def test_unchanged_markdown_counts_toward_limit(self):
        base = f.snapshot({f.DIR + '/a.md': b'a' * 40, f.DIR + '/code/a.py': 'old'})
        head = base.changed({f.DIR + '/code/a.py': b'new'})
        with patch.object(c, 'MAX_TEXT', 30):
            with self.assertRaises(ValueError):
                c.authorize(base, base, head, f.registry(), f.USER, f.BODY)

    def test_checkbox_inside_code_is_not_consent(self):
        self.assertFalse(c.consented('```text\n' + f.BODY + '\n```'))

    def test_checkbox_inside_comment_is_not_consent(self):
        self.assertFalse(c.consented('<!--\n' + f.BODY + '\n-->'))

    def test_issue_consent_must_be_in_declaration(self):
        obj = f.issue()
        obj['body'] = obj['body'].replace('Explore irrational decimal expansions.', 'Example:\n' + f.BODY)
        obj['body'] = obj['body'].rsplit(f.BODY, 1)[0] + '- [ ] ' + c.CONSENT
        with self.assertRaises(ValueError):
            c.allocate(f.registry(), obj, f.NOW, 'test/library')

    def test_duplicate_form_sections_rejected(self):
        obj = f.issue()
        obj['body'] += '\n\n### Idea title\n\nOverridden title'
        with self.assertRaises(ValueError):
            c.allocate(f.registry(), obj, f.NOW, 'test/library')

    def test_newline_in_title_rejected(self):
        obj = f.issue()
        obj['body'] = obj['body'].replace('A mathematical idea', 'Title\nAnother title')
        with self.assertRaises(ValueError):
            c.allocate(f.registry(), obj, f.NOW, 'test/library')

    def test_api_unicode_size_consistency(self):
        # The accepted snapshot uses UTF-8 byte sizes, not character counts.
        snap = f.snapshot({f.DIR + '/README.md': '# 转子发动机\n\n研究燃烧。'})
        result = c.render_catalog(snap, f.registry(), f.NOW, 'test/library')
        self.assertIn('转子发动机', result[c.INDEX].decode())


class MergeBoundaryTests(unittest.TestCase):
    def test_new_draft_is_not_merged(self):
        class Fake:
            calls = []
            def request(self, path, method='GET', data=None):
                self.calls.append((path, method))
                if path == '/pulls/1':
                    return {'state': 'open', 'draft': True, 'base': {'ref': 'main'}, 'head': {'sha': 'h'}}
                if path == '/git/ref/heads/main': return {'object': {'sha': 'base'}}
                if method == 'PUT': return {'merged': True, 'sha': 'bad'}
                raise AssertionError(path)
        api = Fake()
        self.assertFalse(p.API.merge(api, {'number': 1, 'head': {'sha': 'h'}}, 'base'))
        self.assertFalse(any(method == 'PUT' for _, method in api.calls))

    def test_retargeted_pr_is_not_merged(self):
        class Fake:
            calls = []
            def request(self, path, method='GET', data=None):
                self.calls.append((path, method))
                if path == '/pulls/1':
                    return {'state': 'open', 'base': {'ref': 'other'}, 'head': {'sha': 'h'}}
                if path == '/git/ref/heads/main': return {'object': {'sha': 'base'}}
                if method == 'PUT': return {'merged': True, 'sha': 'bad'}
                raise AssertionError(path)
        api = Fake()
        self.assertFalse(p.API.merge(api, {'number': 1, 'head': {'sha': 'h'}}, 'base'))
        self.assertFalse(any(method == 'PUT' for _, method in api.calls))

    def test_non_main_pr_not_processed(self):
        class Fake:
            repo = 'test/library'
            def request(self, path, method='GET', data=None):
                return {'number': 1, 'state': 'open', 'draft': False, 'base': {'ref': 'other'},
                        'head': {'sha': 'h', 'ref': 'topic', 'repo': {'full_name': 'test/library'}}, 'user': f.USER, 'body': f.BODY}
            def main(self): raise AssertionError('A non-main PR must not enter main publication')
        p.process_contributions(Fake(), [{'number': 1, 'user': f.USER, 'head': {'ref': 'topic'}, 'draft': False}])


if __name__ == '__main__':
    unittest.main(verbosity=2)
