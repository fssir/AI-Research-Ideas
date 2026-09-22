"""CC0-1.0. Regression tests use synthetic in-memory Git trees, not research results."""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import catalog as c
import publisher as p

NOW = '2026-09-22T12:34:56+03:00'
LATER = '2026-09-22T12:35:00+03:00'
DIR = 'ideas/000001_20260908_151012_GMTp3'
BODY = '- [x] ' + c.CONSENT
USER = {'id': 10, 'login': 'alice'}


def snapshot(files, modes=None):
    modes = modes or {}
    data = {k: v.encode() if isinstance(v, str) else v for k, v in files.items()}
    store = {c.blob_sha(v): v for v in data.values()}
    return c.Snapshot({k: c.Entry(c.blob_sha(v), modes.get(k, '100644'), len(v)) for k, v in data.items()}, store.__getitem__)


def registry():
    return {'schema_version': 3, 'timezone': 'GMT+3', 'utc_offset': '+03:00', 'next_id': 2, 'ideas': {'ORI-000001': {
        'owner': 'alice', 'owner_id': 10, 'created_at': '2026-09-08T15:10:12+03:00', 'path': DIR, 'status': 'active', 'source_issue': 4, 'license': 'CC0-1.0'}}}


def issue(number=9):
    return {'number': number, 'title': '[NEW IDEA] human label', 'user': USER, 'node_id': 'I_test', 'state': 'open',
        'body': '### Idea title\n\nA mathematical idea\n\n### Idea description\n\nExplore irrational decimal expansions.\n\n### Optional prompt for AI\n\n_No response_\n\n### Declaration\n\n' + BODY}


class CatalogTests(unittest.TestCase):
    def build(self, files, reg=None):
        return c.render_catalog(snapshot(files), reg or registry(), NOW, 'test/library')

    def test_one_markdown_no_metadata(self):
        out = self.build({DIR + '/idea.md': '# Title\n\nOnly an idea.'})
        self.assertEqual(json.loads(out[c.INDEX])['count'], 1)

    def test_full_text_all_markdown_uppercase(self):
        out = self.build({DIR + '/README.md': '# Main\n\n## Idea\n\nFirst.', DIR + '/paper/FULL.MD': '# Paper\n\nunique-second-document-term'})
        row = json.loads(out[c.INDEX])['ideas'][0]
        self.assertEqual(len(row['documents']), 2)
        self.assertIn('unique-second-document-term', str(row['documents']))
        self.assertEqual(row['title'], 'Main')

    def test_long_text_not_silently_cut(self):
        text = '# Title\n' + 'x ' * 100000 + 'UNIQUE_TRAILING_TOKEN'
        out = self.build({DIR + '/idea.md': text})
        self.assertIn('UNIQUE_TRAILING_TOKEN', out[c.INDEX].decode())

    def test_noop_is_identical(self):
        snap = snapshot({DIR + '/README.md': '# Title\n\nA mathematical idea.'})
        first = c.render_catalog(snap, registry(), NOW, 'test/library')
        updated = snap.changed(first)
        second = c.render_catalog(updated, json.loads(first[c.REGISTRY]), LATER, 'test/library')
        self.assertEqual(first, second)
        self.assertEqual(p.updates_diff(updated, second), {})

    def test_real_edit_changes_index(self):
        snap = snapshot({DIR + '/README.md': '# Title\n\nInitial.'})
        first = c.render_catalog(snap, registry(), NOW, 'test/library')
        new = snap.changed(first).changed({DIR + '/README.md': b'# Title\n\nUpdated.'})
        second = c.render_catalog(new, registry(), LATER, 'test/library')
        self.assertEqual(json.loads(second[c.INDEX])['generated_at'], LATER)

    def test_deleted_tombstone_preserved(self):
        out = self.build({})
        reg = json.loads(out[c.REGISTRY]); item = reg['ideas']['ORI-000001']
        self.assertEqual(item['status'], 'deleted')
        self.assertEqual(reg['next_id'], 2)
        again = c.render_catalog(snapshot(out), reg, LATER, 'test/library')
        self.assertEqual(out, again)

    def test_deleted_id_cannot_be_reactivated(self):
        reg = registry(); reg['ideas']['ORI-000001']['status'] = 'deleted'
        with self.assertRaises(ValueError):
            self.build({DIR + '/README.md': '# Restored'}, reg)

    def test_unknown_folder_fails(self):
        with self.assertRaises(ValueError):
            self.build({'ideas/999999_20260922_123456_GMTp3/a.md': '# Unknown'})

    def test_filename_links_encoded(self):
        out = self.build({DIR + '/README.md': '# A [link] | <script>\n\n## Idea\n\nA | B', DIR + '/code/x.py': 'x=1', DIR + '/paper/report.md': '# Manuscript'})
        human = out[c.HUMAN].decode()
        self.assertNotIn('<script>', human)
        self.assertIn('\\[link\\]', human)
        self.assertIn('Code', human)
        self.assertIn('Paper', human)

    def test_gene_not_in_generalization(self):
        fields, keywords = c.fields_keywords('generalization of mathematical sequences', 'Generalization')
        self.assertNotIn('Biology / Medicine', fields)
        self.assertNotIn('gene', keywords)

    def test_and_not_keyword(self):
        _, words = c.fields_keywords('and ' * 50 + 'irrational decimal prediction', 'Irrational')
        self.assertNotIn('and', words)

    def test_chinese_fields(self):
        fields, _ = c.fields_keywords('转子发动机的燃烧研究以及无人机推进', '转子发动机')
        self.assertIn('Mechanical / Aerospace Engineering', fields)

    def test_summary_skips_author_header(self):
        raw = '# Title\n\n**Author:** @alice\n\n## Idea\n\nThe actual idea.\n\n## Results\nOther data.'
        self.assertEqual(c.excerpt(raw), 'The actual idea.')

    def test_source_hash_verified(self):
        bad = c.Snapshot({'x.md': c.Entry('0' * 40)}, lambda _: b'Not this hash')
        with self.assertRaises(ValueError): bad.read('x.md')

    def test_markdown_size_fails_visibly(self):
        with self.assertRaises(ValueError):
            self.build({DIR + '/README.md': b'x' * (c.MAX_MD + 1)})

    def test_registry_creation_time_cannot_change(self):
        reg = registry(); reg['ideas']['ORI-000001']['created_at'] = NOW
        with self.assertRaises(ValueError): c.validate_registry(reg)

    def test_registry_no_id_reuse(self):
        reg = registry(); reg['next_id'] = 1
        with self.assertRaises(ValueError): c.validate_registry(reg)

    def test_timezone(self):
        self.assertEqual(c.parse_time(NOW).utcoffset().total_seconds(), 10800)
        with self.assertRaises(ValueError): c.parse_time('2026-09-22T12:34:56+08:00')


