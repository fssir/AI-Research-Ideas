#!/usr/bin/env python3
from pathlib import Path, PurePosixPath
import argparse, json, os, subprocess, sys

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / ".github" / "ori" / "registry" / "ideas.json"
MAINTAINERS = ROOT / ".github" / "ori" / "config" / "maintainers.txt"
BLOCKED = {".exe", ".dll", ".scr", ".msi", ".com", ".bat", ".cmd", ".ps1", ".apk", ".dmg", ".iso"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--actor", required=True)
    args = ap.parse_args()
    actor = args.actor.strip()
    maintainers = {x.strip().lower() for x in MAINTAINERS.read_text(encoding="utf-8").splitlines() if x.strip()}
    if actor.lower() in maintainers:
        print("Platform maintainer/bot validation passed.")
        return

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    by_folder = {}
    for idea_id, item in registry.get("ideas", {}).items():
        path = item.get("path", "")
        if path:
            by_folder[Path(path).name] = (idea_id, item)

    errors, touched = [], set()
    diff = git("diff", "--name-status", f"{args.base}...{args.head}")
    for line in diff.splitlines():
        parts = line.split("\t")
        for path in parts[1:]:
            pp = PurePosixPath(path)
            if pp.suffix.lower() in BLOCKED:
                errors.append(f"blocked executable/binary extension: {path}")
            p = pp.parts
            if len(p) < 2 or p[0] != "ideas" or p[1] == "README.md":
                errors.append(f"ordinary contributors may only change their own official Idea folder: {path}")
                continue
            folder = p[1]
            record = by_folder.get(folder)
            if not record:
                errors.append(f"unregistered/new official folder cannot be created directly: {path}")
                continue
            _, item = record
            if str(item.get("owner", "")).lower() != actor.lower():
                errors.append(f"{actor} may not modify Idea owned by {item.get('owner')}: {path}")
                continue
            touched.add(folder)

    for folder in touched:
        full = ROOT / "ideas" / folder
        if full.exists() and not any(full.rglob("*.md")):
            errors.append(f"active Idea must contain at least one .md file: ideas/{folder}")

    if errors:
        print("Idea access validation failed:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("Idea access validation passed.")


if __name__ == "__main__":
    main()
