#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter
import json
import re

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / ".github" / "ori" / "registry" / "ideas.json"
HUMAN_INDEX = ROOT / "ideas" / "README.md"
MACHINE_INDEX = ROOT / ".github" / "ori" / "index" / "ideas.json"
TZ = timezone(timedelta(hours=3))

TAXONOMY = {
    "Artificial Intelligence / Machine Learning": [
        "artificial intelligence", "machine learning", "deep learning", "neural network",
        "transformer", "large language model", "llm", "reinforcement learning",
        "computer vision", "natural language processing", "diffusion model",
        "人工智能", "机器学习", "深度学习", "神经网络", "大语言模型", "强化学习", "计算机视觉"
    ],
    "Robotics / Autonomous Systems": [
        "robot", "robotics", "autonomous system", "autonomous vehicle", "slam",
        "path planning", "motion planning", "manipulation", "drone", "uav",
        "机器人", "自主系统", "无人机", "路径规划", "运动规划"
    ],
    "Mechanical / Aerospace Engineering": [
        "mechanical engineering", "wankel", "rotary engine", "engine", "combustion",
        "propulsion", "aerodynamic", "airfoil", "turbine", "mechanical design",
        "转子发动机", "发动机", "燃烧", "推进", "气动", "飞行器", "机械设计"
    ],
    "Energy / Power Systems": [
        "battery", "energy management", "power system", "powertrain", "hybrid power",
        "fuel cell", "microgrid", "renewable energy", "电池", "能量管理", "动力系统",
        "混合动力", "燃料电池", "能源"
    ],
    "Control / Optimization": [
        "control system", "controller", "model predictive control", "mpc", "pid", "lqr",
        "optimization", "genetic algorithm", "particle swarm", "pso", "dynamic programming",
        "控制系统", "控制器", "模型预测控制", "优化", "遗传算法", "粒子群", "动态规划"
    ],
    "Mathematics / Statistics": [
        "mathematics", "mathematical", "theorem", "proof", "statistics", "statistical",
        "stochastic", "deterministic", "equation", "numerical method",
        "数学", "定理", "证明", "统计", "随机", "确定性", "方程", "数值方法"
    ],
    "Physics": [
        "physics", "quantum", "thermodynamics", "fluid dynamics", "particle physics",
        "optics", "electromagnetism", "物理", "量子", "热力学", "流体力学", "光学"
    ],
    "Chemistry / Materials": [
        "chemistry", "chemical", "catalyst", "catalysis", "material", "materials science",
        "alloy", "polymer", "nanomaterial", "化学", "催化", "材料", "合金", "聚合物", "纳米材料"
    ],
    "Biology / Medicine": [
        "biology", "biological", "biomedical", "medical", "medicine", "protein", "gene",
        "genomics", "drug discovery", "clinical", "生物", "生物医学", "医学", "蛋白", "基因", "药物"
    ],
    "Computer Science / Software": [
        "computer science", "algorithm", "software", "database", "compiler", "cybersecurity",
        "distributed system", "graph algorithm", "计算机科学", "算法", "软件", "数据库", "编译器", "网络安全"
    ],
    "Earth / Environmental Science": [
        "climate", "environment", "environmental", "geology", "atmospheric", "ocean",
        "earth science", "气候", "环境", "地质", "大气", "海洋", "地球科学"
    ],
    "Social / Economic Sciences": [
        "economics", "economic", "finance", "financial", "social science", "psychology",
        "behavioral", "经济", "金融", "社会科学", "心理学", "行为"
    ],
}

STOPWORDS = {
    "about", "after", "again", "also", "among", "another", "based", "because", "been",
    "before", "being", "between", "both", "could", "data", "does", "each", "from", "have",
    "idea", "into", "large", "more", "model", "other", "paper", "prompt", "research", "result",
    "results", "should", "study", "system", "than", "that", "their", "there", "these", "they",
    "this", "through", "using", "were", "what", "when", "where", "which", "while", "with",
    "would", "method", "methods", "analysis", "approach", "proposed", "work", "will", "such"
}