class AllocationTests(unittest.TestCase):
    def test_auto_serial_and_time(self):
        reg, updates = c.allocate(registry(), issue(), NOW, 'test/library')
        self.assertEqual(reg['next_id'], 3)
        self.assertIn('ideas/000002_20260922_123456_GMTp3/README.md', updates)
        self.assertEqual(reg['ideas']['ORI-000002']['owner_id'], 10)
        self.assertEqual(reg['ideas']['ORI-000002']['title'], 'A mathematical idea')

    def test_retry_idempotent(self):
        reg, _ = c.allocate(registry(), issue(), NOW, 'test/library')
        reg2, updates = c.allocate(reg, issue(), LATER, 'test/library')
        self.assertEqual(reg, reg2); self.assertEqual(updates, {})

    def test_deleted_source_issue_not_reused(self):
        reg = registry(); reg['ideas']['ORI-000001']['status'] = 'deleted'
        reg2, updates = c.allocate(reg, issue(4), NOW, 'test/library')
        self.assertEqual(updates, {}); self.assertEqual(reg2['next_id'], 2)

    def test_cc0_explicit_consent(self):
        obj = issue(); obj['body'] = obj['body'].replace('[x]', '[ ]')
        with self.assertRaises(ValueError): c.allocate(registry(), obj, NOW, 'test/library')

    def test_blank_description(self):
        obj = issue(); obj['body'] = obj['body'].replace('Explore irrational decimal expansions.', '')
        with self.assertRaises(ValueError): c.allocate(registry(), obj, NOW, 'test/library')

    def test_nested_headings_preserved(self):
        obj = issue(); obj['body'] = obj['body'].replace('Explore irrational decimal expansions.', 'A\n### More details\nB')
        _, updates = c.allocate(registry(), obj, NOW, 'test/library')
        self.assertIn('### More details\nB', next(iter(updates.values())).decode())

    def test_prompt_not_executed(self):
        obj = issue(); obj['body'] = obj['body'].replace('_No response_', '$(echo attack)\n```python\nraise Exception()\n```')
        _, updates = c.allocate(registry(), obj, NOW, 'test/library')
        self.assertIn('$(echo attack)', next(iter(updates.values())).decode())


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.base = snapshot({DIR + '/idea.md': '# Title\n\nText', DIR + '/code/a.py': 'original', c.REGISTRY: c.dump(registry())})

    def auth(self, update, user=USER, body=BODY, current=None):
        return c.authorize(current or self.base, self.base, self.base.changed(update), registry(), user, body)

    def test_owner_edit(self): self.assertTrue(self.auth({DIR + '/idea.md': b'# Edited'}))

    def test_nonowner_denied(self):
        with self.assertRaises(ValueError): self.auth({DIR + '/idea.md': b'# Edited'}, {'id': 11, 'login': 'bob'})

    def test_same_login_wrong_id_denied(self):
        with self.assertRaises(ValueError): self.auth({DIR + '/idea.md': b'# Edited'}, {'id': 11, 'login': 'alice'})

    def test_renamed_account_id_preserved(self):
        self.assertTrue(self.auth({DIR + '/idea.md': b'# Edited'}, {'id': 10, 'login': 'alice-new'}))

    def test_registry_takeover_denied(self):
        fake = registry(); fake['ideas']['ORI-000001']['owner_id'] = 11
        with self.assertRaises(ValueError): self.auth({c.REGISTRY: c.dump(fake)})

    def test_validator_takeover_denied(self):
        with self.assertRaises(ValueError): self.auth({'.github/ori/scripts/catalog.py': b'print("PASS")'})

    def test_bot_not_blanket_admin(self):
        with self.assertRaises(ValueError): self.auth({DIR + '/idea.md': b'# Edited'}, {'id': p.BOT_ID, 'login': 'github-actions[bot]'})

    def test_whole_delete_allowed(self):
        self.assertTrue(self.auth({DIR + '/idea.md': None, DIR + '/code/a.py': None}, body=''))

    def test_last_markdown_delete_denied(self):
        with self.assertRaises(ValueError): self.auth({DIR + '/idea.md': None})

    def test_uppercase_markdown(self):
        self.assertTrue(self.auth({DIR + '/idea.md': None, DIR + '/TEXT.MD': b'# Uppercase'}))

    def test_blank_markdown_denied(self):
        with self.assertRaises(ValueError): self.auth({DIR + '/idea.md': b' \n\t'})

    def test_non_utf8_denied(self):
        with self.assertRaises(UnicodeError): self.auth({DIR + '/idea.md': b'\xff\xfe\xff'})

    def test_submodule_and_symlink_denied(self):
        for mode in ('120000', '160000'):
            with self.subTest(mode=mode):
                head = self.base.changed({DIR + '/bad': b'../../registry'})
                old = head.entries[DIR + '/bad']; head.entries[DIR + '/bad'] = c.Entry(old.sha, mode, old.size)
                with self.assertRaises(ValueError): c.authorize(self.base, self.base, head, registry(), USER, BODY)

    def test_cross_folder_rename_denied(self):
        with self.assertRaises(ValueError): self.auth({DIR + '/idea.md': None, 'ideas/000002_20260922_123456_GMTp3/idea.md': b'# Stolen'})

    def test_current_base_race_denied(self):
        changed = self.base.changed({DIR + '/idea.md': b'# A different update'})
        with self.assertRaises(ValueError): self.auth({DIR + '/idea.md': b'# My update'}, current=changed)

    def test_missing_consent_denied(self):
        with self.assertRaises(ValueError): self.auth({DIR + '/code/a.py': b'updated'}, body='')

    def test_regular_code_not_executed(self):
        self.assertTrue(self.auth({DIR + '/code/danger.py': b'raise Exception("must not execute")'}))

    def test_path_traversal_rejected(self):
        for path in ('/root', 'ideas/../README.md', 'ideas//test', 'ideas\\test', 'ideas/\ntest'):
            self.assertFalse(c.safe_path(path))

    def test_too_many_paths(self):
        with self.assertRaises(ValueError): self.auth({DIR + f'/x{i}.txt': b'a' for i in range(1001)})


