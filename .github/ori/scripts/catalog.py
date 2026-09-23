"""CC0-1.0. Pure, deterministic catalog/authorization logic. No submitted code runs."""
from __future__ import annotations
import copy
import hashlib
import html
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Callable
from urllib.parse import quote

REGISTRY = '.github/ori/registry/ideas.json'
INDEX = '.github/ori/index/ideas.json'
HUMAN = 'ideas/README.md'
TZ = timezone(timedelta(hours=3))
CONSENT = 'I dedicate my original contribution under CC0-1.0 and have the right to submit it.'
MAX_MD = 2 * 1024 * 1024
MAX_TEXT = 32 * 1024 * 1024
MAX_INDEX = 64 * 1024 * 1024
FOLDER = re.compile(r'^ideas/([0-9]{6,})_([0-9]{8})_([0-9]{6})_GMTp3$')
TAXONOMY = {
    'Artificial Intelligence / Machine Learning': ['machine learning', 'deep learning', 'neural network', 'transformer', 'large language model', 'llm', 'reinforcement learning', 'causal sequence model', 'tcn', '机器学习', '深度学习', '神经网络', '大语言模型', '强化学习'],
    'Mathematics / Statistics': ['mathematics', 'mathematical', 'irrational', 'decimal expansion', 'theorem', 'proof', 'statistics', 'statistical', 'stochastic', 'deterministic', '数学', '统计', '定理', '证明', '无理数'],
    'Control / Optimization': ['optimization', 'optimal control', 'model predictive control', 'mpc', 'pid', 'lqr', 'dynamic programming', 'particle swarm', 'controller', '控制', '优化', '动态规划'],
    'Mechanical / Aerospace Engineering': ['mechanical engineering', 'wankel', 'rotary engine', 'combustion', 'propulsion', 'aerodynamics', 'airfoil', '发动机', '气动', '机械', '推进'],
    'Robotics / Autonomous Systems': ['robot', 'robotics', 'uav', 'drone', 'slam', 'motion planning', '机器人', '无人机', '路径规划'],
    'Energy / Power Systems': ['battery', 'powertrain', 'energy management', 'fuel cell', 'renewable energy', '电池', '混合动力', '能量管理', '燃料电池'],
    'Physics': ['physics', 'quantum', 'thermodynamics', 'optics', '物理', '量子', '热力学', '光学'],
    'Chemistry / Materials': ['chemistry', 'catalyst', 'catalysis', 'materials science', 'alloy', 'polymer', '化学', '催化', '材料', '合金'],
    'Biology / Medicine': ['biology', 'biomedical', 'medicine', 'protein', 'gene', 'genomics', 'drug discovery', '生物', '医学', '蛋白', '基因'],
    'Computer Science / Software': ['computer science', 'software', 'database', 'compiler', 'cybersecurity', 'distributed system', '计算机科学', '软件', '数据库'],
    'Earth / Environmental Science': ['climate', 'environmental science', 'geology', 'ocean', '气候', '环境科学', '地质', '海洋'],
    'Social / Economic Sciences': ['economics', 'finance', 'social science', 'psychology', '经济', '金融', '社会科学', '心理学'],
}
STOP = set('a an the and or of in on to is are was were be been as at by for from with without this that these those it its their they we you our your into not no can could should would will may might have has had do does did than then also all each any only one two use used using idea ideas research paper prompt result results method methods analysis proposed work study model models data code file files author created source id license cc0 readme github http https www com org md py'.split())


