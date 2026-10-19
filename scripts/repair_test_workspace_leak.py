#!/usr/bin/env python3
"""Repair chats whose working folder points into a pytest temp tree.

Background: in July to September 2026 a test run leaked its temporary
workspace (/tmp/hermes-webui-tests/webui-test-*/test-workspace) into the live
settings.json and, from there, into per-profile last_workspace.txt files. New
chats inherited it. Those chats are REAL conversations by real people (some
have hundreds of messages); only their working-folder field is wrong, and the
folder no longer exists. So this script never deletes a chat: it points the
working folder back to a real one and keeps a backup of every value it changes.

Targets (anything containing the marker, default "/hermes-webui-tests/"):
  * sessions/_index.json rows      -> "workspace"
  * sessions/<id>.json files        -> top-level "workspace"
  * <profile>/webui_state/last_workspace.txt (default profile: <state>/)
  * settings.json "default_workspace"

New folder per chat: the profile's default (<profile home>/config.yaml
workspace / terminal.cwd), otherwise the WebUI default workspace from
settings.json, otherwise $HOME. Not the owner's last-used folder, which
changes daily.

Modes:
  (default)      dry run, read only: list what would change, with counts
  --apply        write the changes; backup + log under
                 <state>/maintenance-backups/test-workspace-repair-<stamp>/
  --restore DIR  put every backed-up value back (exact file copies)

Idempotent: a second --apply finds nothing left to change. Stop the WebUI
before --apply / --restore (it rewrites the same files).
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

MARKER = "/hermes-webui-tests/"


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


def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _atomic_write_text(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _slug(email: str) -> str:
    import re
    return re.sub(r"[^a-z0-9._@+-]", "_", str(email).strip().lower())[:160] or "unknown"


def _profile_state_dir(state: Path, hermes: Path, profile: str) -> Path:
    return state if profile in ("", "default", None) else hermes / "profiles" / profile / "webui_state"


def _profile_config_workspace(hermes: Path, profile: str) -> str | None:
    home = hermes if profile in ("", "default", None) else hermes / "profiles" / profile
    try:
        import yaml  # type: ignore
        cfg = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    for value in (cfg.get("workspace"), cfg.get("default_workspace"),
                  (cfg.get("terminal") or {}).get("cwd") if isinstance(cfg.get("terminal"), dict) else None):
        if value and str(value) not in (".", "") and os.path.isdir(os.path.expanduser(str(value))):
            return os.path.realpath(os.path.expanduser(str(value)))
    return None


def replacement(state: Path, hermes: Path, profile: str, owner: str, marker: str) -> tuple[str, str]:
    """(new folder, reason) for one chat."""
    # Deliberately NOT the owner's last-used folder: that changes every day and
    # would file old chats under whatever they happen to work on now.
    v = _profile_config_workspace(hermes, profile)
    if v and marker not in v:
        return v, "profile default folder (config.yaml)"
    settings = _read_json(state / "settings.json", {}) or {}
    v = str(settings.get("default_workspace") or "")
    if v and marker not in v and os.path.isdir(v):
        return v, "WebUI default folder (settings.json)"
    return str(Path.home()), "home folder (no other default found)"


def scan(state: Path, hermes: Path, marker: str) -> dict:
    index_path = state / "sessions" / "_index.json"
    index = _read_json(index_path, []) or []
    chats = []
    for row in index:
        if isinstance(row, dict) and marker in str(row.get("workspace") or ""):
            profile = row.get("profile") or "default"
            owner = str(row.get("owner_email") or "").strip().lower()
            new, why = replacement(state, hermes, profile, owner, marker)
            sfile = state / "sessions" / f"{row.get('session_id')}.json"
            chats.append({"session_id": row.get("session_id"), "profile": profile, "owner": owner,
                          "title": (row.get("title") or "")[:80], "messages": row.get("message_count"),
                          "archived": bool(row.get("archived")), "old": row.get("workspace"), "new": new,
                          "reason": why, "session_file": str(sfile) if sfile.is_file() else None})
    profile_files = []
    candidates = [("default", state / "last_workspace.txt")] + [
        (p.parent.parent.name, p) for p in sorted((hermes / "profiles").glob("*/webui_state/last_workspace.txt"))]
    for profile, f in candidates:
        try:
            v = f.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            continue
        if marker in v:
            profile_files.append({"profile": profile, "file": str(f), "old": v, "action": "remove"})
    settings = _read_json(state / "settings.json", {}) or {}
    settings_fix = None
    if marker in str(settings.get("default_workspace") or ""):
        settings_fix = {"file": str(state / "settings.json"), "old": settings.get("default_workspace"),
                        "new": str(Path.home())}
    return {"index": str(index_path), "chats": chats, "profile_last_workspace": profile_files,
            "settings": settings_fix}


def apply(state: Path, hermes: Path, marker: str) -> dict:
    plan = scan(state, hermes, marker)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = state / "maintenance-backups" / f"test-workspace-repair-{stamp}"
    dest.mkdir(parents=True, exist_ok=False)
    manifest, log = [], []

    def keep(src: Path):
        rel = f"{len(manifest):04d}-{src.name}"
        shutil.copy2(src, dest / rel)
        manifest.append({"source": str(src), "backup": str(dest / rel)})

    changed_files = 0
    for chat in plan["chats"]:
        if chat["session_file"]:
            p = Path(chat["session_file"])
            raw = p.read_text(encoding="utf-8")
            data = json.loads(raw)
            dumper = _same_format_dumper(raw, data)
            if dumper is None:
                log.append({**chat, "result": "skipped: file format not reproducible, left untouched"})
                continue
            keep(p)
            data["workspace"] = chat["new"]
            _atomic_write_text(p, dumper(data))
            changed_files += 1
        log.append({**chat, "result": "updated"})
    if plan["chats"]:
        ip = Path(plan["index"])
        raw = ip.read_text(encoding="utf-8")
        index = json.loads(raw)
        keep(ip)
        new_by_id = {c["session_id"]: c["new"] for c in plan["chats"]}
        for row in index:
            if isinstance(row, dict) and row.get("session_id") in new_by_id and marker in str(row.get("workspace") or ""):
                row["workspace"] = new_by_id[row["session_id"]]
        _atomic_write_text(ip, _dump(index) + ("\n" if raw.endswith("\n") else ""))
    for item in plan["profile_last_workspace"]:
        p = Path(item["file"])
        keep(p)
        p.unlink()
        log.append({**item, "result": "removed (falls back to the profile default)"})
    if plan["settings"]:
        p = Path(plan["settings"]["file"])
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
        keep(p)
        data["default_workspace"] = plan["settings"]["new"]
        _atomic_write_text(p, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        log.append({**plan["settings"], "result": "updated"})
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (dest / "repair-log.jsonl").open("w", encoding="utf-8") as fh:
        for entry in log:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"backup": str(dest), "chats": len(plan["chats"]), "session_files_changed": changed_files,
            "profile_files_removed": len(plan["profile_last_workspace"]), "settings_fixed": bool(plan["settings"])}


def restore(backup_dir: Path) -> dict:
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest:
        src, dst = Path(item["backup"]), Path(item["source"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return {"restored_files": len(manifest)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", default=os.path.expanduser("~/.hermes/webui"))
    ap.add_argument("--hermes", default=os.path.expanduser("~/.hermes"))
    ap.add_argument("--marker", default=MARKER)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore")
    ap.add_argument("--list", action="store_true", help="print every item in the dry run")
    args = ap.parse_args()
    state, hermes = Path(args.state), Path(args.hermes)
    if args.restore:
        print(json.dumps(restore(Path(args.restore)), indent=1))
        return 0
    if args.apply:
        print(json.dumps(apply(state, hermes, args.marker), indent=1))
        return 0
    plan = scan(state, hermes, args.marker)
    from collections import Counter
    summary = {
        "dry_run": True,
        "chats": len(plan["chats"]),
        "chats_with_session_file": sum(1 for c in plan["chats"] if c["session_file"]),
        "archived": sum(1 for c in plan["chats"] if c["archived"]),
        "messages_total": sum(int(c["messages"] or 0) for c in plan["chats"]),
        "by_profile_owner": {f"{k[0]} / {k[1]}": v for k, v in Counter((c["profile"], c["owner"]) for c in plan["chats"]).most_common()},
        "new_folder_reasons": dict(Counter(c["reason"] for c in plan["chats"])),
        "profile_last_workspace_files": [p["file"] for p in plan["profile_last_workspace"]],
        "settings_default_workspace_leaked": bool(plan["settings"]),
    }
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    if args.list:
        for c in plan["chats"]:
            print(f"{c['session_id']}\t{c['profile']}\t{c['owner']}\t{c['messages']}\t{c['new']}\t{c['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
