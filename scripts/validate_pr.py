#!/usr/bin/env python3
from pathlib import Path, PurePosixPath
import argparse, os, re, subprocess, sys, yaml

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_RE = re.compile(r"^\d{6}_\d{8}_\d{6}_GMTp3$")
ID_RE = re.compile(r"^ORI-\d{6}$")
BLOCKED_EXT = {".exe", ".dll", ".scr", ".msi", ".com", ".bat", ".cmd", ".ps1", ".apk", ".dmg", ".iso"}

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)

def read_yaml_at(ref, path):
    try:
        return yaml.safe_load(git("show", f"{ref}:{path}")) or {}
    except subprocess.CalledProcessError:
        return None

def maintainers():
    data = yaml.safe_load((ROOT / "config/maintainers.yml").read_text(encoding="utf-8")) or {}
    return set(data.get("maintainers") or [])

def owner_of_official(base, folder):
    meta = read_yaml_at(base, f"ideas/{folder}/metadata.yml")
    return ((meta or {}).get("owner") or {}).get("github") if meta else None

def validate_metadata(meta, official=False):
    errors = []
    for k in ["title", "summary", "owner", "fields", "keywords", "originality", "ai"]:
        if not meta.get(k): errors.append(f"missing required field: {k}")
    owner = ((meta.get("owner") or {}).get("github") or "").strip()
    if not owner: errors.append("owner.github is required")
    orig = meta.get("originality") or {}
    if orig.get("declaration") is not True: errors.append("originality.declaration must be true")
    for k in ["search_date", "sources", "queries", "closest_public_work", "differentiation"]:
        if not orig.get(k): errors.append(f"originality.{k} is required")
    if "assisted" not in (meta.get("ai") or {}): errors.append("ai.assisted must be declared")
    if official:
        if not ID_RE.match(str(meta.get("id") or "")): errors.append("official id must match ORI-000001")
        created = str(meta.get("created_at") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+03:00$", created): errors.append("created_at must use fixed +03:00")
        if meta.get("timezone") != "GMT+3": errors.append("timezone must be GMT+3")
    return errors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--actor", default=os.getenv("GITHUB_ACTOR", ""))
    args = ap.parse_args()
    actor = args.actor.strip()
    if not actor: raise SystemExit("Missing GitHub actor")
    is_maintainer = actor in maintainers()
    out = git("diff", "--name-status", f"{args.base}...{args.head}")
    errors, metas = [], set()
    for line in out.splitlines():
        parts = line.split("\t")
        for path in parts[1:]:
            pp = PurePosixPath(path)
            if pp.suffix.lower() in BLOCKED_EXT:
                errors.append(f"blocked executable/binary extension: {path}")
            if path.endswith("metadata.yml"): metas.add(path)
            if is_maintainer: continue
            p = pp.parts
            if len(p) >= 3 and p[0] == "submissions":
                if p[1] != actor: errors.append(f"{actor} may not modify submission owned by {p[1]}: {path}")
                continue
            if len(p) >= 2 and p[0] == "ideas" and OFFICIAL_RE.match(p[1]):
                base_owner = owner_of_official(args.base, p[1])
                if base_owner is None: errors.append(f"non-maintainers may not create official numbered folders directly: {path}")
                elif base_owner != actor: errors.append(f"{actor} may not modify idea owned by {base_owner}: {path}")
                continue
            errors.append(f"non-maintainer may not modify protected/core path: {path}")
    for path in metas:
        p = ROOT / path
        if not p.exists(): continue
        meta = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        official = len(PurePosixPath(path).parts) >= 2 and PurePosixPath(path).parts[0] == "ideas"
        errors += [f"{path}: {e}" for e in validate_metadata(meta, official)]
        if not is_maintainer:
            owner = ((meta.get("owner") or {}).get("github") or "").strip()
            if owner and owner != actor: errors.append(f"{path}: owner.github must equal PR actor ({actor})")
    if errors:
        print("ORI validation failed:")
        for e in errors: print(" -", e)
        sys.exit(1)
    print("ORI validation passed.")

if __name__ == "__main__":
    main()