def dump(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def safe_path(path: str) -> bool:
    parts = path.split('/')
    return bool(path) and not path.startswith('/') and '\\' not in path and all(p not in ('', '.', '..', '.git') for p in parts) and not any(ord(c) < 32 or ord(c) == 127 for c in path)


@dataclass(frozen=True)
class Entry:
    sha: str
    mode: str = '100644'
    size: int = 0


class Snapshot:
    """Virtual Git tree: blobs stay data, never become executable worktree files."""
    def __init__(self, entries: dict[str, Entry], reader: Callable[[str], bytes]):
        self.entries = dict(entries)
        self.reader = reader
        self.cache: dict[str, bytes] = {}

    def read(self, path: str, limit: int = MAX_TEXT) -> bytes:
        entry = self.entries[path]
        if entry.mode not in ('100644', '100755') or entry.size > limit:
            raise ValueError(f'Unsafe or oversized file: {path}')
        if entry.sha not in self.cache:
            data = self.reader(entry.sha)
            if len(data) > limit or blob_sha(data) != entry.sha:
                raise ValueError(f'Blob size/hash mismatch: {path}')
            self.cache[entry.sha] = data
        if len(self.cache[entry.sha]) > limit:
            raise ValueError(f'Cached file exceeds read limit: {path}')
        return self.cache[entry.sha]

    def changed(self, updates: dict[str, bytes | None]) -> Snapshot:
        store = dict(self.cache)
        entries = dict(self.entries)
        for path, data in updates.items():
            if not safe_path(path):
                raise ValueError(f'Unsafe path: {path}')
            if data is None:
                entries.pop(path, None)
            else:
                sha = blob_sha(data)
                store[sha] = data
                entries[path] = Entry(sha, '100644', len(data))
        def read(sha):
            return store[sha] if sha in store else self.reader(sha)
        return Snapshot(entries, read)

    def under(self, path: str) -> list[str]:
        return sorted(p for p in self.entries if p.startswith(path + '/'))


def parse_time(value: str) -> datetime:
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+03:00', value):
        raise ValueError('Creation time must include seconds and fixed +03:00')
    d = datetime.fromisoformat(value)
    if d.utcoffset() != timedelta(hours=3) or d.microsecond or not value.endswith('+03:00'):
        raise ValueError('Creation time must have seconds and fixed +03:00 offset')
    return d


def validate_registry(reg: dict) -> None:
    if reg.get('timezone') != 'GMT+3' or reg.get('utc_offset') != '+03:00':
        raise ValueError('Registry timezone changed')
    paths, issues, numbers = set(), set(), []
    for ident, item in reg.get('ideas', {}).items():
        if not re.fullmatch(r'ORI-[0-9]{6,}', ident):
            raise ValueError(f'Invalid ID: {ident}')
        n = int(ident[4:]); numbers.append(n)
        if n < 1 or ident != f'ORI-{n:06d}':
            raise ValueError('Non-canonical ID')
        match = FOLDER.fullmatch(item.get('path', ''))
        when = parse_time(item['created_at'])
        if not match or item['path'] != f'ideas/{n:06d}_{when:%Y%m%d_%H%M%S}_GMTp3':
            raise ValueError('ID/path/time mismatch')
        if item['path'] in paths:
            raise ValueError('Duplicate directory')
        paths.add(item['path'])
        issue = item.get('source_issue')
        if issue is not None:
            if issue in issues:
                raise ValueError('One issue allocated twice')
            issues.add(issue)
        if item.get('status') not in ('active', 'deleted') or not item.get('owner'):
            raise ValueError('Invalid status/owner')
    if type(reg.get('next_id')) is not int or reg['next_id'] <= max(numbers, default=0):
        raise ValueError('next_id would reuse an existing ID')


def plain(text: str) -> str:
    text = visible_markdown(text)
    text = re.sub(r'!?\[([^\[\]\n]*)\]\([^()\n]*\)', r'\1', text)
    text = re.sub(r'<[^<>\n]*>', ' ', text)
    lines = []
    for line in text.splitlines():
        if re.match(r'^\s*\*\*(ID|Author|Created|Source issue):\*\*', line):
            continue
        lines.append(re.sub(r'^[#>\s]+|[*`_~]', '', line).strip())
    return '\n'.join(lines).strip()


def terms(text: str, word: str) -> int:
    if re.search('[\u3400-\u9fff]', word):
        return text.casefold().count(word.casefold())
    return len(re.findall(r'(?<![\w])' + re.escape(word) + r'(?:s)?(?![\w])', text, flags=re.I))


def fields_keywords(text: str, title: str) -> tuple[list[str], list[str]]:
    scores, words = [], Counter()
    for field, vocabulary in TAXONOMY.items():
        score = 0
        for term in vocabulary:
            count = terms(text, term)
            if count:
                weight = (3 if ' ' in term else 2)
                score += weight
                words[term] += min(count, 4) * weight
        if score:
            scores.append((score, field))
    scores.sort(key=lambda x: (-x[0], x[1]))
    fields = [f for s, f in scores if s >= max(2, scores[0][0] * .35)][:3] if scores else ['Interdisciplinary / Other']
    counts = Counter(term.casefold() for term in re.findall(r'[a-zA-Z][a-zA-Z0-9]*(?:-[a-zA-Z0-9]+)*', text))
    for term, count in counts.items():
        if len(term) > 2 and term not in STOP:
            words[term] += count * (1 + (2 if terms(title, term) else 0))
    keywords = [t for t, _ in sorted(words.items(), key=lambda p: (-p[1], p[0])) if t not in STOP][:8]
    return fields, keywords


def excerpt(raw: str) -> str:
    section = re.search(r'(?ims)^##\s+(?:Idea|Abstract|Research question|研究想法|摘要)\s*\n(.*?)(?=^##\s|\Z)', raw)
    text = plain(section.group(1) if section else re.sub(r'^#\s+.*$', '', raw, flags=re.M))
    text = re.sub(r'\s+', ' ', text).strip()
    return text if len(text) <= 260 else text[:259].rstrip() + '…'


def md_escape(text: str) -> str:
    text = html.escape(re.sub(r'\s+', ' ', str(text)), quote=False)
    return re.sub(r'([\\`*_|\[\]])', r'\\\1', text)


def render_catalog(snap: Snapshot, registry: dict, now: str, repo: str) -> dict[str, bytes]:
    """Only generated files change. A no-op rebuild is byte-for-byte stable."""
    reg = copy.deepcopy(registry)
    validate_registry(reg)
    active_dirs = {r['path'] for r in reg['ideas'].values() if r['status'] == 'active'}
    actual_dirs = {'/'.join(p.split('/')[:2]) for p in snap.entries if len(p.split('/')) > 2 and p.startswith('ideas/')}
    unknown = actual_dirs - active_dirs
    # Deleted IDs must never silently become active again.
    if unknown:
        raise ValueError('Unregistered/restored Idea folders: ' + ', '.join(sorted(unknown)))
    old = json.loads(snap.read(INDEX, MAX_INDEX)) if INDEX in snap.entries else {}
    rows = []
    for ident, item in reg['ideas'].items():
        if item['status'] == 'deleted':
            continue
        paths = snap.under(item['path'])
        if not paths:
            item['status'] = 'deleted'; item.setdefault('deleted_at', now)
            continue
        for p in paths:
            if not safe_path(p) or snap.entries[p].mode not in ('100644', '100755'):
                raise ValueError(f'Non-regular/unsafe Idea file: {p}')
        docs = sorted((p for p in paths if p.lower().endswith('.md')), key=lambda p: (p != item['path'] + '/README.md', len(PurePosixPath(p).parts), p.casefold(), p))
        if not docs:
            raise ValueError('At least one Markdown file is required: ' + item['path'])
        documents, total = [], 0
        for p in docs:
            ent = snap.entries[p]
            if ent.size > MAX_MD:
                raise ValueError('Markdown file exceeds 2 MiB; split it: ' + p)
            # Reuse text only from a hash-verified Git blob, never from an untrusted index override.
            raw_bytes = snap.read(p, MAX_MD)
            raw = raw_bytes.decode('utf-8-sig')
            total += len(raw_bytes)
            if total > MAX_TEXT:
                raise ValueError('Idea Markdown exceeds 32 MiB; indexing aborted, not truncated')
            documents.append({'path': p[len(item['path']) + 1:], 'sha': ent.sha, 'text': raw})
        if not any(d['text'].strip() for d in documents):
            raise ValueError('Markdown must contain text')
        first = documents[0]['text']
        match = re.search(r'^#\s+(.+)$', first, re.M)
        title = plain(match.group(1))[:200] if match else item.get('title') or PurePosixPath(docs[0]).stem
        all_text = '\n'.join(plain(d['text']) for d in documents)
        fields, keywords = fields_keywords(all_text, title)
        files = [p[len(item['path']) + 1:] for p in paths]
        rows.append({'id': ident, 'title': title, 'summary': excerpt(first), 'fields': fields, 'keywords': keywords,
                     'classification_method': 'keyword-rules-v2', 'owner': item['owner'], 'created_at': item['created_at'],
                     'path': item['path'], 'url': f'https://github.com/{repo}/tree/main/' + quote(item['path'], safe='/'),
                     'license': item.get('license', 'See file notices'), 'files': files, 'documents': documents})
    rows.sort(key=lambda x: int(x['id'][4:]), reverse=True)
    data = {'schema_version': 3, 'count': len(rows), 'ideas': rows}
    old_data = {k: v for k, v in old.items() if k != 'generated_at'}
    data['generated_at'] = old.get('generated_at') if old_data == data else now
    lines = ['# Research Ideas', '', '[Submit an Idea](https://github.com/' + repo + '/issues/new?template=new_idea.yml) · [Machine-readable full-text index](../' + INDEX + ')', '',
             'Newest first. Click a title to open its complete folder. Ctrl+F searches this overview; for all Markdown use GitHub Code search: `repo:' + repo + ' path:ideas/ YOUR_KEYWORD`.', '',
             'Fields/keywords are rule-based suggestions, not novelty or quality assessments.', '', '| Idea | Field / keywords | Summary |', '|---|---|---|']
    for row in rows:
        directory = quote(row['path'][6:], safe='') + '/'
        groups = []
        for label, starts in [('Code', ('code/',)), ('Paper', ('paper/',)), ('Data', ('data/',)), ('Results', ('results/',)), ('Figures', ('figures/',))]:
            candidates = [f for f in row['files'] if f.startswith(starts)]
            if candidates:
                target = candidates[0].split('/')[0] + '/'
                groups.append(f'[{label}]({directory}{target})')
        title = f'[{row["id"]} · {md_escape(row["title"])}]({directory})'
        detail = md_escape('; '.join(row['fields']) + ' · ' + ', '.join(row['keywords']))
        summary = md_escape(row['summary']) + '<br>' + ' · '.join(groups)
        summary += '<br>' + md_escape('@' + row['owner'] + ' · ' + row['created_at'])
        lines.append(f'| {title} | {detail} | {summary} |')
    if not rows:
        lines.append('| No Ideas published yet | — | Submit the first Idea using the link above. |')
    index_bytes = dump(data)
    if len(index_bytes) > MAX_INDEX:
        raise ValueError('Full-text catalog exceeds 64 MiB; shard it before accepting more content')
    return {REGISTRY: dump(reg), INDEX: index_bytes, HUMAN: ('\n'.join(lines) + '\n').encode()}


def visible_markdown(text: str) -> str:
    """Mask code and comments without changing offsets used to parse Issue forms."""
    def mask(value):
        return re.sub(r'[^\n]', ' ', value)
    text = re.sub(r'<!--.*?(?:-->|\Z)', lambda m: mask(m.group()), text or '', flags=re.S)
    output, fence = [], None
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^[ ]{0,3}(`{3,}|~{3,})', line)
        if fence is not None:
            output.append(mask(line))
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= fence[1] and not line[marker.end():].strip():
                fence = None
        elif marker:
            fence = (marker.group(1)[0], len(marker.group(1)))
            output.append(mask(line))
        elif line.startswith(('    ', '\t')):
            output.append(mask(line))
        else:
            output.append(line)
    return ''.join(output)


def consented(body: str) -> bool:
    return bool(re.search(r'^[ ]{0,3}-[ ]*\[[xX]\][ ]*' + re.escape(CONSENT) + r'[ ]*$', visible_markdown(body), re.M))


def sections(body: str) -> dict[str, str]:
    body = body or ''
    labels = 'Idea title|Idea description|Optional prompt for AI|Declaration'
    found = list(re.finditer(r'^### (' + labels + r')[ \t]*$', visible_markdown(body), re.M))
    names = [m.group(1) for m in found]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate submission form headings; keep each form section once')
    return {m.group(1): body[m.end(): found[i + 1].start() if i + 1 < len(found) else len(body)].strip() for i, m in enumerate(found)}


def allocate(registry: dict, issue: dict, now: str, repo: str) -> tuple[dict, dict[str, bytes]]:
    reg = copy.deepcopy(registry)
    validate_registry(reg)
    if any(x.get('source_issue') == issue['number'] for x in reg['ideas'].values()):
        return reg, {}  # Idempotent, including deleted IDs.
    values = sections(issue.get('body') or '')
    if not re.match(r'^\[NEW IDEA\]', issue.get('title', ''), re.I) or not consented(values.get('Declaration', '')):
        raise ValueError('New Ideas require the submission form and explicit CC0 consent in Declaration')
    title, description = values.get('Idea title', ''), values.get('Idea description', '')
    if not title or not description or description == '_No response_' or len(title) > 200 or len(description) > 60000:
        raise ValueError('A title (1–200 characters) and description (1–60000 characters) are required')
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in title):
        raise ValueError('Idea title must be a single line without control characters')
    when = parse_time(now)
    user = issue['user']
    if type(user.get('id')) is not int or not re.fullmatch(r'[A-Za-z0-9-]+(?:\[bot\])?', user.get('login', '')):
        raise ValueError('Invalid GitHub identity')
    n = reg['next_id']; ident = f'ORI-{n:06d}'
    folder = f'ideas/{n:06d}_{when:%Y%m%d_%H%M%S}_GMTp3'
    reg['ideas'][ident] = {'owner': user['login'], 'owner_id': user['id'], 'title': title, 'created_at': now,
        'status': 'active', 'path': folder, 'source_issue': issue['number'], 'source_issue_node_id': issue.get('node_id'),
        'source_body_sha256': hashlib.sha256(issue['body'].encode()).hexdigest(), 'license': 'CC0-1.0'}
    reg['next_id'] = n + 1
    content = f'# {md_escape(title)}\n\n**ID:** {ident}  \n**Author:** @{user["login"]}  \n**Created:** {now} (GMT+3)  \n**Source issue:** https://github.com/{repo}/issues/{issue["number"]}\n\n## Idea\n\n{description}\n'
    prompt = values.get('Optional prompt for AI', '')
    if prompt and prompt != '_No response_':
        content += '\n## Prompt for AI\n\n' + prompt + '\n'
    content += '\n## Reuse\n\nOriginal contributed material: CC0-1.0; no attribution required by this dedication. Third-party notices still apply.\n'
    return reg, {folder + '/README.md': content.encode()}


def authorize(current: Snapshot, ancestor: Snapshot, head: Snapshot, registry: dict, user: dict, body: str) -> dict[str, Entry | None]:
    """Use the trusted BASE registry and GitHub user ID, not files from the PR."""
    validate_registry(registry)
    paths = set(ancestor.entries) | set(head.entries)
    delta = {p: head.entries.get(p) for p in paths if ancestor.entries.get(p) != head.entries.get(p)}
    if not delta or len(delta) > 1000:
        raise ValueError('Empty or oversized change set (maximum 1000 paths)')
    owners = {v['path']: v for v in registry['ideas'].values() if v['status'] == 'active'}
    candidate = dict(current.entries)
    touched, added_bytes = set(), 0
    for path, entry in delta.items():
        folder = '/'.join(path.split('/')[:2])
        item = owners.get(folder)
        if not safe_path(path) or len(path.split('/')) < 3 or not item:
            raise ValueError('Protected/unregistered path: ' + path)
        owner_ok = user.get('id') == item['owner_id'] if item.get('owner_id') is not None else user.get('login', '').casefold() == item['owner'].casefold()
        if not owner_ok:
            raise ValueError('You do not own: ' + folder)
        if current.entries.get(path) not in (ancestor.entries.get(path), entry):
            raise ValueError('Base changed; update your PR: ' + path)
        if entry is not None:
            if entry.mode not in ('100644', '100755') or entry.size > 50 * 1024 * 1024:
                raise ValueError('Non-regular or oversized file: ' + path)
            added_bytes += entry.size
            candidate[path] = entry
        else:
            candidate.pop(path, None)
        touched.add(folder)
    if added_bytes > 100 * 1024 * 1024:
        raise ValueError('PR exceeds 100 MiB')
    if any(e is not None for e in delta.values()) and not consented(body):
        raise ValueError('Tick the CC0 contribution consent in the PR description')
    for folder in touched:
        remaining = [p for p in candidate if p.startswith(folder + '/')]
        if not remaining:
            continue  # Whole-Idea deletion is allowed; registry keeps a tombstone.
        md = [p for p in remaining if p.lower().endswith('.md')]
        if not md:
            raise ValueError('An active Idea needs at least one .md file')
        has_text, total = False, 0
        for p in md:
            source = head if p in delta and delta[p] is not None else current
            raw_bytes = source.read(p, MAX_MD)
            total += len(raw_bytes)
            if total > MAX_TEXT:
                raise ValueError('Idea Markdown exceeds 32 MiB; split/reduce before merging')
            raw = raw_bytes.decode('utf-8-sig')
            has_text |= bool(raw.strip())
        if not has_text:
            raise ValueError('Markdown must contain text')
    return delta
