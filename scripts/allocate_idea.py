#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS = ROOT / "submissions"
IDEAS = ROOT / "ideas"
REGISTRY = ROOT / "registry" / "ideas.json"
TZ = timezone(timedelta(hours=3))


def markdown_files(folder):
    return sorted(
        [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".md"],
        key=lambda p: str(p).lower(),
    )


def clean_text(text):
    text = re.sub(r"[`*_>#]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_preview(folder):
    files = markdown_files(folder)
    if not files:
        raise ValueError("Idea folder must contain at least one .md file")
    md = files[0]
    text = md.read_text(encoding="utf-8", errors="replace")
    title = ""
    summary = ""
    lines = text.splitlines()
    for line in lines:
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            title = clean_text(m.group(1))
            break
    if not title:
        for line in lines:
            candidate = clean_text(line)
            if candidate:
                title = candidate[:120]
                break
    if not title:
        title = md.stem
    in_fence = False
    for line in lines:
        s = line.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not s or s.startswith("#"):
            continue
        candidate = clean_text(s)
        if candidate and candidate != title:
            summary = candidate[:240]
            break
    if not summary:
        summary = title
    return title, summary, str(md.relative_to(folder)).replace("\\", "/")


def allocate(src, registry):
    src = src.resolve()
    try:
        rel = src.relative_to(SUBMISSIONS.resolve())
    except ValueError:
        raise ValueError("Submission must be inside submissions/")
    if len(rel.parts) < 2 or not src.is_dir():
        raise ValueError("Submission path must be submissions/<github-user>/<short-name>/")
    owner = rel.parts[0]
    if not markdown_files(src):
        raise ValueError(f"{rel}: at least one .md file is required")

    n = int(registry["next_id"])
    idea_id = f"ORI-{n:06d}"
    now = datetime.now(TZ)
    folder_name = f"{n:06d}_{now:%Y%m%d_%H%M%S}_GMTp3"
    dst = IDEAS / folder_name
    if dst.exists():
        raise ValueError(f"Destination already exists: {dst}")

    shutil.copytree(src, dst)
    title, summary, primary_md = extract_preview(dst)

    registry["ideas"][idea_id] = {
        "owner": owner,
        "title": title,
        "summary": summary,
        "primary_md": primary_md,
        "created_at": now.isoformat(timespec="seconds"),
        "timezone": "GMT+3",
        "status": "active",
        "path": f"ideas/{folder_name}",
    }
    registry["next_id"] = n + 1
    shutil.rmtree(src)
    print(f"Allocated {idea_id} -> ideas/{folder_name} (owner: {owner})")


def pending_folders():
    result = []
    if not SUBMISSIONS.exists():
        return result
    for owner_dir in sorted(SUBMISSIONS.iterdir(), key=lambda p: p.name.lower()):
        if not owner_dir.is_dir():
            continue
        for idea_dir in sorted(owner_dir.iterdir(), key=lambda p: p.name.lower()):
            if idea_dir.is_dir():
                result.append(idea_dir)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("submission", nargs="?", help="submissions/<github-user>/<short-name>")
    ap.add_argument("--all", action="store_true", help="allocate all pending submission folders")
    args = ap.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    targets = pending_folders() if args.all else ([ROOT / args.submission] if args.submission else [])
    if not targets:
        print("No pending submissions.")
        return

    for src in targets:
        allocate(src, registry)

    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)


if __name__ == "__main__":
    main()