class PublisherTests(unittest.TestCase):
    def test_our_branch_needs_real_bot_and_own_repo(self):
        pr = {'user': {'id': p.BOT_ID}, 'head': {'ref': p.BRANCH, 'repo': {'full_name': 'test/library'}}, 'body': p.MARKER}
        self.assertTrue(p.is_our_pr(pr, 'test/library'))
        pr['head']['repo']['full_name'] = 'evil/fork'
        self.assertFalse(p.is_our_pr(pr, 'test/library'))

    def test_null_pr_body_is_not_ours(self):
        pr = {'user': {'id': p.BOT_ID}, 'head': {'ref': p.BRANCH, 'repo': {'full_name': 'test/library'}}, 'body': None}
        self.assertFalse(p.is_our_pr(pr, 'test/library'))

    def test_merge_checks_base_again(self):
        class Fake:
            calls = []
            def request(self, path, method='GET', data=None):
                self.calls.append((path, method))
                return {'state': 'open', 'head': {'sha': 'h'}} if path == '/pulls/1' else {'object': {'sha': 'advanced'}}
        fake = Fake()
        self.assertFalse(p.API.merge(fake, {'number': 1, 'head': {'sha': 'h'}}, 'old'))
        self.assertFalse(any(method == 'PUT' for _, method in fake.calls))

    def test_noop_diff(self):
        s = snapshot({'x': 'same'})
        self.assertEqual(p.updates_diff(s, {'x': b'same'}), {})

    def test_generated_pr_scope_enforced(self):
        class Fake:
            repo = 'test/library'
            def pages(self, path): return [{'filename': 'README.md'}]
        pr = {'number': 1, 'user': {'id': p.BOT_ID}, 'head': {'ref': p.BRANCH, 'repo': {'full_name': 'test/library'}}, 'body': p.MARKER, 'changed_files': 1}
        self.assertFalse(p.generated_pr_safe(Fake(), pr))


