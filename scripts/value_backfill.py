#!/usr/bin/env python3
"""AI estimates of the value of every existing scheduled task and bot duty.

Every task and bot responsibility should say what the work cost by hand
before and what a person still spends on it now (api/value_tracking.py).
Existing work has no such numbers. This script asks a model for an estimate
with a short rationale, labelled ``ai_estimate`` so the owner confirms or
adjusts it later (Management shows "Schattingen niet bevestigd").

    python scripts/with_agent_runtime.py scripts/value_backfill.py --plan [--limit N] [--out plan.json]
    python scripts/with_agent_runtime.py scripts/value_backfill.py --apply plan.json

--plan reads only: it writes nothing but the plan file. --apply writes the
values from a reviewed plan, only where a task or duty still has none, so a
value set by a person in the meantime is never overwritten.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OMNIROUTE = os.environ.get("OMNIROUTE_URL", "http://127.0.0.1:20128/v1/chat/completions")
MODELS = [os.environ.get("VALUE_BACKFILL_MODEL", "synthwave-auto"), "auto"]

SYSTEM = """Je schat de waarde van een automatisering voor een Nederlands bedrijf.
Gegeven een geplande taak (naam, ritme, prompt of script), schat:
- task: in maximaal 10 woorden welk handwerk dit vervangt;
- per: "run" (per keer dat de taak draait), "day" of "week". Draait de taak vaker dan
  dagelijks (elke paar minuten of elk uur), kies dan "day": schat wat de taak PER DAG aan
  handwerk vervangt, niet per run. Een wekelijkse taak is "run";
