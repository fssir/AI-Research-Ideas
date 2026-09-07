#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, json, shutil, subprocess, yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "ideas.json"
IDEAS = ROOT / "ideas"
TZ = timezone(timedelta(hours=3))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("submission", help="Path like submissions/<github-user>/<slug>")
    args = p.parse_args()
    src = (ROOT / args.submission).resolve()
    submissions_root = (ROOT / "submissions").resolve()
    if submissions_root not in src.parents or not src.is_dir():
        raise SystemExit("Submission must be an existing folder inside submissions/")
    meta_path = src / "metadata.yml"
    if not meta_path.exists():
        raise SystemExit("metadata.yml is required")
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    owner = ((meta.get("owner") or {}).get("github") or "").strip()
    if not owner:
        raise SystemExit("owner.github is required")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    n = int(registry["next_id"])
    idea_id = f"ORI-{n:06d}"
    now = datetime.now(TZ)
    folder_name = f"{n:06d}_{now:%Y%m%d_%H%M%S}_GMTp3"
    dst = IDEAS / folder_name
    if dst.exists():
        raise SystemExit(f"Destination already exists: {dst}")
    shutil.copytree(src, dst)
    meta["id"] = idea_id
    meta["created_at"] = now.isoformat(timespec="seconds")
    meta["timezone"] = "GMT+3"
    meta["status"] = "active"
    meta["repository_path"] = f"ideas/{folder_name}"
    (dst / "metadata.yml").write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), encoding="utf-8")
    registry["ideas"][idea_id] = {"owner": owner, "title": meta.get("title", ""), "created_at": meta["created_at"], "status": "active", "path": f"ideas/{folder_name}"}
    registry["next_id"] = n + 1
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.rmtree(src)
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print(f"Allocated {idea_id} -> ideas/{folder_name}")

if __name__ == "__main__":
    main()
