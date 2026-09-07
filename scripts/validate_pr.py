#!/usr/bin/env python3
from pathlib import Path, PurePosixPath
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_RE = __import__("re").compile(r"^\d{6}_\d{8}_\d{6}_GMTp3$")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)


def maintainers():
    result = set()
    text = (ROOT / "config" / "maintainers.yml").read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            result.add(line[2:].strip())
    return result


def registry_at(ref):
    try:
        return json.loads(git("show", f"{ref}:registry/ideas.json"))
    except Exception:
        return {"ideas": {}}


def official_owner(registry, folder):
    wanted = f"ideas/{folder}"
    for item in registry.get("ideas", {}).values():
        if item.get("path") == wanted and item.get("status") != "deleted":
            return item.get("owner")
    return None


def has_markdown(folder):
    return folder.exists() and any(p.is_file() and p.suffix.lower() == ".md" for p in folder.rglob("*"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--actor", required=True)
    args = ap.parse_args()

    actor = args.actor.strip()
    if actor in maintainers():
        print(f"Platform maintainer/system PR accepted: {actor}")
        return

    registry = registry_at(args.base)
    errors = []
    submission_roots = set()
    official_roots = set()

    diff = git("diff", "--name-status", f"{args.base}...{args.head}")
    for line in diff.splitlines():
        parts = line.split("\t")
        for path in parts[1:]:
            p = PurePosixPath(path).parts

            if len(p) >= 3 and p[0] == "submissions":
                owner = p[1]
                if owner != actor:
                    errors.append(f"{actor} may not modify submission owned by {owner}: {path}")
                submission_roots.add("/".join(p[:3]))
                continue

            if len(p) >= 2 and p[0] == "ideas" and OFFICIAL_RE.match(p[1]):
                owner = official_owner(registry, p[1])
                if owner is None:
                    errors.append(f"New official numbered folders are platform-created only: {path}")
                elif owner != actor:
                    errors.append(f"{actor} may not modify Idea owned by {owner}: {path}")
                official_roots.add("/".join(p[:2]))
                continue

            errors.append(f"Ordinary contributors may not modify platform/core path: {path}")

    for root in submission_roots:
        folder = ROOT / root
        if folder.exists() and not has_markdown(folder):
            errors.append(f"{root} must contain at least one .md file")

    for root in official_roots:
        folder = ROOT / root
        if folder.exists() and not has_markdown(folder):
            errors.append(f"{root} must retain at least one .md file, or delete the entire Idea folder")

    if errors:
        print("Idea access validation failed:")
        for e in errors:
            print(" -", e)
        sys.exit(1)

    print("Idea access validation passed.")


if __name__ == "__main__":
    main()
