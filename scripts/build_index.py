#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, yaml

ROOT = Path(__file__).resolve().parents[1]
IDEAS = ROOT / "ideas"
REGISTRY = ROOT / "registry" / "ideas.json"
INDEX = IDEAS / "README.md"
TZ = timezone(timedelta(hours=3))

def esc(v):
    return str(v or "").replace("|", "\\|").replace("\n", " ").strip()

def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records, active_paths = [], set()
    for folder in sorted(IDEAS.iterdir()):
        if not folder.is_dir():
            continue
        meta_path = folder / "metadata.yml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        idea_id = meta.get("id")
        if not idea_id:
            continue
        active_paths.add(folder.name)
        owner = ((meta.get("owner") or {}).get("github")) or ""
        record = {
            "id": idea_id,
            "title": meta.get("title", ""),
            "summary": meta.get("summary", ""),
            "fields": ", ".join(meta.get("fields") or []),
            "owner": owner,
            "created_at": meta.get("created_at", ""),
            "status": meta.get("status", "active"),
            "folder": folder.name,
        }
        records.append(record)
        registry["ideas"].setdefault(idea_id, {})
        registry["ideas"][idea_id].update({
            "owner": owner,
            "title": record["title"],
            "created_at": record["created_at"],
            "status": record["status"],
            "path": f"ideas/{folder.name}",
        })
    now = datetime.now(TZ).isoformat(timespec="seconds")
    for idea_id, item in registry["ideas"].items():
        path = item.get("path", "")
        folder = Path(path).name if path else ""
        if item.get("status") != "deleted" and folder and folder not in active_paths:
            item["status"] = "deleted"
            item["deleted_at"] = now
    records.sort(key=lambda x: int(x["id"].split("-")[-1]), reverse=True)
    lines = [
        "# Research Idea Index", "",
        "Search this page before opening folders. Each title links to the complete idea record.", "",
        "| ID | Title | Summary | Field | Owner | Created (GMT+3) | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in records:
        title = f"[{esc(r['title'])}]({r['folder']}/)"
        lines.append(f"| {esc(r['id'])} | {title} | {esc(r['summary'])} | {esc(r['fields'])} | @{esc(r['owner'])} | {esc(r['created_at'])} | {esc(r['status'])} |")
    if not records:
        lines.append("| — | No official ideas allocated yet | — | — | — | — | — |")
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
