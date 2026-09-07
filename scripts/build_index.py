#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import re

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "ideas.json"
INDEX = ROOT / "ideas" / "README.md"
TZ = timezone(timedelta(hours=3))


def md_files(folder):
    return sorted([p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".md"], key=lambda p: str(p).lower())


def clean(text):
    text = re.sub(r"[`*_>#]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def preview(folder):
    files = md_files(folder)
    if not files:
        return "Untitled Idea", "No Markdown preview available", ""
    md = files[0]
    lines = md.read_text(encoding="utf-8", errors="replace").splitlines()
    title = ""
    for line in lines:
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            title = clean(m.group(1))
            break
    if not title:
        for line in lines:
            if clean(line):
                title = clean(line)[:120]
                break
    if not title:
        title = md.stem
    summary = ""
    in_fence = False
    for line in lines:
        s = line.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not s or s.startswith("#"):
            continue
        candidate = clean(s)
        if candidate and candidate != title:
            summary = candidate[:240]
            break
    return title, summary or title, str(md.relative_to(folder)).replace("\\", "/")


def esc(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    now = datetime.now(TZ).isoformat(timespec="seconds")
    active = []

    for idea_id, item in registry.get("ideas", {}).items():
        path = item.get("path")
        folder = ROOT / path if path else None
        if item.get("status") != "deleted" and (not folder or not folder.exists()):
            item["status"] = "deleted"
            item["deleted_at"] = now
            continue
        if item.get("status") == "deleted":
            continue
        title, summary, primary_md = preview(folder)
        item["title"] = title
        item["summary"] = summary
        item["primary_md"] = primary_md
        active.append((idea_id, item))

    active.sort(key=lambda pair: int(pair[0].split("-")[-1]), reverse=True)

    lines = [
        "# Research Idea Index",
        "",
        "This page shows a short preview before you open an Idea folder. Titles and summaries are extracted automatically from Markdown files.",
        "",
        "| ID | Title | Preview | Owner | Created (GMT+3) | Status |",
        "|---|---|---|---|---|---|",
    ]

    for idea_id, item in active:
        folder_name = Path(item["path"]).name
        title_link = f"[{esc(item.get('title'))}]({folder_name}/)"
        lines.append(
            f"| {esc(idea_id)} | {title_link} | {esc(item.get('summary'))} | "
            f"@{esc(item.get('owner'))} | {esc(item.get('created_at'))} | {esc(item.get('status'))} |"
        )

    if not active:
        lines.append("| — | No official ideas yet | — | — | — | — |")

    lines += ["", "Deleted Idea IDs remain reserved in `registry/ideas.json` and are never reused."]
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
