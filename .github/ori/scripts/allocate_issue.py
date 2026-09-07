#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, os, re, subprocess

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / ".github" / "ori" / "registry" / "ideas.json"
IDEAS = ROOT / "ideas"
TZ = timezone(timedelta(hours=3))


def clean_title(title):
    return re.sub(r"^\[NEW IDEA\]\s*", "", title or "", flags=re.I).strip() or "Untitled Idea"


def section(body, name):
    lines = (body or "").splitlines()
    wanted = f"### {name}".strip().lower()
    out, active = [], False
    for line in lines:
        if line.strip().lower() == wanted:
            active = True
            continue
        if active and line.startswith("### "):
            break
        if active:
            out.append(line)
    return "\n".join(out).strip()


def main():
    title = clean_title(os.environ.get("ISSUE_TITLE", ""))
    body = os.environ.get("ISSUE_BODY", "")
    author = os.environ.get("ISSUE_AUTHOR", "").strip()
    issue_number = os.environ.get("ISSUE_NUMBER", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not author:
        raise SystemExit("Missing issue author")

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    n = int(registry["next_id"])
    idea_id = f"ORI-{n:06d}"
    now = datetime.now(TZ)
    folder = f"{n:06d}_{now:%Y%m%d_%H%M%S}_GMTp3"
    path = IDEAS / folder
    path.mkdir(parents=True, exist_ok=False)

    description = section(body, "Idea description") or body.strip()
    prompt = section(body, "Optional prompt for AI")
    readme = [
        f"# {title}", "",
        f"**ID:** {idea_id}  ",
        f"**Author:** @{author}  ",
        f"**Created:** {now.isoformat(timespec='seconds')} (GMT+3)  ",
        f"**Source issue:** #{issue_number}", "",
        "## Idea", "", description or "No description provided.", ""
    ]
    if prompt and prompt.lower() != "_no response_":
        readme += ["## Prompt for AI", "", prompt, ""]
    path.joinpath("README.md").write_text("\n".join(readme), encoding="utf-8")

    summary = re.sub(r"\s+", " ", re.sub(r"[#*_>`~-]", "", description)).strip()[:240]
    registry["ideas"][idea_id] = {
        "owner": author,
        "title": title,
        "summary": summary,
        "created_at": now.isoformat(timespec="seconds"),
        "status": "active",
        "path": f"ideas/{folder}",
        "source_issue": int(issue_number) if issue_number.isdigit() else issue_number
    }
    registry["next_id"] = n + 1
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(["python", str(ROOT / ".github" / "ori" / "scripts" / "build_index.py")], check=True)
    print(f"Allocated {idea_id} -> ideas/{folder}")


if __name__ == "__main__":
    main()
