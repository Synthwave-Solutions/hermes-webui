#!/usr/bin/env python3
"""Point "Home" spaces at /workspace to the profile's real working folder.

/workspace is the folder INSIDE a Docker sandbox (the terminal backend these
profiles used before). Both affected profiles now run with the local backend
and terminal.cwd = <hermes>/profiles/<profile>/workspace, so /workspace does
not exist on the host and the "Home" space (and its project after the
Projects + Spaces merge) points nowhere.

For every profile whose registry has an entry at a missing /workspace while
config.yaml has terminal.backend local with an existing terminal.cwd:
  * the space entry's path becomes terminal.cwd; name, owner and members stay
    exactly the same (no one is added or removed);
  * the space project created by the merge (kind "space", same profile and
    source path) follows: its folder and source_space path are updated;
  * chats of that profile whose working folder is /workspace follow too.
Backups of every file touched, a log, dry run (default), --apply, --restore.
Stop the WebUI before --apply / --restore.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

OLD = "/workspace"


_FORMATS = [dict(indent=2, ensure_ascii=False), dict(ensure_ascii=False), dict(ensure_ascii=True),
            dict(indent=2, ensure_ascii=True)]


def _same_format_dumper(raw: str, data):
    """A dumper that reproduces this file's exact JSON style, or None."""
    for fmt in _FORMATS:
        out = json.dumps(data, **fmt)
        if out == raw or out + "\n" == raw:
            tail = "\n" if raw.endswith("\n") else ""
            return lambda obj, fmt=fmt, tail=tail: json.dumps(obj, **fmt) + tail
    return None


def _read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _write(p: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, p)


def _cwd(hermes: Path, profile: str) -> str | None:
    try:
        import yaml  # type: ignore
        cfg = yaml.safe_load((hermes / "profiles" / profile / "config.yaml").read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    term = cfg.get("terminal") or {}
    if not isinstance(term, dict) or str(term.get("backend") or "local") != "local":
        return None
    cwd = str(term.get("cwd") or "")
    return os.path.realpath(os.path.expanduser(cwd)) if cwd and os.path.isdir(os.path.expanduser(cwd)) else None


def plan(state: Path, hermes: Path) -> list[dict]:
    items = []
    for reg in sorted((hermes / "profiles").glob("*/webui_state/workspaces.json")):
        profile = reg.parent.parent.name
        rows = _read_json(reg, []) or []
        if not any(isinstance(r, dict) and r.get("path") == OLD for r in rows) or os.path.isdir(OLD):
            continue
        new = _cwd(hermes, profile)
        if not new:
            items.append({"profile": profile, "registry": str(reg), "action": "skip",
                          "reason": "no local terminal.cwd to point to"})
            continue
        if any(isinstance(r, dict) and os.path.realpath(str(r.get("path"))) == new for r in rows):
            items.append({"profile": profile, "registry": str(reg), "action": "skip",
                          "reason": f"{new} is already a separate space in this profile"})
            continue
        entry = next(r for r in rows if isinstance(r, dict) and r.get("path") == OLD)
        items.append({"profile": profile, "registry": str(reg), "action": "update", "old": OLD, "new": new,
                      "name": entry.get("name"), "owner_email": entry.get("owner_email"),
                      "members": entry.get("members") or []})
    return items


def apply(state: Path, hermes: Path) -> dict:
    items = [i for i in plan(state, hermes) if i["action"] == "update"]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = state / "maintenance-backups" / f"home-spaces-{stamp}"
    dest.mkdir(parents=True, exist_ok=False)
    manifest, log = [], []

    def keep(src: Path):
        tgt = dest / f"{len(manifest):04d}-{src.name}"
        shutil.copy2(src, tgt)
        manifest.append({"source": str(src), "backup": str(tgt)})

    projects_path = state / "projects.json"
    projects = _read_json(projects_path, []) or []
    index_path = state / "sessions" / "_index.json"
    index = _read_json(index_path, []) or []
    projects_changed = index_changed = False
    for it in items:
        reg = Path(it["registry"])
        raw = reg.read_text(encoding="utf-8")
        rows = json.loads(raw)
        keep(reg)
        for r in rows:
            if isinstance(r, dict) and r.get("path") == OLD:
                r["path"] = it["new"]
        _write(reg, json.dumps(rows, ensure_ascii=False, indent=2))
        log.append({**it, "result": "space updated"})
        for p in projects:
            src = p.get("source_space") if isinstance(p, dict) else None
            if p.get("kind") == "space" and isinstance(src, dict) and src.get("profile") == it["profile"] and src.get("path") == OLD:
                src["path"] = it["new"]
                for f in p.get("folders") or []:
                    if isinstance(f, dict) and f.get("path") == OLD:
                        f["path"] = it["new"]
                projects_changed = True
                log.append({"project_id": p.get("project_id"), "name": p.get("name"), "result": "space project folder updated"})
        for row in index:
            if isinstance(row, dict) and row.get("profile") == it["profile"] and row.get("workspace") == OLD:
                sfile = state / "sessions" / f"{row.get('session_id')}.json"
                if sfile.is_file():
                    sraw = sfile.read_text(encoding="utf-8")
                    data = json.loads(sraw)
                    dumper = _same_format_dumper(sraw, data)
                    if dumper is None:
                        log.append({"session_id": row.get("session_id"), "result": "chat file format not reproducible: index only"})
                    else:
                        keep(sfile)
                        data["workspace"] = it["new"]
                        _write(sfile, dumper(data))
                row["workspace"] = it["new"]
                index_changed = True
                log.append({"session_id": row.get("session_id"), "result": "chat folder updated"})
    if projects_changed:
        keep(projects_path)
        _write(projects_path, json.dumps(projects, ensure_ascii=False, indent=2))
    if index_changed:
        raw = index_path.read_text(encoding="utf-8")
        keep(index_path)
        _write(index_path, _dump(index) + ("\n" if raw.endswith("\n") else ""))
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (dest / "log.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in log), encoding="utf-8")
    return {"backup": str(dest), "spaces_updated": len(items), "log_entries": len(log)}


def restore(backup: Path) -> dict:
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest:
        shutil.copy2(item["backup"], item["source"])
    return {"restored_files": len(manifest)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", default=os.path.expanduser("~/.hermes/webui"))
    ap.add_argument("--hermes", default=os.path.expanduser("~/.hermes"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore")
    args = ap.parse_args()
    state, hermes = Path(args.state), Path(args.hermes)
    if args.restore:
        result = restore(Path(args.restore))
    elif args.apply:
        result = apply(state, hermes)
    else:
        result = {"dry_run": True, "items": plan(state, hermes)}
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