- before_minutes: minuten handwerk per eenheid (per keer, per dag of per week);
- review_minutes: minuten die een mens per eenheid nog kwijt is aan nakijken of opvolgen;
- rationale: in maximaal 25 woorden waarom.
Wees nuchter en eerder te laag dan te hoog. Vervangt de taak geen handwerk (technische bewaking,
opschonen, een test), zet before_minutes op 0 en leg in rationale uit waarom.
Antwoord alleen met JSON: {"task": "...", "per": "run", "before_minutes": 0, "review_minutes": 0, "rationale": "..."}"""

DUTY_SYSTEM = """Je schat de waarde van een verantwoordelijkheid van een AI-bot voor een Nederlands bedrijf.
Gegeven de bot en de verantwoordelijkheid, schat:
- minutes_before: minuten handwerk per keer zonder de bot;
- minutes_now: minuten die een mens per keer nog kwijt is met de bot;
- times_per_week: hoe vaak dit per week voorkomt;
- rationale: maximaal 25 woorden.
Wees nuchter. Antwoord alleen met JSON: {"minutes_before": 0, "minutes_now": 0, "times_per_week": 0, "rationale": "..."}"""


def _key() -> str:
    key = os.environ.get("OMNIROUTE_API_KEY", "")
    if key:
        return key
    env = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / ".env"
    try:
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("OMNIROUTE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _content(raw: str) -> str:
    """The assistant text from a JSON completion or from an SSE stream."""
    raw = raw.strip()
    if raw.startswith("{"):
        out = json.loads(raw)
        return out["choices"][0]["message"]["content"] or ""
    parts = []
    for line in raw.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            chunk = json.loads(payload)
        except ValueError:
            continue
        for choice in chunk.get("choices") or []:
            parts.append((choice.get("delta") or {}).get("content") or (choice.get("message") or {}).get("content") or "")
    return "".join(parts)


def ask(system: str, context: str) -> dict | None:
    key = _key()
    for model in MODELS:
        for attempt in range(2):
            body = json.dumps({"model": model, "temperature": 0.1, "max_tokens": 800, "stream": False,
                               "messages": [{"role": "system", "content": system},
                                            {"role": "user", "content": context}]}).encode()
            headers = {"Content-Type": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"
            try:
                req = urllib.request.Request(OMNIROUTE, data=body, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw = resp.read().decode()
                text = _content(raw)
                start = text.find("{")
                if start >= 0:
                    obj, _end = json.JSONDecoder().raw_decode(text[start:])
                    if isinstance(obj, dict):
                        return obj
            except Exception as exc:  # noqa: BLE001
                print(f"  [{model}] attempt {attempt + 1}: {str(exc)[:120]}", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
    return None


def job_context(profile: str, job: dict) -> str:
    prompt = str(job.get("prompt") or "")
    prompt = re.sub(r"DIAGRAM \(documentation.*", "", prompt, flags=re.S)[:1800]
    parts = [f"Naam: {job.get('name')}", f"Bot/store: {profile}",
             f"Ritme: {job.get('schedule_display') or (job.get('schedule') or {}).get('display') or ''}"]
    if job.get("script"):
        parts.append(f"Script: {Path(str(job['script'])).name}")
    if job.get("no_agent"):
        parts.append("Draait zonder agent (alleen script).")
    parts.append("Prompt:\n" + prompt)
    return "\n".join(parts)


def plan(limit: int | None, out: Path) -> int:
    from api import value_tracking, bot_metadata
    from api.management import _bots

    tasks = []
    for profile, job in value_tracking.iter_store_jobs():
        if job.get("enabled") is False or job.get("state") == "paused":
            continue
        if isinstance(job.get("value"), dict) and value_tracking.job_value(job):
            continue
        tasks.append(("job", profile, job))
    for name, bot in _bots().items():
        if bot["kind"] != "bot":
            continue
        for index, duty in enumerate(bot["duties"]):
            if duty.get("minutes_before"):
                continue
            tasks.append(("duty", name, {"bot": bot, "index": index, "duty": duty}))
    if limit:
        tasks = tasks[:limit]
    print(f"{len(tasks)} items to estimate", flush=True)

    def work(item):
        kind, profile, obj = item
        if kind == "job":
            answer = ask(SYSTEM, job_context(profile, obj))
            return {"kind": "job", "store": profile, "job_id": obj.get("id"), "name": obj.get("name"), "estimate": answer}
        bot, duty = obj["bot"], obj["duty"]
        context = (f"Bot: {bot['title']} ({bot.get('role') or ''})\nVerantwoordelijkheid: {duty.get('title')}\n"
                   f"Doel: {duty.get('objective') or ''}\nWanneer: {duty.get('trigger') or ''}")
        answer = ask(DUTY_SYSTEM, context)
        return {"kind": "duty", "bot": profile, "index": obj["index"], "title": duty.get("title"), "estimate": answer}

    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get("VALUE_BACKFILL_WORKERS", "6"))) as pool:
        for row in pool.map(work, tasks):
            rows.append(row)
            est = row.get("estimate") or {}
            label = row.get("name") or f"{row.get('bot')}: {row.get('title')}"
            if row["kind"] == "job":
                print(f"- {label[:60]:60} {est.get('before_minutes', '?'):>4} -> {est.get('review_minutes', '?'):>3} min/{est.get('per', 'run'):4} {str(est.get('task') or '')[:44]}", flush=True)
            else:
                print(f"- {label[:60]:60} {est.get('minutes_before', '?'):>4} -> {est.get('minutes_now', '?'):>3} min x {est.get('times_per_week', '?')}/wk", flush=True)
    out.write_text(json.dumps({"created_at": time.time(), "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"plan written: {out}")
    return 0


def apply(path: Path, actor: str) -> int:
    from api import value_tracking, bot_metadata, cron_bots

    data = json.loads(path.read_text(encoding="utf-8"))
    done = skipped = 0
    for row in data.get("rows", []):
        est = row.get("estimate") or {}
        if not est:
            skipped += 1
            continue
        if row["kind"] == "job":
            job, _owner = cron_bots.find_job(row["job_id"], row["store"])
            if job is None or value_tracking.job_value(job):
                skipped += 1
                continue
            before = int(est.get("before_minutes") or 0)
            if before <= 0:
                value = {"unknown": True, "unknown_reason": str(est.get("rationale") or "Vervangt geen handwerk")[:200],
                         "task": str(est.get("task") or "")[:120], "source": "ai_estimate", "confidence": "estimated"}
            else:
                per = est.get("per") if est.get("per") in ("run", "day", "week") else "run"
                value = {"before_minutes": before, "review_minutes": min(before, int(est.get("review_minutes") or 0)), "per": per,
                         "task": str(est.get("task") or "")[:120], "rationale": str(est.get("rationale") or "")[:400],
                         "source": "ai_estimate", "confidence": "estimated"}
            previous = job.get("value") if isinstance(job.get("value"), dict) else {}
            if previous.get("team"):
                value["team"] = previous["team"]
            value_tracking.set_job_value(row["job_id"], row["store"], value, actor)
            done += 1
        else:
            meta = bot_metadata.read_profile(row["bot"])
            duties = list((meta.get("bot") or {}).get("responsibilities") or [])
            index = row["index"]
            if index >= len(duties) or duties[index].get("title") != row.get("title") or duties[index].get("minutes_before"):
                skipped += 1
                continue
            before = int(est.get("minutes_before") or 0)
            if before <= 0:
                skipped += 1
                continue
            duties[index] = dict(duties[index], minutes_before=before,
                                 minutes_now=min(before, int(est.get("minutes_now") or 0)),
                                 times_per_week=float(est.get("times_per_week") or 0),
                                 value_source="ai_estimate", value_confidence="estimated")
            bot_metadata.save_profile(row["bot"], {"responsibilities": duties}, meta.get("bot_revision") or 0)
            done += 1
    print(f"applied {done}, skipped {skipped}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", action="store_true")
    group.add_argument("--apply", metavar="PLAN")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default="")
    ap.add_argument("--actor", default="value-backfill")
    args = ap.parse_args()
    if args.plan:
        from api.config import STATE_DIR

        out = Path(args.out) if args.out else Path(STATE_DIR) / "value" / f"backfill-plan-{time.strftime('%Y%m%d-%H%M%S')}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        return plan(args.limit, out)
    return apply(Path(args.apply), args.actor)


if __name__ == "__main__":
    sys.exit(main())
