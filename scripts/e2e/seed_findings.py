"""Create synthetic delivered bot updates only inside the isolated browser fixture."""
import os
from pathlib import Path

from isolation import install_guard


def main():
    qa = Path(os.environ["QA_ISOLATION_STATE"]).resolve()
    assert qa == Path(os.environ["QA_STATE"]).resolve() and qa.name == "e2e-state"
    install_guard(qa)
    os.environ.update(HERMES_HOME=str(qa / "home"), HERMES_BASE_HOME=str(qa / "home"),
                      HERMES_WEBUI_STATE_DIR=str(qa / "state"),
                      HERMES_WEBUI_DEFAULT_WORKSPACE=str(qa / "workspace"))
    from api.cron_bots import ensure_job_chat
    from api.cron_webui_delivery import build_update_text, deliver_update_to_session

    for user, profile, days in [("admin", "qa-research", [1, 3]), ("admin", "default", [2, 4]),
                                ("alice", "default", [5])]:
        job = {"id": f"qa-findings-{profile}-{user}", "managed_by": "scout", "name": "Research update"}
        sid, _ = ensure_job_chat(job, profile, f"{user}@example.test")
        for day in days:
            subjects = ["A new supplier published a price list.", "Two deadlines moved to next week.",
                        "Three customer interviews are ready to review.", "The revised proposal is ready for review.",
                        "Private report for Alice."]
            body = subjects[day - 1] + "\n\n" + "The original report includes a dated comparison."
            job["last_run_at"] = f"2026-11-{day:02}T08:00:00+00:00"
            result = build_update_text(job, body=body, run_ok=True, run_error=None)
            ok, error = deliver_update_to_session(sid, result, job, profile=profile)
            assert ok, error


if __name__ == "__main__":
    main()