class FakeAPI:
    """In-memory REST/Git publication simulation, with no network or research code."""
    repo = 'test/library'
    def __init__(self):
        reg = registry(); reg['ideas'] = {}; reg['next_id'] = 1
        base = snapshot({c.REGISTRY: c.dump(reg), '.github/ori/config/maintainers.json': c.dump({'maintainers': [{'id': 10, 'login': 'alice'}]})})
        self.commits = {'base': base}; self.main_sha = 'base'; self.branches = {}; self.prs = {}; self.issues = [issue(1)]
        self.trees = {}; self.checks = {}; self.comments = {}; self.merge_enabled = True; self.n = 0

    def main(self): return self.main_sha, self.commits[self.main_sha]
    def snapshot(self, sha): return self.commits[sha]
    def check(self, sha, ok, summary): self.checks[sha] = ok
    def comment(self, number, message): self.comments[number] = message
    def pages(self, path):
        if path.startswith('/issues?'): return [i for i in self.issues if i['state'] == 'open']
        if path.startswith('/pulls?'):
            return list(self.prs.values()) if 'state=all' in path else [pr for pr in self.prs.values() if pr['state'] == 'open']
        if path.endswith('/files'):
            pr = self.prs[int(path.split('/')[2])]; old = self.commits[pr['parent']]; new = self.commits[pr['head']['sha']]
            return [{'filename': path} for path in set(old.entries) | set(new.entries) if old.entries.get(path) != new.entries.get(path)]
        raise AssertionError(path)

    def request(self, path, method='GET', data=None):
        if path == '/git/ref/heads/main': return {'object': {'sha': self.main_sha}}
        if path.startswith('/git/commits/') and method == 'GET': return {'tree': {'sha': path.rsplit('/', 1)[-1]}}
        if path == '/git/trees':
            self.n += 1; key = 'tree' + str(self.n)
            self.trees[key] = self.commits[data['base_tree']].changed({e['path']: e['content'].encode() for e in data['tree']})
            return {'sha': key}
        if path == '/git/commits':
            self.n += 1; key = 'commit' + str(self.n)
            self.commits[key] = self.trees[data['tree']]
            return {'sha': key}
        if path == '/git/ref/heads/' + p.BRANCH:
            if p.BRANCH not in self.branches: raise p.ApiError(404, 'not found')
            return {'object': {'sha': self.branches[p.BRANCH]}}
        if path == '/git/refs' and method == 'POST':
            self.branches[p.BRANCH] = data['sha']; return {}
        if path == '/git/refs/heads/' + p.BRANCH and method == 'PATCH':
            self.branches[p.BRANCH] = data['sha']
            for pr in self.prs.values():
                if pr['state'] == 'open': pr['head']['sha'] = data['sha']
            return {}
        if path == '/pulls' and method == 'POST':
            number = len(self.prs) + 1
            pr = {'number': number, 'state': 'open', 'draft': False, 'title': data['title'], 'body': data['body'], 'user': {'id': p.BOT_ID, 'login': 'github-actions[bot]'}, 'head': {'sha': self.branches[p.BRANCH], 'ref': p.BRANCH, 'repo': {'full_name': self.repo}}, 'parent': self.main_sha}
            self.prs[number] = pr; return pr
        if path.startswith('/pulls/'):
            pr = self.prs[int(path.split('/')[2])]
            if method == 'PATCH': pr.update(data)
            return pr
        if path.startswith('/issues/'):
            obj = next(i for i in self.issues if i['number'] == int(path.split('/')[2]))
            if method == 'PATCH': obj.update(data)
            return obj
        raise AssertionError((path, method, data))

    def merge(self, pr, base_sha):
        assert base_sha == self.main_sha
        assert self.checks.get(pr['head']['sha']) is True, 'Cannot merge before independent check'
        if not self.merge_enabled: return False
        self.main_sha = pr['head']['sha']; pr['state'] = 'closed'; pr['merged'] = True
        return True


