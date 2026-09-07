#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, re

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / ".github" / "ori" / "registry" / "ideas.json"
INDEX = ROOT / "ideas" / "README.md"
TZ = timezone(timedelta(hours=3))


def esc(v):
    return str(v or "").replace("|", "\\|").replace("\n", " ").strip()


def extract(folder):
    files = sorted(folder.rglob("*.md"))
    if not files:
        return "Untitled Idea", ""
    text = files[0].read_text(encoding="utf-8", errors="replace")
    title = next((m.group(1).strip() for m in re.finditer(r"^#\s+(.+)$", text, re.M)), files[0].stem)
    clean = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("**ID:**") or s.startswith("**Author:**") or s.startswith("**Created:**") or s.startswith("**Source issue:**"):
            continue
        clean.append(re.sub(r"[*_>`~-]", "", s))
    return title, re.sub(r"\s+", " ", " ".join(clean)).strip()[:240]


def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    now = datetime.now(TZ).isoformat(timespec="seconds")
    rows = []
    for idea_id, item in registry.get("ideas", {}).items():
        folder = ROOT / item.get("path", "")
        if item.get("status") != "deleted" and not folder.exists():
            item["status"] = "deleted"
            item["deleted_at"] = now
        if item.get("status") == "deleted":
            continue
        title, summary = extract(folder)
        item["title"], item["summary"] = title, summary
        rows.append((int(idea_id.split("-")[-1]), idea_id, item))

    rows.sort(reverse=True)
    lines = [
        "# Research Ideas", "",
        "Browse the public Idea library. The summary lets you see the approximate content before opening a folder.", "",
        "| ID | Title | Summary | Owner | Created (GMT+3) |",
        "|---|---|---|---|---|"
    ]
    if not rows:
        lines.append("| — | No Ideas published yet | — | — | — |")
    for _, idea_id, item in rows:
        folder = Path(item["path"]).name
        lines.append(f"| {esc(idea_id)} | [{esc(item.get('title'))}]({folder}/) | {esc(item.get('summary'))} | @{esc(item.get('owner'))} | {esc(item.get('created_at'))} |")
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