def esc(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def markdown_files(folder):
    files = list(folder.rglob("*.md"))
    return sorted(files, key=lambda p: (p.name.lower() != "readme.md", str(p.relative_to(folder)).lower()))


def strip_markdown(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    cleaned = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(("**ID:**", "**Author:**", "**Created:**", "**Source issue:**")):
            continue
        s = re.sub(r"^#{1,6}\s*", "", s)
        s = re.sub(r"[*_>`~]", "", s)
        cleaned.append(s)
    return re.sub(r"\s+", " ", " ".join(cleaned)).strip()


def collect_text(folder):
    files = markdown_files(folder)
    if not files:
        return [], "", "", "Untitled Idea"

    texts = []
    title = None
    first_clean = ""
    total_chars = 0
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")[:50000]
        if title is None:
            match = re.search(r"^#\s+(.+)$", raw, re.M)
            if match:
                title = match.group(1).strip()
        clean = strip_markdown(raw)
        if not first_clean and clean:
            first_clean = clean
        if clean and total_chars < 250000:
            remaining = 250000 - total_chars
            texts.append(clean[:remaining])
            total_chars += min(len(clean), remaining)

    if not title:
        title = files[0].stem
    return files, "\n".join(texts), first_clean, title


def infer_fields(text):
    lower = text.lower()
    scores = []
    for field, terms in TAXONOMY.items():
        score = 0
        for term in terms:
            count = lower.count(term.lower())
            if count:
                score += count * (3 if " " in term or any("\u4e00" <= c <= "\u9fff" for c in term) else 1)
        if score:
            scores.append((score, field))
    if not scores:
        return ["Interdisciplinary / Other"]
    scores.sort(reverse=True)
    best = scores[0][0]
    fields = [field for score, field in scores if score >= max(2, best * 0.55)][:2]
    return fields or [scores[0][1]]


def infer_keywords(text, title, fields, limit=8):
    lower = text.lower()
    candidates = Counter()

    # Prefer meaningful multi-word/bilingual domain phrases already present in the Idea.
    for field, terms in TAXONOMY.items():
        field_bonus = 3 if field in fields else 1
        for term in terms:
            count = lower.count(term.lower())
            if count:
                candidates[term.lower()] += count * field_bonus * (3 if " " in term else 2)

    # Add frequent informative English terms; title occurrences receive extra weight.
    title_words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9+.-]{2,}", title)}
    words = re.findall(r"[A-Za-z][A-Za-z0-9+.-]{2,}", text)
    for word in words:
        key = word.lower().strip(".-")
        if len(key) < 3 or key in STOPWORDS or key.isdigit():
            continue
        candidates[key] += 3 if key in title_words else 1

    selected = []
    for term, _ in candidates.most_common(40):
        if any(term == x or term in x or x in term for x in selected):
            continue
        selected.append(term)
        if len(selected) >= limit:
            break
    return selected


def summarize(first_clean, all_text, limit=280):
    source = first_clean or all_text
    source = re.sub(r"\s+", " ", source).strip()
    if len(source) <= limit:
        return source
    cut = source[:limit].rsplit(" ", 1)[0].strip()
    return (cut or source[:limit]).rstrip(".,;:") + "…"


def analyze(folder):
    files, all_text, first_clean, title = collect_text(folder)
    fields = infer_fields(f"{title}\n{all_text}")
    keywords = infer_keywords(f"{title}\n{all_text}", title, fields)
    summary = summarize(first_clean, all_text)
    rel_files = [str(p.relative_to(folder)).replace("\\", "/") for p in files]
    return {
        "title": title,
        "summary": summary,
        "fields": fields,
        "keywords": keywords,
        "markdown_files": rel_files,
    }


def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    now = datetime.now(TZ).isoformat(timespec="seconds")
    rows = []
    machine_rows = []

    for idea_id, item in registry.get("ideas", {}).items():
        folder = ROOT / item.get("path", "")
        if item.get("status") != "deleted" and not folder.exists():
            item["status"] = "deleted"
            item["deleted_at"] = now
        if item.get("status") == "deleted":
            continue

        meta = analyze(folder)
        item.update(meta)
        serial = int(idea_id.split("-")[-1])
        rows.append((serial, idea_id, item))
        machine_rows.append({
            "id": idea_id,
            "title": meta["title"],
            "summary": meta["summary"],
            "fields": meta["fields"],
            "keywords": meta["keywords"],
            "owner": item.get("owner", ""),
            "created_at": item.get("created_at", ""),
            "path": item.get("path", ""),
            "markdown_files": meta["markdown_files"],
        })

    rows.sort(reverse=True)
    machine_rows.sort(key=lambda x: int(x["id"].split("-")[-1]), reverse=True)

    lines = [
        "# Research Ideas", "",
        "Newest Ideas are listed first. Search this page by title, field, keyword, or summary. **Click an Idea title to open its complete folder and browse all code, papers, data, figures, and other files.**", "",
        "| Idea | Field | Keywords | Summary |",
        "|---|---|---|---|",
    ]
    if not rows:
        lines.append("| — | No Ideas published yet | — | — |")
    for _, idea_id, item in rows:
        folder = Path(item["path"]).name
        title = f"{idea_id} · {item.get('title', 'Untitled Idea')}"
        field = "; ".join(item.get("fields") or ["Interdisciplinary / Other"])
        keywords = ", ".join(item.get("keywords") or []) or "—"
        summary = item.get("summary") or "—"
        owner = item.get("owner") or "unknown"
        created = item.get("created_at") or ""
        summary_with_meta = f"{summary}  —  @{owner} · {created}"
        lines.append(f"| [{esc(title)}]({folder}/) | {esc(field)} | {esc(keywords)} | {esc(summary_with_meta)} |")

    HUMAN_INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    MACHINE_INDEX.parent.mkdir(parents=True, exist_ok=True)
    MACHINE_INDEX.write_text(json.dumps({
        "schema_version": 1,
        "generated_at": now,
        "count": len(machine_rows),
        "ideas": machine_rows,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
