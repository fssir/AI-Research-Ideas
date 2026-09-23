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


class InputAndPreflightTests(unittest.TestCase):
    def test_fenced_form_headings_are_not_parsed(self):
        obj = f.issue()
        obj['body'] = obj['body'].replace('Explore irrational decimal expansions.', 'Text\n```md\n### Idea title\nExample only\n```')
        _, files = c.allocate(f.registry(), obj, f.NOW, 'test/library')
        self.assertIn('### Idea title\nExample only', next(iter(files.values())).decode())

    def test_actual_consent_after_example_accepted(self):
        self.assertTrue(c.consented('```\n' + f.BODY + '\n```\n' + f.BODY))

    def test_indented_checkbox_is_not_consent(self):
        self.assertFalse(c.consented('    ' + f.BODY))

    def test_malformed_markup_remains_bounded(self):
        # Previously repeated unmatched '[' or '<' caused excessive regex work.
        text = '[' * 30000 + '<' * 30000
        self.assertEqual(len(c.plain(text)), len(text))

    def test_data_and_results_get_separate_links(self):
        snap = f.snapshot({f.DIR + '/README.md': '# Title', f.DIR + '/data/a.csv': 'x', f.DIR + '/results/a.csv': 'y'})
        text = c.render_catalog(snap, f.registry(), f.NOW, 'test/library')[c.HUMAN].decode()
        self.assertIn('/data/)', text)
        self.assertIn('/results/)', text)

    def test_catalog_limit_is_checked(self):
        snap = f.snapshot({f.DIR + '/README.md': '# Title\nContent'})
        with patch.object(c, 'MAX_INDEX', 30):
            with self.assertRaises(ValueError):
                c.render_catalog(snap, f.registry(), f.NOW, 'test/library')

    def test_bad_pr_does_not_block_good_pr(self):
        api = ContributionAPI()
        p.process_contributions(api, api.prs)
        self.assertFalse(api.checks['bad'])
        self.assertTrue(api.checks['good'])
        self.assertEqual(api.merged, [2])

    def test_index_preflight_prevents_bad_content_merging(self):
        api = ContributionAPI()
        with patch.object(c, 'MAX_INDEX', 30):
            p.process_contributions(api, [api.prs[1]])
        self.assertFalse(api.checks['good'])
        self.assertEqual(api.merged, [])

    def test_transient_api_error_not_hidden(self):
        api = ContributionAPI()
        api.snapshot = lambda sha: (_ for _ in ()).throw(p.ApiError(503, 'service unavailable'))
        with self.assertRaises(p.ApiError):
            p.process_contributions(api, [api.prs[1]])
        self.assertEqual(api.merged, [])

    def test_consent_changed_before_merge_stops(self):
        class API:
            def request(self, path, method='GET', data=None):
                if method == 'PUT': raise AssertionError('must not merge withdrawn consent')
                return {'state': 'open', 'base': {'ref': 'main'}, 'head': {'sha': 'h'}, 'body': 'withdrawn'}
        self.assertFalse(p.API.merge(API(), {'number': 1, 'head': {'sha': 'h'}, 'body': f.BODY}, 'base'))

    def test_valid_merge_still_works(self):
        pr = {'number': 1, 'state': 'open', 'base': {'ref': 'main'}, 'head': {'sha': 'h'}, 'body': f.BODY, 'user': f.USER}
        class API:
            def request(self, path, method='GET', data=None):
                if path == '/pulls/1': return pr
                if path == '/git/ref/heads/main': return {'object': {'sha': 'base'}}
                if method == 'PUT':
                    assert data['sha'] == 'h'
                    return {'merged': True, 'sha': 'merged'}
                raise AssertionError(path)
        self.assertTrue(p.API.merge(API(), pr, 'base'))


class ContributionAPI:
    repo = 'test/library'
    def __init__(self):
        self.current = f.snapshot({c.REGISTRY: c.dump(f.registry()), f.DIR + '/README.md': '# Original',
            '.github/ori/config/maintainers.json': c.dump({'maintainers': []})})
        self.head = self.current.changed({f.DIR + '/README.md': b'# Updated\n\nActual idea'})
        self.checks, self.merged = {}, []
        self.prs = [{'number': n, 'state': 'open', 'draft': False, 'base': {'ref': 'main'},
             'user': f.USER, 'body': f.BODY, 'head': {'sha': sha, 'ref': 'topic', 'repo': {'full_name': self.repo}}}
            for n, sha in [(1, 'bad'), (2, 'good')]]
    def request(self, path, method='GET', data=None):
        if path.startswith('/pulls/'):
            return self.prs[int(path.rsplit('/', 1)[-1]) - 1]
        if path.startswith('/compare/'):
            return {'merge_base_commit': {'sha': 'base'}}
        raise AssertionError(path)
    def main(self): return 'base', self.current
    def snapshot(self, sha):
        if sha == 'bad': raise ValueError('truncated malicious/oversize tree')
        return self.current if sha == 'base' else self.head
    def check(self, sha, ok, summary): self.checks[sha] = ok
    def merge(self, pr, base_sha): self.merged.append(pr['number']); return True


if __name__ == '__main__':
    unittest.main(verbosity=2)
