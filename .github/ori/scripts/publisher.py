"""CC0-1.0. Trusted GitHub-only publisher. Never checks out or executes PR content."""
from __future__ import annotations
import base64
import copy
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import quote

from catalog import (CONSENT, Entry, Snapshot, REGISTRY, INDEX, HUMAN, TZ, allocate,
                     authorize, blob_sha, consented, dump, render_catalog, safe_path, validate_registry)

BRANCH = 'automation/ori-platform'
MARKER = '<!-- ori-platform-v3 -->'
BOT_ID = 41898282
GENERATED = {REGISTRY, INDEX, HUMAN}


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f'GitHub HTTP {status}: {message[:600]}')


class API:
    def __init__(self, repo: str, token: str):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or not token:
            raise ValueError('GITHUB_REPOSITORY and GH_TOKEN are required')
        self.repo, self.token = repo, token
        self.root = 'https://api.github.com/repos/' + repo
        self.blobs: dict[str, bytes] = {}

    def request(self, path: str, method: str = 'GET', data=None):
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('Repository-relative API path required')
        req = urllib.request.Request(self.root + path, data=None if data is None else json.dumps(data).encode(), method=method,
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                     'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'ORI-platform'})
        try:
            with urllib.request.urlopen(req, timeout=40) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code, exc.read().decode(errors='replace')) from None

    def pages(self, path: str):
        items = []
        for page in range(1, 101):
            part = self.request(path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
            items.extend(part)
            if len(part) < 100:
                return items
        raise ValueError('API pagination limit reached; refusing an incomplete scan')

    def blob(self, sha: str) -> bytes:
        if sha not in self.blobs:
            obj = self.request('/git/blobs/' + sha)
            if obj.get('encoding') != 'base64':
                raise ValueError('Unexpected GitHub blob encoding')
            data = base64.b64decode(obj['content'])
            if blob_sha(data) != sha:
                raise ValueError('Downloaded blob hash mismatch')
            self.blobs[sha] = data
        return self.blobs[sha]

    def snapshot(self, sha: str) -> Snapshot:
        commit = self.request('/git/commits/' + sha)
        obj = self.request('/git/trees/' + commit['tree']['sha'] + '?recursive=1')
        if obj.get('truncated'):
            raise ValueError('GitHub tree is truncated; automatic processing stopped')
        entries = {e['path']: Entry(e['sha'], e['mode'], e.get('size', 0)) for e in obj['tree'] if e['type'] != 'tree'}
        return Snapshot(entries, self.blob)

    def main(self):
        sha = self.request('/git/ref/heads/main')['object']['sha']
        return sha, self.snapshot(sha)

    def check(self, sha: str, ok: bool, summary: str):
        # This is a real, independent authorization check of the immutable candidate,
        # not a fabricated approval or an alias for arbitrary PR workflow success.
        self.request('/check-runs', 'POST', {'name': 'ori-validation', 'head_sha': sha, 'status': 'completed',
            'conclusion': 'success' if ok else 'failure',
            'output': {'title': 'Idea access and publication validation', 'summary': summary[:65000]}})

    def comment(self, number: int, message: str):
        body = MARKER + '\n' + message
        existing = [c for c in self.pages(f'/issues/{number}/comments') if c['user']['id'] == BOT_ID and c.get('body', '').startswith(MARKER)]
        if existing:
            if existing[-1]['body'] != body:
                self.request('/issues/comments/' + str(existing[-1]['id']), 'PATCH', {'body': body})
        else:
            self.request(f'/issues/{number}/comments', 'POST', {'body': body})

    def merge(self, pr: dict, base_sha: str) -> bool:
        number, head = pr['number'], pr['head']['sha']
        for _ in range(4):
            live = self.request(f'/pulls/{number}')
            if live['state'] != 'open' or live['head']['sha'] != head:
                print(f'PR #{number} changed; not merged')
                return False
            if self.request('/git/ref/heads/main')['object']['sha'] != base_sha:
                print(f'Base advanced before PR #{number} merge; revalidation required')
                return False
            try:
                result = self.request(f'/pulls/{number}/merge', 'PUT', {'sha': head, 'merge_method': 'squash'})
                if result.get('merged'):
                    print(f'Merged PR #{number} at {result["sha"]}')
                    return True
            except ApiError as exc:
                if exc.status not in (405, 409):
                    raise
                print(f'PR #{number} pending GitHub rules or conflict: {exc}')
            time.sleep(2)
        return False


def is_our_pr(pr: dict, repo: str) -> bool:
    return (pr['user']['id'] == BOT_ID and pr['head']['ref'] == BRANCH
            and (pr['head'].get('repo') or {}).get('full_name') == repo
            and (pr.get('body') or '').startswith(MARKER))


def process_contributions(api: API, prs: list[dict]) -> None:
    for short in prs:
        if short.get('draft') or is_our_pr(short, api.repo) or short['user']['id'] == BOT_ID:
            continue
        pr = api.request(f'/pulls/{short["number"]}')
        base_sha, current = api.main()
        head = api.snapshot(pr['head']['sha'])
        comparison = api.request('/compare/' + base_sha + '...' + pr['head']['sha'])
        ancestor = api.snapshot(comparison['merge_base_commit']['sha'])
        reg = json.loads(current.read(REGISTRY)); validate_registry(reg)
        config = json.loads(current.read('.github/ori/config/maintainers.json'))
        maintainer = pr['user']['id'] in {u['id'] for u in config['maintainers']}
        changed = {p for p in set(ancestor.entries) | set(head.entries) if ancestor.entries.get(p) != head.entries.get(p)}
        core_change = any(not p.startswith('ideas/') or p == HUMAN for p in changed)
        if maintainer and core_change:
            # Maintainers can change platform code, but the robot never auto-merges it.
            api.check(pr['head']['sha'], True, 'Trusted maintainer platform change. Manual maintainer review/merge required; this check does not execute candidate code or certify tests.')
            continue
        try:
            authorize(current, ancestor, head, reg, pr['user'], pr.get('body', ''))
        except (ValueError, KeyError, UnicodeError) as exc:
            api.check(pr['head']['sha'], False, str(exc))
            print(f'Rejected PR #{pr["number"]}: {exc}')
            continue
        api.check(pr['head']['sha'], True, f'Validated all changed paths against trusted main {base_sha}; authenticated PR author {pr["user"]["login"]}; Markdown, CC0 consent and file checks passed. Submitted code was not executed.')
        api.merge(pr, base_sha)


def updates_diff(snap: Snapshot, updates: dict[str, bytes]) -> dict[str, bytes]:
    return {p: b for p, b in updates.items() if snap.entries.get(p) != Entry(blob_sha(b), '100644', len(b))}


def plan(api: API, base: Snapshot, issues: list[dict], pending: Snapshot | None, now: str):
    registry = json.loads(base.read(REGISTRY)); validate_registry(registry)
    reserved = {}
    if pending is not None and REGISTRY in pending.entries:
        pending_reg = json.loads(pending.read(REGISTRY)); validate_registry(pending_reg)
        reserved = {r.get('source_issue'): r['created_at'] for r in pending_reg['ideas'].values()}
    updates = {}
    source_hashes = {}
    existing_issues = {r.get('source_issue') for r in registry['ideas'].values()}
    for issue in sorted(issues, key=lambda i: (i.get('created_at', ''), i['number'])):
        if 'pull_request' in issue or issue['number'] in existing_issues or not re.match(r'^\[NEW IDEA\]', issue.get('title', ''), re.I):
            continue
        try:
            registry, files = allocate(registry, issue, reserved.get(issue['number'], now), api.repo)
        except (ValueError, KeyError) as exc:
            api.comment(issue['number'], 'Not published yet: ' + str(exc) + '\nUse the new-Idea form; an existing issue can be edited to add the checked CC0 declaration.')
            continue
        source_hashes[issue['number']] = hashlib.sha256(issue['body'].encode()).hexdigest()
        updates.update(files)
    working = base.changed(updates)
    # Preserve a pending index timestamp only when its recomputed content is identical.
    # No ownership or source data are trusted from the pending search index.
    if pending is not None and INDEX in pending.entries:
        working = working.changed({INDEX: pending.read(INDEX)})
    updates.update(render_catalog(working, registry, now, api.repo))
    return updates_diff(base, updates), source_hashes


def generated_pr_safe(api: API, pr: dict) -> bool:
    """Never overwrite somebody's manual PR, even if its branch name looks right."""
    if not is_our_pr(pr, api.repo):
        return False
    files = api.pages(f'/pulls/{pr["number"]}/files')
    if len(files) != pr.get('changed_files', len(files)):
        return False
    return all(f['filename'] in GENERATED or re.fullmatch(r'ideas/[0-9]{6,}_[0-9]{8}_[0-9]{6}_GMTp3/README.md', f['filename']) for f in files)


def publish(api: API):
    issues = api.pages('/issues?state=open&sort=created&direction=asc')
    prs = api.pages('/pulls?state=open')
    process_contributions(api, prs)
    base_sha, base = api.main()
    now = datetime.now(TZ).isoformat(timespec='seconds')
    pending_prs = [p for p in prs if p['head']['ref'] == BRANCH and (p['head'].get('repo') or {}).get('full_name') == api.repo]
    if len(pending_prs) > 1:
        raise ValueError('Multiple publication PRs exist; refusing to guess')
    pending_pr = api.request(f'/pulls/{pending_prs[0]["number"]}') if pending_prs else None
    if pending_pr and not generated_pr_safe(api, pending_pr):
        raise ValueError('Reserved publication branch/PR contains non-generated changes; not overwritten')
    pending = api.snapshot(pending_pr['head']['sha']) if pending_pr else None
    orphan_sha = None
    if pending_pr is None:
        try:
            ref = api.request('/git/ref/heads/' + BRANCH)
        except ApiError as exc:
            if exc.status != 404:
                raise
        else:
            history = api.pages('/pulls?state=all&head=' + quote(api.repo.split('/')[0] + ':' + BRANCH))
            if not history:
                # Recover a crash after creating the branch but before creating its PR.
                # It is reusable only if its ENTIRE tree matches a freshly verified plan.
                orphan_sha = ref['object']['sha']
                pending = api.snapshot(orphan_sha)
            elif not all(is_our_pr(pr, api.repo) for pr in history):
                raise ValueError('Reserved branch has non-platform history; refusing overwrite')
    updates, source_hashes = plan(api, base, issues, pending, now)
    if not updates:
        print('Catalog current: no changes and no timestamp-only PR')
        if pending_pr:
            api.request(f'/pulls/{pending_pr["number"]}', 'PATCH', {'state': 'closed'})
        close_published_issues(api, base)
        return
    expected = base.changed(updates)
    if orphan_sha and pending.entries != expected.entries:
        raise ValueError('Orphan branch differs from the verified publication plan; manual recovery required')
    head_sha = pending_pr['head']['sha'] if pending_pr else orphan_sha
    if pending is None or pending.entries != expected.entries:
        tree_base = api.request('/git/commits/' + base_sha)['tree']['sha']
        tree = api.request('/git/trees', 'POST', {'base_tree': tree_base, 'tree': [
            {'path': p, 'mode': '100644', 'type': 'blob', 'content': data.decode('utf-8')} for p, data in sorted(updates.items())]})
        commit = api.request('/git/commits', 'POST', {'message': 'chore: publish Ideas and refresh catalog', 'tree': tree['sha'], 'parents': [base_sha]})
        head_sha = commit['sha']
        # Only this dedicated machine-owned branch is refreshed, never main or a user's branch.
        try:
            api.request('/git/ref/heads/' + BRANCH)
        except ApiError as exc:
            if exc.status != 404:
                raise
            api.request('/git/refs', 'POST', {'ref': 'refs/heads/' + BRANCH, 'sha': head_sha})
        else:
            if not pending_pr:
                # A stale branch left after a previous merged/closed machine PR is disposable.
                history = api.pages('/pulls?state=all&head=' + quote(api.repo.split('/')[0] + ':' + BRANCH))
                if not history or not all(is_our_pr(p, api.repo) for p in history):
                    raise ValueError('Existing reserved branch is not verifiably machine-owned')
            api.request('/git/refs/heads/' + BRANCH, 'PATCH', {'sha': head_sha, 'force': True})
    if not pending_pr:
        pending_pr = api.request('/pulls', 'POST', {'title': 'chore: publish Ideas and refresh catalog', 'head': BRANCH, 'base': 'main',
            'body': MARKER + '\nGenerated from current main and consenting new-Idea issues. One reusable PR; no submitted code is executed. IDs become permanent when this PR is merged.'})
    pr = api.request(f'/pulls/{pending_pr["number"]}')
    # Independently read back the entire resulting tree, not only a truncated file listing.
    if pr['head']['sha'] != head_sha or api.snapshot(head_sha).entries != expected.entries:
        raise ValueError('Publication tree changed; refusing approval/merge')
    if api.request('/git/ref/heads/main')['object']['sha'] != base_sha:
        print('main advanced while building catalog; next run will regenerate')
        return
    for number, body_hash in source_hashes.items():
        live = api.request(f'/issues/{number}')
        if live['state'] != 'open' or hashlib.sha256((live.get('body') or '').encode()).hexdigest() != body_hash:
            print(f'Issue #{number} changed; publication needs regeneration')
            return
    api.check(head_sha, True, f'Generated tree read back and matched exactly against deterministic publication plan from main {base_sha}. Registry uniqueness, Markdown indexing, source consent and safe paths verified. No PR code executed.')
    for number in source_hashes:
        api.comment(number, f'Publication is prepared in PR #{pr["number"]}. The permanent folder appears after merge. If GitHub rules block it, the same PR is retried, not duplicated.')
    if api.merge(pr, base_sha):
        _, current = api.main()
        close_published_issues(api, current)
    else:
        print(f'PR #{pr["number"]} is pending. Required rules were NOT bypassed; see its Checks tab.')


def close_published_issues(api: API, snap: Snapshot):
    registry = json.loads(snap.read(REGISTRY))
    for item in registry['ideas'].values():
        number = item.get('source_issue')
        if type(number) is not int or item.get('status') != 'active':
            continue
        issue = api.request(f'/issues/{number}')
        if issue.get('state') == 'open':
            api.comment(number, 'Published: https://github.com/' + api.repo + '/tree/main/' + item['path'] + '\nAdd code, data, papers or figures to this folder through a PR. The issue remains available as the submission record.')
            api.request(f'/issues/{number}', 'PATCH', {'state': 'closed', 'state_reason': 'completed'})


def main():
    # Only trusted default-branch workflow code may invoke this entry point with a write token.
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    api = API(repo, os.environ.get('GH_TOKEN', ''))
    publish(api)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'::error::ORI platform stopped: {exc}', file=sys.stderr)
        raise
