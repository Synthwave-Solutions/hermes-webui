#!/usr/bin/env python3
"""Bot-owned scheduled jobs: report, apply and restore (18 Oct 2026).

The owning bot of a scheduled job is the profile whose cron store holds it
(api/cron_bots.py): ``<hermes>/cron/jobs.json`` is SynthPulse (``default``),
``<hermes>/profiles/<bot>/cron/jobs.json`` is that bot. Every existing job
therefore already has an owner and needs no new field. This script shows the
numbers and the rows that point at another bot:

* ``legacy_profile``: the job carries the old per-job ``profile`` override
  naming another existing bot. The WebUI's Run now ran it as that bot while
  the scheduler ran it as the store's bot; ``apply`` moves it to the named
  bot's store and clears the override, so both agree.
* ``missing_profile``: the override names a bot that no longer exists
  (reported; ``apply`` clears the override, the job stays where it runs).
* ``origin_other_bot``: made in a WebUI chat of another bot than the store's
  (reported only; ``--move-origin-mismatch`` moves them to the chat's bot).
* ``origin_chat_missing``: the WebUI chat it was made in is gone (its results
  will go to its job chat).
* ``no_person``: nobody to report to (no owner_email, no WebUI creator).
* ``duplicate_id``: the same job id in two stores.

Commands (nothing is written without ``apply``):

  plan     print per-bot counts and the findings above (the dry run)
  apply    back up every store it changes (and the saved run output it moves)
           to ``--backup-dir``, then move/clear as above under each store's
           ``.jobs.lock``; writes ``manifest.json`` there
  restore  put the backed-up jobs.json files back from ``--backup-dir``

Run ``plan`` against a copy first: ``--hermes /path/to/copy`` and
``--sessions /path/to/copy/webui/sessions``. ``apply`` on live data belongs in
a maintenance window with the gateway and the WebUI stopped.
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import fcntl
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = "default"


def _read_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def _jobs_of(data) -> list:
    jobs = data.get("jobs") if isinstance(data, dict) else data
    return [j for j in jobs if isinstance(j, dict)] if isinstance(jobs, list) else []


def stores(hermes: Path) -> list[tuple[str, Path]]:
    """``(bot, home)`` for the root and every profile directory, root first."""
    out = [(ROOT, hermes)]
    profiles = hermes / "profiles"
    if profiles.is_dir():
        for home in sorted(p for p in profiles.iterdir() if p.is_dir() and not p.name.startswith(".")):
            out.append((home.name, home))
    return out


def _norm_profile(value, bots: set) -> str:
    raw = str(value or "").strip()
    if not raw or raw == ROOT:
        return ROOT
    return raw


def _session(sessions: Path | None, sid: str):
    if not sessions or not sid or "/" in sid or ".." in sid:
        return None
    return _read_json(sessions / f"{sid}.json", None)


def plan(hermes: Path, sessions: Path | None, move_origin_mismatch: bool = False) -> dict:
    bots = [name for name, _home in stores(hermes)]
    bot_set = set(bots)
    counts = collections.Counter()
    enabled = collections.Counter()
    findings = collections.defaultdict(list)
    moves = []
    clears = []
    seen_ids = {}
    for bot, home in stores(hermes):
        path = home / "cron" / "jobs.json"
        if not path.exists():
            continue
        for job in _jobs_of(_read_json(path, {})):
            jid = str(job.get("id") or "")
            counts[bot] += 1
            if job.get("enabled") is not False:
                enabled[bot] += 1
            row = {"bot": bot, "job_id": jid, "name": job.get("name")}
            if jid in seen_ids:
                findings["duplicate_id"].append(dict(row, other_bot=seen_ids[jid]))
            seen_ids.setdefault(jid, bot)
            legacy = str(job.get("profile") or "").strip()
            if legacy:
                target = _norm_profile(legacy, bot_set)
                if target not in bot_set:
                    findings["missing_profile"].append(dict(row, profile=legacy))
                    clears.append(dict(row, profile=legacy))
                elif target != bot:
                    findings["legacy_profile"].append(dict(row, profile=target))
                    moves.append(dict(row, to=target, reason="legacy_profile"))
                    continue
            origin = job.get("origin") if isinstance(job.get("origin"), dict) else {}
            person = str(job.get("owner_email") or "").strip()
            if str(origin.get("platform") or "").lower() == "webui":
                sid = str(origin.get("chat_id") or "")
                session = _session(sessions, sid) if sid else None
                if sid and sessions is not None and session is None:
                    findings["origin_chat_missing"].append(dict(row, chat_id=sid))
                if session is not None:
                    chat_bot = _norm_profile(session.get("profile"), bot_set)
                    in_chat = {_norm_profile(b, bot_set) for b in (session.get("bot_participants") or [])}
                    if chat_bot != bot and bot not in in_chat:
                        findings["origin_other_bot"].append(dict(row, chat_bot=chat_bot, chat_id=sid))
                        if move_origin_mismatch and chat_bot in bot_set:
                            moves.append(dict(row, to=chat_bot, reason="origin_other_bot"))
                    person = person or str(session.get("owner_email") or "").strip()
                person = person or str(origin.get("user_id") or "").strip()
            if not person:
                findings["no_person"].append(row)
    return {
        "hermes": str(hermes),
        "bots": bots,
        "jobs_per_bot": {b: counts[b] for b in bots if counts[b]},
        "enabled_per_bot": {b: enabled[b] for b in bots if enabled[b]},
        "total": sum(counts.values()),
        "findings": {k: v for k, v in findings.items()},
        "moves": moves,
        "clears": clears,
    }


@contextlib.contextmanager
def _store_lock(home: Path):
    cron = home / "cron"
    cron.mkdir(parents=True, exist_ok=True)
    with open(cron / ".jobs.lock", "a+", encoding="utf-8") as fd:
        deadline = time.monotonic() + 30
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() > deadline:
                    raise SystemExit(f"timed out waiting for {cron / '.jobs.lock'}; stop the gateway first") from exc
                time.sleep(0.2)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)


def _write_jobs(path: Path, data, jobs: list) -> None:
    payload = dict(data) if isinstance(data, dict) else {}
    payload["jobs"] = jobs
    fd, tmp = tempfile.mkstemp(prefix=".jobs_", suffix=".tmp", dir=str(path.parent))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def apply(hermes: Path, sessions: Path | None, backup: Path, move_origin_mismatch: bool = False) -> dict:
    report = plan(hermes, sessions, move_origin_mismatch)
    homes = dict(stores(hermes))
    touched = sorted({m["bot"] for m in report["moves"]} | {m["to"] for m in report["moves"]}
                     | {c["bot"] for c in report["clears"]})
    backup.mkdir(parents=True, exist_ok=True)
    manifest = {"created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "hermes": str(hermes),
                "stores": {}, "moves": [], "clears": []}
    for bot in touched:
        src = homes[bot] / "cron" / "jobs.json"
        dst = backup / bot / "jobs.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, dst)
        manifest["stores"][bot] = {"path": str(src), "backup": str(dst), "existed": src.exists()}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    for clear in report["clears"]:
        path = homes[clear["bot"]] / "cron" / "jobs.json"
        with _store_lock(homes[clear["bot"]]):
            data = _read_json(path, {})
            jobs = _jobs_of(data)
            for job in jobs:
                if str(job.get("id")) == clear["job_id"]:
                    job["profile"] = None
            _write_jobs(path, data, jobs)
        manifest["clears"].append(clear)
    for move in report["moves"]:
        src_home, dst_home = homes[move["bot"]], homes[move["to"]]
        src_path, dst_path = src_home / "cron" / "jobs.json", dst_home / "cron" / "jobs.json"
        with _store_lock(dst_home):
            if any(str(j.get("id")) == move["job_id"] for j in _jobs_of(_read_json(dst_path, {}))):
                manifest["moves"].append(dict(move, skipped="id already in target"))
                continue
        with _store_lock(src_home):
            data = _read_json(src_path, {})
            jobs = _jobs_of(data)
            job = next((j for j in jobs if str(j.get("id")) == move["job_id"]), None)
            if job is None or job.get("run_claim") or job.get("fire_claim"):
                manifest["moves"].append(dict(move, skipped="missing or running"))
                continue
            _write_jobs(src_path, data, [j for j in jobs if j is not job])
        moved = dict(job, profile=None)
        with _store_lock(dst_home):
            data = _read_json(dst_path, {"jobs": []})
            _write_jobs(dst_path, data, _jobs_of(data) + [moved])
        out_src = src_home / "cron" / "output" / move["job_id"]
        out_dst = dst_home / "cron" / "output" / move["job_id"]
        if out_src.is_dir() and not out_dst.exists():
            shutil.copytree(out_src, backup / move["bot"] / "output" / move["job_id"], dirs_exist_ok=True)
            out_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(out_src), str(out_dst))
            move = dict(move, output_moved=str(out_dst))
        manifest["moves"].append(move)
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def restore(backup: Path) -> dict:
    manifest = _read_json(backup / "manifest.json", None)
    if not manifest:
        raise SystemExit(f"no manifest.json in {backup}")
    restored = []
    for bot, info in manifest.get("stores", {}).items():
        target = Path(info["path"])
        home = target.parent.parent
        with _store_lock(home):
            if info.get("existed"):
                shutil.copy2(info["backup"], target)
            elif target.exists():
                target.unlink()
        restored.append(bot)
    for move in manifest.get("moves", []):
        moved_to = move.get("output_moved")
        saved = backup / move["bot"] / "output" / move["job_id"]
        if moved_to and saved.is_dir():
            original = Path(manifest["stores"][move["bot"]]["path"]).parent / "output" / move["job_id"]
            if not original.exists():
                shutil.copytree(saved, original)
            shutil.rmtree(moved_to, ignore_errors=True)
    return {"restored_stores": restored}


def _print_plan(report: dict) -> None:
    print(f"Hermes home: {report['hermes']}")
    print(f"Jobs: {report['total']} in {len(report['jobs_per_bot'])} bot store(s)")
    for bot, count in sorted(report["jobs_per_bot"].items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {bot}: {count} ({report['enabled_per_bot'].get(bot, 0)} enabled)")
    for key in ("legacy_profile", "missing_profile", "origin_other_bot", "origin_chat_missing",
                "no_person", "duplicate_id"):
        rows = report["findings"].get(key, [])
        print(f"{key}: {len(rows)}")
        for row in rows[:50]:
            print("  " + json.dumps(row, ensure_ascii=False))
    print(f"apply would move {len(report['moves'])} job(s) and clear {len(report['clears'])} override(s)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("plan", "apply", "restore"))
    ap.add_argument("--hermes", type=Path, default=Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")))
    ap.add_argument("--sessions", type=Path, default=None,
                    help="WebUI sessions dir (default <hermes>/webui/sessions when it exists)")
    ap.add_argument("--backup-dir", type=Path, default=None)
    ap.add_argument("--move-origin-mismatch", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    hermes = args.hermes.expanduser()
    sessions = args.sessions or (hermes / "webui" / "sessions")
    sessions = sessions if sessions.is_dir() else None
    if args.command == "plan":
        report = plan(hermes, sessions, args.move_origin_mismatch)
        print(json.dumps(report, indent=1, ensure_ascii=False)) if args.json else _print_plan(report)
        return 0
    if args.backup_dir is None:
        ap.error(f"{args.command} needs --backup-dir")
    if args.command == "apply":
        manifest = apply(hermes, sessions, args.backup_dir.expanduser(), args.move_origin_mismatch)
        print(json.dumps({"moves": manifest["moves"], "clears": manifest["clears"],
                          "backup": str(args.backup_dir)}, indent=1, ensure_ascii=False))
        return 0
    print(json.dumps(restore(args.backup_dir.expanduser()), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
