"""Management and organisation chart read models (8 Nov 2026).

``/api/management/overview``  headline numbers, per team, per bot, decisions
``/api/management/job``       one job: its value and every run in the period
``/api/management/pricing``   GET/POST the price table (organisation admins)
``/api/org/chart``            departments, teams, people, bots and jobs

``/api/value/job``            POST set, confirm or clear a job's value or team
``/api/value/chat``           POST label one of your own bot chats

Every view is filtered by ``org_structure.request_scope``: organisation
admins see everything, department admins their departments, team members
only the organisation chart of their own team (``/api/org/chart``) and no
Management numbers. Numbers about a single person never leave this module
except to that person.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from urllib.parse import parse_qs

from api import org_structure, value_tracking
from api.helpers import j

logger = logging.getLogger(__name__)

UNASSIGNED = "_unassigned"
PERIODS = {"7": 7, "28": 28, "90": 90, "365": 365}
FAILING_STREAK = 3


def _period(qs) -> tuple[int, float, float]:
    days = PERIODS.get((qs.get("period") or ["28"])[0], 28)
    end = time.time()
    return days, end - days * 86400, end


import os as _os

# Personal and private profiles are people's own assistants, not bots that
# work for a team; they stay out of the organisation chart and Management.
PRIVATE_BOT_CATEGORIES = {c.strip().lower() for c in _os.environ.get(
    "SP_ORG_EXCLUDE_BOT_CATEGORIES",
    "Persoonlijke assistenten,Partner-assistenten,Gedeelde inbox,Privé,Prive,Private,Personal").split(",") if c.strip()}


def _bots() -> dict:
    """``{name: {title, kind, serves, duties, avatar}}`` for every profile."""
    from api import bot_metadata

    try:
        import api.profiles as profiles

        try:
            rows = profiles.list_profiles_api(fast=True, include_skill_counts=False)
        except TypeError:
            rows = profiles.list_profiles_api()
    except Exception:
        logger.warning("profile listing failed for management", exc_info=True)
        rows = []
    out = {}
    for row in rows or []:
        name = str((row or {}).get("name") or "")
        if not name:
            continue
        try:
            meta = bot_metadata.read_profile(name)
        except Exception:
            meta = {}
        bot = meta.get("bot") or {}
        out[name] = {
            "name": name,
            "title": bot.get("title") or name,
            "kind": meta.get("bot_kind") or "unknown",
            "role": bot.get("role") or "",
            "reports_to": bot.get("reports_to") or "",
            "serves": [s for s in bot.get("serves") or [] if isinstance(s, str)],
            "duties": bot.get("responsibilities") or [],
            "avatar_url": meta.get("bot_avatar_url") or "",
            "color": bot.get("color") or "",
            "category": bot.get("category") or "",
        }
    return out


_CATEGORY_ALIASES = {
    "sales": ("sales", "commercieel", "commercial", "verkoop"),
    "commercieel": ("sales", "commercieel", "commercial", "verkoop"),
    "engineering": ("engineering", "tech", "techniek", "platform", "development"),
    "platform": ("platform", "tech", "engineering"),
    "delivery": ("delivery", "projecten", "operations"),
    "finance": ("finance", "financien", "financiën"),
    "marketing": ("marketing",),
    "management": ("management", "directie", "mt"),
}


def suggest_team(category: str, structure: dict) -> str:
    """A team for an unassigned task or bot from its existing category: a
    team with that name, else the only team of a department with that name."""
    cat = " ".join(str(category or "").lower().split())
    if not cat:
        return ""
    names = _CATEGORY_ALIASES.get(cat, (cat,))
    teams = {k: v for k, v in (structure.get("teams") or {}).items() if isinstance(v, dict)}
    for key, team in sorted(teams.items()):
        if str(team.get("name") or "").lower() in names:
            return key
    depts = org_structure.departments(structure)
    for dkey, dept in depts.items():
        if dkey in names or str(dept.get("name") or "").lower() in names:
            in_dept = sorted(k for k, v in teams.items() if v.get("department") == dkey)
            if len(in_dept) == 1:
                return in_dept[0]
    return ""


def _job_team(job: dict, structure: dict, bot_teams: dict | None = None, store: str | None = None) -> str:
    """A task's team: its own ``value.team``, else the team its responsible
    bot works for, else the team of its owner."""
    value = job.get("value") if isinstance(job.get("value"), dict) else {}
    if value.get("team"):
        return value["team"]
    if bot_teams:
        from api import cron_bots

        team = bot_teams.get(cron_bots.job_bot(job, store if store is not None else job.get("owner_profile")))
        if team:
            return team
    owner = org_structure.norm_email(job.get("owner_email"))
    return org_structure.team_of(owner, structure) if owner else ""


def _bot_teams(bots: dict) -> dict:
    return {name: (b.get("serves") or [""])[0] for name, b in bots.items() if b.get("serves")}


def _job_state(job: dict) -> str:
    if job.get("enabled") is False or job.get("state") == "paused":
        return "paused"
    status = str(job.get("last_status") or "").lower()
    if status in ("error", "failed", "failure") or int(job.get("failure_streak") or 0) > 0:
        return "error"
    if status in ("ok", "success", "completed"):
        return "ok"
    return "new"


def _value_label(value: dict | None) -> str:
    if not value:
        return "missing"
    if value.get("unknown"):
        return "unknown"
    if value.get("confidence") == "confirmed":
        return "confirmed"
    return "ai_estimate" if value.get("source") == "ai_estimate" else "estimated"


def _collect_safely():
    try:
        value_tracking.collect()
    except Exception:
        logger.warning("value collect failed", exc_info=True)


def build(view: org_structure.ViewScope, days: int, start: float, end: float) -> dict:
    """The whole read model in one pass, filtered for ``view``."""
    from api import cron_bots

    structure = org_structure.load()
    policy = org_structure._policy()
    snap = org_structure.snapshot(view, structure, policy)
    pricing = value_tracking.load_pricing()
    bots = _bots()
    team_names = {k: t["name"] for k, t in (structure.get("teams") or {}).items() if isinstance(t, dict)}

    def visible_team(key: str) -> bool:
        if key in ("", UNASSIGNED):
            return view.scope == org_structure.SCOPE_ALL
        return key in snap["teams"]

    jobs = {}
    bot_teams = _bot_teams(bots)
    for profile, job in value_tracking.iter_store_jobs():
        jid = str(job.get("id") or "")
        if not jid:
            continue
        team = _job_team(job, structure, bot_teams, profile) or UNASSIGNED
        if not visible_team(team):
            continue
        value = value_tracking.job_value(job)
        jobs[(profile, jid)] = {
            "id": jid, "store": profile, "name": job.get("name") or jid,
            "bot": cron_bots.job_bot(job, profile), "team": team,
            "enabled": job.get("enabled") is not False and job.get("state") != "paused",
            "state": _job_state(job), "failure_streak": int(job.get("failure_streak") or 0),
            "schedule": job.get("schedule_display") or "",
            "owner_email": org_structure.norm_email(job.get("owner_email")),
            "value": value, "value_label": _value_label(value),
            "suggested_team": suggest_team(job.get("category"), structure) if team == UNASSIGNED else "",
            "runs": 0, "ok_runs": 0, "failed_runs": 0, "saved_minutes": 0, "review_minutes": 0,
            "ai_cost_eur": 0.0, "unpriced_tokens": 0, "net_eur": None, "_periods": set(),
        }

    def rate_for(team: str):
        return org_structure.team_rate(team, structure, policy) if team not in ("", UNASSIGNED) else None

    # Runs in the period, attributed to the job's current team.
    for run in value_tracking.runs_between(start, end):
        key = (run["store"], run["job_id"])
        row = jobs.get(key)
        if row is None:
            continue
        money = value_tracking.run_money(run, rate_for(row["team"]), pricing)
        row["runs"] += 1
        row["ok_runs" if run["status"] == "ok" else "failed_runs"] += 1
        per = (row["value"] or {}).get("per", "run")
        if per == "run":
            row["saved_minutes"] += money["saved_minutes"]
            row["review_minutes"] += money["review_minutes"]
        elif run["status"] == "ok" and money["has_value"] and run.get("finished_at"):
            # Count once per day or ISO week with a completed run.
            stamp = time.gmtime(run["finished_at"])
            row["_periods"].add(time.strftime("%Y-%j", stamp) if per == "day" else time.strftime("%G-%V", stamp))
            money = dict(money, saved_minutes=0, net_eur=(-(money["ai_cost_eur"] or 0) if money["net_eur"] is not None else None))
        if money["ai_cost_eur"] is None:
            row["unpriced_tokens"] += (run.get("tokens_in") or 0) + (run.get("tokens_out") or 0) + (run.get("tokens_cache") or 0)
        else:
            row["ai_cost_eur"] += money["ai_cost_eur"]
        if money["net_eur"] is not None:
            row["net_eur"] = round((row["net_eur"] or 0) + money["net_eur"], 2)

    # Per-day and per-week values: the saving once per period with a run.
    for row in jobs.values():
        periods = row.pop("_periods")
        value = row["value"] or {}
        if periods and value.get("per") in ("day", "week"):
            each = max(0, int(value.get("before_minutes") or 0) - int(value.get("review_minutes") or 0))
            row["saved_minutes"] += each * len(periods)
            row["review_minutes"] += int(value.get("review_minutes") or 0) * len(periods)
            rate = rate_for(row["team"])
            if rate is not None:
                row["net_eur"] = round((row["net_eur"] or 0) + each * len(periods) / 60 * rate, 2)
        row["confirmed"] = row["value_label"] == "confirmed"
        row["saved_per_day"] = row["saved_minutes"] / max(1, days)

    # Bot chats in the period. Team = the bot's first served team, else the
    # chatting person's team.
    bot_rows = {}
    for name, bot in bots.items():
        if bot["kind"] != "bot" or str(bot.get("category") or "").strip().lower() in PRIVATE_BOT_CATEGORIES:
            continue
        team = (bot["serves"] or [""])[0] or UNASSIGNED
        estimate = value_tracking.bot_estimate_per_week(name)
        bot_rows[name] = {"name": name, "title": bot["title"], "team": team, "serves": bot["serves"],
                          "category": " ".join(str(bot.get("category") or "").split())[:60],
                          "avatar_url": bot["avatar_url"], "color": bot["color"], "role": bot["role"],
                          "suggested_team": suggest_team(bot.get("category"), structure) if team == UNASSIGNED else "",
                          "duties": len(bot["duties"]), "duties_with_value": estimate["duties_with_value"],
                          "estimate_minutes_per_week": estimate["minutes_per_week"],
                          "estimate_confirmed": estimate["confirmed"],
                          "chats": 0, "people": set(), "labeled_minutes": 0, "auto_minutes": 0, "auto_chats": 0, "ai_cost_eur": 0.0,
                          "unpriced_tokens": 0, "jobs": 0, "job_saved_minutes": 0}
    for chat in value_tracking.chats_between(start, end):
        row = bot_rows.get(chat["bot"])
        if row is None:
            continue
        row["chats"] += 1
        if chat.get("user_hash"):
            row["people"].add(chat["user_hash"])
        if chat.get("label_state") == "confirmed":
            row["labeled_minutes"] += int(chat.get("saved_minutes") or 0)
        elif chat.get("label_state") == "auto" and chat.get("duty"):
            row["auto_minutes"] += int(chat.get("saved_minutes") or 0)
            row["auto_chats"] += 1
        cost, source = value_tracking.ai_cost_eur(chat.get("model"), chat.get("tokens_in") or 0,
                                                  chat.get("tokens_out") or 0, chat.get("tokens_cache") or 0,
                                                  chat.get("provider_cost_usd"), pricing)
        if cost is None:
            row["unpriced_tokens"] += (chat.get("tokens_in") or 0) + (chat.get("tokens_out") or 0) + (chat.get("tokens_cache") or 0)
        else:
            row["ai_cost_eur"] += cost
    for row in jobs.values():
        bot = bot_rows.get(row["bot"])
        if bot is not None:
            bot["jobs"] += 1
            bot["job_saved_minutes"] += row["saved_minutes"]
    bot_rows = {k: v for k, v in bot_rows.items() if visible_team(v["team"])}
    weeks = days / 7.0

    # Per team.
    teams = {}
    for key, team in snap["teams"].items():
        teams[key] = {"key": key, "name": team["name"], "department": team["department"], "lead": team["lead"],
                      "members": len(team["members"]), "hourly_rate": team.get("hourly_rate"),
                      "bots": 0, "jobs": 0, "active_jobs": 0, "runs": 0, "ok_runs": 0, "failed_runs": 0,
                      "saved_minutes": 0, "estimate_minutes": 0, "ai_cost_eur": 0.0, "unpriced_tokens": 0,
                      "net_eur": None, "failing": 0, "missing_value": 0, "saved_confirmed_minutes": 0}
    if view.scope == org_structure.SCOPE_ALL:
        teams[UNASSIGNED] = {"key": UNASSIGNED, "name": "", "department": "", "lead": "", "members": 0,
                             "hourly_rate": None, "bots": 0, "jobs": 0, "active_jobs": 0, "runs": 0, "ok_runs": 0,
                             "failed_runs": 0, "saved_minutes": 0, "estimate_minutes": 0, "ai_cost_eur": 0.0,
                             "unpriced_tokens": 0, "net_eur": None, "failing": 0, "missing_value": 0,
                             "saved_confirmed_minutes": 0}
    for row in jobs.values():
        team = teams.get(row["team"])
        if team is None:
            continue
        team["jobs"] += 1
        team["active_jobs"] += 1 if row["enabled"] else 0
        for k in ("runs", "ok_runs", "failed_runs", "saved_minutes", "unpriced_tokens"):
            team[k] += row[k]
        team["saved_confirmed_minutes"] += row["saved_minutes"] if row["confirmed"] else 0
        team["ai_cost_eur"] += row["ai_cost_eur"]
        if row["net_eur"] is not None:
            team["net_eur"] = round((team["net_eur"] or 0) + row["net_eur"], 2)
        if row["enabled"] and row["failure_streak"] >= FAILING_STREAK:
            team["failing"] += 1
        if row["enabled"] and row["value_label"] == "missing":
            team["missing_value"] += 1
    for row in bot_rows.values():
        team = teams.get(row["team"])
        if team is None:
            continue
        team["bots"] += 1
        team["saved_minutes"] += row["labeled_minutes"]
        team["saved_confirmed_minutes"] += row["labeled_minutes"]
        # Estimate: chats a model linked to a duty; without such labels the
        # duties' own "times per week" stand in.
        team["estimate_minutes"] += row["auto_minutes"] if row["auto_chats"] else int(row["estimate_minutes_per_week"] * weeks)
        team["ai_cost_eur"] += row["ai_cost_eur"]
        team["unpriced_tokens"] += row["unpriced_tokens"]
        rate = rate_for(row["team"])
        if rate is not None and row["labeled_minutes"]:
            team["net_eur"] = round((team["net_eur"] or 0) + row["labeled_minutes"] / 60 * rate - row["ai_cost_eur"], 2)
    for team in teams.values():
        team["ai_cost_eur"] = round(team["ai_cost_eur"], 2)

    active = [r for r in jobs.values() if r["enabled"]]
    confirmed = [r for r in active if r["value_label"] == "confirmed"]
    totals = {
        "saved_minutes": sum(t["saved_minutes"] for t in teams.values()),
        "saved_confirmed_minutes": sum(t["saved_confirmed_minutes"] for t in teams.values()),
        "estimate_minutes": sum(t["estimate_minutes"] for t in teams.values()),
        "ai_cost_eur": round(sum(t["ai_cost_eur"] for t in teams.values()), 2),
        "unpriced_tokens": sum(t["unpriced_tokens"] for t in teams.values()),
        "net_eur": None, "active_jobs": len(active), "bots": len(bot_rows),
        "runs": sum(r["runs"] for r in jobs.values()), "ok_runs": sum(r["ok_runs"] for r in jobs.values()),
        "coverage": round(len(confirmed) / len(active), 3) if active else None,
        "with_value": sum(1 for r in active if r["value_label"] not in ("missing",)),
        "rates_set": any(t.get("hourly_rate") is not None for t in teams.values()) or any(
            (d.get("hourly_rate") is not None) for d in snap["departments"].values()),
        "pricing_set": bool(pricing.get("models")),
    }
    nets = [t["net_eur"] for t in teams.values() if t["net_eur"] is not None]
    if nets:
        totals["net_eur"] = round(sum(nets), 2)
    if totals["net_eur"] is not None and totals["ai_cost_eur"]:
        totals["return_ratio"] = round((totals["net_eur"] + totals["ai_cost_eur"]) / totals["ai_cost_eur"], 1)

    def job_ref(r):
        return {"id": r["id"], "store": r["store"], "name": r["name"], "team": r["team"], "bot": r["bot"],
                "saved_minutes": r["saved_minutes"], "net_eur": r["net_eur"], "ai_cost_eur": round(r["ai_cost_eur"], 2),
                "runs": r["runs"], "failed_runs": r["failed_runs"], "value_label": r["value_label"],
                "failure_streak": r["failure_streak"], "state": r["state"], "suggested_team": r.get("suggested_team", ""),
                "per": (r["value"] or {}).get("per", "run"), "confirmed": r.get("confirmed", False),
                "before_minutes": (r["value"] or {}).get("before_minutes"), "review_minutes": (r["value"] or {}).get("review_minutes")}

    decisions = []
    failing = [r for r in active if r["failure_streak"] >= FAILING_STREAK]
    if failing:
        decisions.append({"kind": "failing", "count": len(failing),
                          "items": [job_ref(r) for r in sorted(failing, key=lambda r: -r["failure_streak"])[:20]]})
    missing = [r for r in active if r["value_label"] == "missing"]
    if missing:
        decisions.append({"kind": "missing_value", "count": len(missing), "items": [job_ref(r) for r in missing[:50]]})
    unconfirmed = [r for r in active if r["value_label"] in ("ai_estimate", "estimated")]
    if unconfirmed:
        decisions.append({"kind": "unconfirmed", "count": len(unconfirmed), "items": [job_ref(r) for r in unconfirmed[:50]]})
    high = [r for r in active if r["saved_per_day"] > 240 and not r["confirmed"]]
    if high:
        decisions.append({"kind": "check_high", "count": len(high),
                          "items": [job_ref(r) for r in sorted(high, key=lambda r: -r["saved_minutes"])[:20]]})
    negative = [r for r in active if r["net_eur"] is not None and r["net_eur"] < 0 and r["runs"]]
    if negative:
        decisions.append({"kind": "negative", "count": len(negative),
                          "items": [job_ref(r) for r in sorted(negative, key=lambda r: r["net_eur"])[:10]]})
    idle = [t for k, t in teams.items() if k != UNASSIGNED and not t["jobs"] and not t["bots"]]
    if idle:
        decisions.append({"kind": "idle_teams", "count": len(idle),
                          "items": [{"key": t["key"], "name": t["name"]} for t in idle]})
    unassigned = teams.get(UNASSIGNED)
    if unassigned and (unassigned["jobs"] or unassigned["bots"]):
        items = [job_ref(r) for r in jobs.values() if r["team"] == UNASSIGNED and r["enabled"]]
        bot_items = [{"bot": b["name"], "name": b["title"], "suggested_team": b["suggested_team"]}
                     for b in bot_rows.values() if b["team"] == UNASSIGNED]
        decisions.append({"kind": "unassigned", "count": unassigned["jobs"] + unassigned["bots"],
                          "suggestions": sum(1 for x in items + bot_items if x.get("suggested_team")),
                          "items": (bot_items + items)[:200]})
    try:
        from api import approvals

        pending = [r for r in (approvals.list_requests(status="pending") or [])]
        old = [r for r in pending if time.time() - float(r.get("created_at_ts") or r.get("created_at_epoch") or time.time()) > 3 * 86400]
        if old:
            decisions.append({"kind": "old_approvals", "count": len(old), "items": []})
    except Exception:
        pass

    ranked = sorted((r for r in jobs.values() if r["saved_minutes"]), key=lambda r: -r["saved_minutes"])
    bots_out = []
    for row in sorted(bot_rows.values(), key=lambda r: -(r["labeled_minutes"] + r["job_saved_minutes"])):
        out = dict(row)
        out["people"] = len(row["people"])
        out["ai_cost_eur"] = round(row["ai_cost_eur"], 2)
        bots_out.append(out)
    return {
        "period_days": days, "start": start, "end": end,
        "last_collect_at": value_tracking.last_collect_at(),
        "ledger_since": value_tracking.ledger_since(),
        "viewer": view.to_dict(), "totals": totals,
        "teams": sorted(teams.values(), key=lambda t: (t["key"] == UNASSIGNED, t["department"], t["name"])),
        "departments": snap["departments"], "team_names": team_names,
        "bots": bots_out,
        "jobs": [job_ref(r) for r in sorted(jobs.values(), key=lambda r: (-r["saved_minutes"], r["name"]))],
        "top": [job_ref(r) for r in ranked[:5]],
        "decisions": decisions,
        "pricing": {"set": bool(pricing.get("models")), "updated_at": pricing.get("updated_at")},
    }


def chart(view: org_structure.ViewScope) -> dict:
    """Organisation chart: departments > teams > people, with bots and jobs."""
    structure = org_structure.load()
    policy = org_structure._policy()
    snap = org_structure.snapshot(view, structure, policy)
    days, start, end = 28, time.time() - 28 * 86400, time.time()
    if view.scope in (org_structure.SCOPE_ALL, org_structure.SCOPE_DEPARTMENTS):
        model = build(view, days, start, end)
        team_stats = {t["key"]: t for t in model["teams"]}
        bots = model["bots"]
        jobs = model["jobs"]
    else:
        # Team members: only their team, counts without money.
        model = build(org_structure.ViewScope(email=view.email, scope=org_structure.SCOPE_TEAMS,
                                              lead_teams=view.lead_teams, member_teams=view.member_teams), days, start, end)
        team_stats = {t["key"]: {k: v for k, v in t.items() if k not in ("net_eur", "hourly_rate", "ai_cost_eur")}
                      for t in model["teams"]}
        bots = model["bots"]
        jobs = model["jobs"]
    people_titles = snap["people"]
    nodes = []
    for dkey, dept in sorted(snap["departments"].items(), key=lambda kv: kv[1]["name"].lower()):
        dept_teams = []
        for tkey, team in sorted(snap["teams"].items(), key=lambda kv: kv[1]["name"].lower()):
            if team["department"] != dkey:
                continue
            dept_teams.append({
                **team, "stats": team_stats.get(tkey, {}),
                "people": [people_titles.get(m, {"email": m}) for m in team["members"]],
                "bot_list": [b for b in bots if b["team"] == tkey or tkey in (b.get("serves") or [])],
                "job_list": [jb for jb in jobs if jb["team"] == tkey],
            })
        nodes.append({**dept, "teams": dept_teams})
    unassigned = None
    if view.scope == org_structure.SCOPE_ALL:
        unassigned = {"bot_list": [b for b in bots if b["team"] == UNASSIGNED],
                      "job_list": [jb for jb in jobs if jb["team"] == UNASSIGNED],
                      "stats": team_stats.get(UNASSIGNED, {})}
    return {"departments": nodes, "unassigned": unassigned, "viewer": view.to_dict(),
            "people": people_titles, "updated_at": snap.get("updated_at")}


def job_detail(view, store: str, job_id: str, days: int, start: float, end: float, handler=None) -> dict:
    """One job's value and runs. For its owner, people who may see the job,
    and organisation or department admins of its team."""
    from api import cron_bots

    job, owner = cron_bots.find_job(job_id, store)
    if job is None:
        raise KeyError("Job not found")
    structure = org_structure.load()
    team = _job_team(job, structure, _bot_teams(_bots()), owner) or UNASSIGNED
    allowed = view.scope == org_structure.SCOPE_ALL or (
        team != UNASSIGNED and view.scope == org_structure.SCOPE_DEPARTMENTS and view.edits_team(team))
    if not allowed and handler is not None:
        from api import cron_scope
        from api.governance.enforce import _request_identity

        identity = _request_identity(handler)
        allowed = cron_scope.identity_sees_cron_row(identity, job, store_profile=owner)
    if not allowed:
        raise KeyError("Job not found")
    pricing = value_tracking.load_pricing()
    rate = org_structure.team_rate(team, structure) if team != UNASSIGNED else None
    runs = []
    for run in value_tracking.runs_between(start, end):
        if run["store"] != owner or run["job_id"] != job_id:
            continue
        money = value_tracking.run_money(run, rate, pricing)
        runs.append({"finished_at": run["finished_at"], "status": run["status"], "duration_s": run["duration_s"],
                     "model": run["model"], "tokens": (run["tokens_in"] or 0) + (run["tokens_out"] or 0) + (run["tokens_cache"] or 0),
                     **money})
    runs.sort(key=lambda r: -(r["finished_at"] or 0))
    return {"job": {"id": job_id, "store": owner, "name": job.get("name"), "team": team},
            "value": value_tracking.job_value(job), "raw_value": job.get("value") if isinstance(job.get("value"), dict) else None,
            "rate": rate if view.sees_money else None,
            # Names only, so the owner can place the task in a team.
            "teams": sorted(({"key": k, "name": (t or {}).get("name") or k,
                              "department": (t or {}).get("department") or k.split("/", 1)[0]}
                             for k, t in (structure.get("teams") or {}).items() if isinstance(t, dict)),
                            key=lambda r: (r["department"], r["name"].lower())),
            "runs": runs, "period_days": days}


# ── HTTP ─────────────────────────────────────────────────────────────────────

_GET = ("/api/management/overview", "/api/management/job", "/api/management/pricing", "/api/org/chart", "/api/value/chat")
_POST = ("/api/management/pricing", "/api/value/job", "/api/value/chat", "/api/value/collect")


def handle_get(handler, parsed) -> bool:
    path = str(getattr(parsed, "path", "") or "")
    if path not in _GET:
        return False
    qs = parse_qs(parsed.query or "")
    view = org_structure.request_scope(handler)
    try:
        if path == "/api/org/chart":
            if view.is_none:
                j(handler, {"error": "forbidden", "reason": "org_scope", "viewer": view.to_dict()}, status=403)
                return True
            _collect_safely()
            j(handler, chart(view))
            return True
        if path == "/api/value/chat":
            sid = (qs.get("session_id") or [""])[0]
            j(handler, value_tracking.chat_label_for(sid, view.email))
            return True
        if path == "/api/management/job":
            _collect_safely()
            days, start, end = _period(qs)
            store = (qs.get("store") or ["default"])[0]
            job_id = (qs.get("job_id") or [""])[0]
            j(handler, job_detail(view, store, job_id, days, start, end, handler=handler))
            return True
        if view.scope not in (org_structure.SCOPE_ALL, org_structure.SCOPE_DEPARTMENTS):
            j(handler, {"error": "forbidden", "reason": "management_scope", "viewer": view.to_dict()}, status=403)
            return True
        if path == "/api/management/pricing":
            j(handler, {**value_tracking.load_pricing(), "editable": view.scope == org_structure.SCOPE_ALL})
            return True
        _collect_safely()
        days, start, end = _period(qs)
        payload = build(view, days, start, end)
        compare = (qs.get("compare") or [""])[0]
        if compare == "previous":
            prev = build(view, days, start - days * 86400, start)
            payload["previous_totals"] = prev["totals"]
        j(handler, payload)
    except PermissionError as e:
        j(handler, {"error": str(e)}, status=403)
    except KeyError as e:
        j(handler, {"error": str(e).strip("'")}, status=404)
    except Exception:
        logger.exception("GET %s failed", path)
        j(handler, {"error": "internal_error"}, status=500)
    return True


def handle_post(handler, parsed, body) -> bool:
    path = str(getattr(parsed, "path", "") or "")
    if path not in _POST:
        return False
    view = org_structure.request_scope(handler)
    body = body if isinstance(body, dict) else {}
    try:
        if path == "/api/management/pricing":
            if view.scope != org_structure.SCOPE_ALL:
                raise PermissionError("Only organisation admins set prices")
            j(handler, value_tracking.save_pricing(body.get("models") or {}, view.email))
            return True
        if path == "/api/value/collect":
            if view.scope not in (org_structure.SCOPE_ALL, org_structure.SCOPE_DEPARTMENTS):
                raise PermissionError("Not allowed")
            j(handler, value_tracking.collect(force=True))
            return True
        if path == "/api/value/chat":
            key = str(body.get("session_key") or "")
            if not key and body.get("session_id"):
                key = (value_tracking.chat_label_for(str(body["session_id"]), view.email) or {}).get("session_key") or ""
            row = value_tracking.label_chat(key, str(body.get("duty") or ""), view.email, body.get("saved_minutes"))
            j(handler, {"ok": True, "duty": row.get("duty"), "saved_minutes": row.get("saved_minutes")})
            return True
        return _post_job_value(handler, view, body)
    except PermissionError as e:
        j(handler, {"error": str(e)}, status=403)
    except KeyError as e:
        j(handler, {"error": str(e).strip("'")}, status=404)
    except ValueError as e:
        j(handler, {"error": str(e)}, status=400)
    except Exception:
        logger.exception("POST %s failed", path)
        j(handler, {"error": "internal_error"}, status=500)
    return True


def _post_job_value(handler, view, body) -> bool:
    """Set, confirm or clear a job's value (and team).

    Allowed for the job's owner, a cron admin, and organisation or
    department admins for jobs in their teams.
    """
    from api import cron_bots, cron_scope
    from api.governance.enforce import _request_identity

    job_id = str(body.get("job_id") or "")
    store = cron_bots.normalize_profile(body.get("store") or "default")
    job, owner = cron_bots.find_job(job_id, store)
    identity = _request_identity(handler)
    if job is None or not cron_scope.identity_sees_cron_row(identity, job, store_profile=store):
        if job is None or view.scope != org_structure.SCOPE_ALL:
            raise KeyError("Job not found")
    structure = org_structure.load()
    team_now = _job_team(job, structure, _bot_teams(_bots()), store)
    is_owner = cron_scope.identity_owns_cron_job(identity, job)
    is_org = view.scope == org_structure.SCOPE_ALL or (team_now and view.edits_team(team_now))
    try:
        from api.routes import _cron_admin_allowed

        is_admin = bool(_cron_admin_allowed(handler))
    except Exception:
        is_admin = False
    if not (is_owner or is_admin or is_org):
        raise PermissionError("Only the owner of this task, a cron admin or its department admin can set its value")
    action = str(body.get("action") or "set")
    if action == "confirm":
        saved = value_tracking.confirm_job_value(job_id, store, str(body.get("answer") or ""), view.email)
    elif action == "clear":
        saved = value_tracking.set_job_value(job_id, store, None, view.email)
    elif action == "team":
        team = str(body.get("team") or "")
        if team and not (view.scope == org_structure.SCOPE_ALL or view.edits_team(team) or is_owner or is_admin):
            raise PermissionError("You cannot place tasks in this team")
        current = value_tracking.job_value(job) or {}
        if not current:
            saved = _set_team_only(job_id, store, team)
        else:
            if team:
                current["team"] = team
            else:
                current.pop("team", None)
            saved = value_tracking.set_job_value(job_id, store, current, current.get("set_by") or view.email)
    else:
        value = body.get("value")
        if not isinstance(value, dict):
            raise ValueError("value required")
        saved = value_tracking.set_job_value(job_id, store, value, view.email)
    try:
        from api.governance.audit import append_audit_event

        append_audit_event("job_value_changed", subject_email=view.email, subject_user_id="",
                           path="/api/value/job", method="POST", reason=action,
                           extra={"job_id": job_id, "store": store})
    except Exception:
        logger.debug("audit append failed", exc_info=True)
    j(handler, {"ok": True, "value": saved.get("value"), "team": _job_team(saved, org_structure.load())})
    return True


def _set_team_only(job_id: str, store: str, team: str) -> dict:
    """A team without a value yet: kept as ``value: {team, unknown}`` would be
    wrong, so the team rides on a minimal placeholder field."""
    from api import cron_bots
    from api.profiles import cron_profile_context_for_home

    if team and team not in org_structure.team_keys():
        raise ValueError("Unknown team")
    home = cron_bots.home_for_profile(store)
    with cron_profile_context_for_home(home):
        import cron.jobs as cj

        with cron_bots._locked(cj):
            jobs = cj.load_jobs()
            match = next((x for x in jobs if str(x.get("id") or "") == job_id), None)
            if match is None:
                raise KeyError("Job not found")
            value = match.get("value") if isinstance(match.get("value"), dict) else {}
            if team:
                value["team"] = team
            else:
                value.pop("team", None)
            if value:
                match["value"] = value
            else:
                match.pop("value", None)
            cron_bots._save(cj, jobs)
            return dict(match)