class PublicationIntegrationTests(unittest.TestCase):
    def test_issue_to_permanent_folder_and_index(self):
        api = FakeAPI(); p.publish(api)
        reg = json.loads(api.main()[1].read(c.REGISTRY))
        self.assertEqual(reg['next_id'], 2)
        self.assertEqual(reg['ideas']['ORI-000001']['owner_id'], 10)
        self.assertEqual(json.loads(api.main()[1].read(c.INDEX))['count'], 1)
        self.assertEqual(api.issues[0]['state'], 'closed')
        self.assertEqual(len(api.prs), 1)

    def test_second_run_no_duplicate_pr(self):
        api = FakeAPI(); p.publish(api); sha = api.main_sha; p.publish(api)
        self.assertEqual(api.main_sha, sha); self.assertEqual(len(api.prs), 1)

    def test_pending_no_timestamp_only_changes_across_seconds(self):
        from datetime import datetime as DateTime
        api = FakeAPI(); api.merge_enabled = False
        with patch('publisher.datetime') as clock:
            clock.now.return_value = DateTime.fromisoformat(NOW)
            p.publish(api)
        old_sha = api.prs[1]['head']['sha']
        with patch('publisher.datetime') as clock:
            clock.now.return_value = DateTime.fromisoformat(LATER)
            p.publish(api)
        self.assertEqual(api.prs[1]['head']['sha'], old_sha)
        self.assertEqual(len(api.prs), 1)

    def test_pending_reuses_branch_and_pr(self):
        api = FakeAPI(); api.merge_enabled = False
        p.publish(api); old_sha = api.prs[1]['head']['sha']; p.publish(api)
        self.assertEqual(len(api.prs), 1)
        self.assertEqual(api.prs[1]['head']['sha'], old_sha)
        api.merge_enabled = True; p.publish(api)
        self.assertEqual(len(api.prs), 1); self.assertTrue(api.prs[1]['merged'])

    def test_two_simultaneous_issues_unique_ids(self):
        api = FakeAPI(); api.issues.append(issue(2)); p.publish(api)
        reg = json.loads(api.main()[1].read(c.REGISTRY))
        self.assertEqual(set(reg['ideas']), {'ORI-000001', 'ORI-000002'})
        self.assertEqual(len({i['path'] for i in reg['ideas'].values()}), 2)
        self.assertEqual(reg['next_id'], 3)

    def test_retry_after_branch_created_before_pr(self):
        api = FakeAPI()
        original = api.request
        def fail_once(path, method='GET', data=None):
            if path == '/pulls' and method == 'POST':
                raise p.ApiError(503, 'simulated interruption')
            return original(path, method, data)
        api.request = fail_once
        with self.assertRaises(p.ApiError): p.publish(api)
        self.assertIn(p.BRANCH, api.branches)
        self.assertEqual(len(api.prs), 0)
        api.request = original
        p.publish(api)
        self.assertEqual(len(api.prs), 1)
        self.assertEqual(json.loads(api.main()[1].read(c.REGISTRY))['next_id'], 2)

    def test_new_issue_after_previous_merge(self):
        api = FakeAPI(); p.publish(api); api.issues.append(issue(2)); p.publish(api)
        self.assertEqual(json.loads(api.main()[1].read(c.REGISTRY))['next_id'], 3)
        self.assertEqual(len(api.prs), 2)
        self.assertEqual(len([pr for pr in api.prs.values() if pr['state'] == 'open']), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
