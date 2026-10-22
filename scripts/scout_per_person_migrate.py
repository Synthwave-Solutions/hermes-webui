#!/usr/bin/env python3
"""Move bot wide Scout settings to Scout per person per bot.

For every bot profile whose ``ui_meta.hermes-bots.scout`` has no ``people``
yet, this script

1. writes the settings in the new form: the old switch becomes the switch of
   the owner of the bot's Scout job (else bot_metadata.SCOUT_LEGACY_OWNER),
   with a derived top level ``enabled`` (api/bot_metadata.py);
2. tags that Scout job with ``scout_person`` and ``scout_adopted`` so it is
   the job of that person (api/bot_scout.py), and its collector starts from
   the bot wide ledger.

Idempotent: a bot that already has ``people`` and a tagged job is reported as
done. Without ``--apply`` nothing is written; it only prints what it would do.
With ``--apply --sync`` it also brings each person's job in line right away
(name, prompt, schedule, toolsets and the runner copy); otherwise that happens
on the next Scout save in the WebUI.

Run from the WebUI checkout:
  PYTHONPATH=<hermes-agent>:. python scripts/scout_per_person_migrate.py [--apply [--sync]] [bot ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _raw_scout(home: Path):
    from api.yaml_utils import safe_load

    path = home / "profile.yaml"
    if not path.is_file():
        return None
    data = safe_load(path.read_text(encoding="utf-8")) or {}
    meta = ((data.get("ui_meta") or {}).get("hermes-bots") or {}) if isinstance(data, dict) else {}
    scout = meta.get("scout") if isinstance(meta, dict) else None
    return scout if isinstance(scout, dict) else None


def _scout_jobs(home: Path) -> list:
    path = home / "cron" / "jobs.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    return [j for j in jobs if isinstance(j, dict) and j.get("managed_by") == "scout"]


def bot_names(root: Path) -> list:
    names = []
    for path in sorted((root / "profiles").glob("*/profile.yaml")):
        if _raw_scout(path.parent) is not None:
            names.append(path.parent.name)
    if _raw_scout(root) is not None:
        names.insert(0, "default")
    return names


def migrate(name: str, apply: bool, sync: bool) -> list:
    from api import bot_metadata, bot_scout
    from api.cron_bots import home_for_profile
    from api.profiles import cron_profile_context_for_home

    home = Path(home_for_profile(name))
    lines = []
    raw = _raw_scout(home)
    row = bot_metadata.read_profile(name)
    if raw is None:
        return [f"{name}: geen Scout-instellingen, overgeslagen"]
    if row.get("bot_kind") != "bot":
        return [f"{name}: geen bot (soort {row.get('bot_kind')}), overgeslagen"]
    scout = (row.get("bot") or {}).get("scout")
    if not scout:
        return [f"{name}: Scout-instellingen onleesbaar, overgeslagen"]
    people = scout.get("people") or {}
    if "people" in raw:
        lines.append(f"{name}: instellingen staan al per persoon ({len(people)} personen)")
    else:
        lines.append(f"{name}: instellingen omzetten naar per persoon: "
                     + (", ".join(f"{p} {'aan' if v.get('enabled') else 'uit'}" for p, v in people.items()) or "niemand aan"))
        if apply:
            bot_metadata.save_scout(name, scout, row["bot_revision"])
            lines.append(f"{name}: instellingen opgeslagen")
    jobs = _scout_jobs(home)
    if not jobs:
        lines.append(f"{name}: geen Scout-job")
    for job in jobs:
        person = bot_scout.job_person(job) or bot_metadata.SCOUT_LEGACY_OWNER
        if job.get(bot_scout.PERSON_FIELD):
            lines.append(f"{name}: job {job.get('id')} hoort al bij {job[bot_scout.PERSON_FIELD]}")
            continue
        lines.append(f"{name}: job {job.get('id')} ({job.get('name')}) koppelen aan {person}")
        if apply:
            with cron_profile_context_for_home(home):
                import cron.jobs as cj

                bot_scout._mark_scout(cj, str(job["id"]), person, adopted=True)
            lines.append(f"{name}: job {job.get('id')} gekoppeld")
    if apply and sync:
        current = (bot_metadata.read_profile(name).get("bot") or {}).get("scout") or {}
        if current.get("enabled"):
            bot_scout.install_runner(home)
        for person, job in bot_scout.sync_all(home, current).items():
            if job:
                from api.cron_bots import find_job_chat, ensure_job_chat
                if find_job_chat(job["id"], name, person):
                    ensure_job_chat(job, name, person)
            state = "aan" if job and bot_scout._is_on(job) else "uit"
            lines.append(f"{name}: job van {person} bijgewerkt ({state})")
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--apply", action="store_true", help="write the changes (default: only show them)")
    parser.add_argument("--sync", action="store_true", help="with --apply: also update each person's job now")
    parser.add_argument("bots", nargs="*", help="bot profile names (default: every bot with Scout settings)")
    args = parser.parse_args(argv)
    if args.sync and not args.apply:
        parser.error("--sync needs --apply")
    from api.profiles import _DEFAULT_HERMES_HOME

    names = args.bots or bot_names(Path(_DEFAULT_HERMES_HOME))
    print(("TOEPASSEN" if args.apply else "PROEFRUN, er wordt niets geschreven") + f": {len(names)} bots")
    failed = 0
    for name in names:
        try:
            for line in migrate(name, args.apply, args.sync):
                print("  " + line)
        except Exception as exc:  # one broken bot never stops the others
            failed += 1
            print(f"  {name}: MISLUKT ({type(exc).__name__}: {exc})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
