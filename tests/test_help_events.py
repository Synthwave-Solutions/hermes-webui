"""Help usage counters: counts only, never an identity (plan 6.1, 6.2, W4).

``POST /api/help/events`` adds one to a counter per event, per page or tour
id and per UTC day in ``help_events.json`` in the WebUI state directory. It
never reads or stores who sent it, answers 204 for every report (also the
ones it drops) and keeps the file bounded.
"""

import copy
import io
import json
import threading
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from api import help_events

MEMBER = "ada.member@example.com"


class _Handler:
    """A request handler as far as the route uses it, with an identity attached."""

    def __init__(self):
        self.status = None
        self.response_headers = []
        self.wfile = io.BytesIO()
        self.client_address = ("203.0.113.7", 50123)
        self.headers = {
            "Cookie": "hermes_session=secret-session-value",
            "User-Agent": "HelpTest/1.0",
            "X-Forwarded-For": "198.51.100.9",
            "Tailscale-User-Login": MEMBER,
        }

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass

    @property
    def raw(self):
        return self.wfile.getvalue()


@pytest.fixture
def state(tmp_path, monkeypatch):
    from api import config

    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.delenv(help_events.RETENTION_ENV, raising=False)
    return tmp_path


def _stored(state):
    path = state / help_events.FILE_NAME
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _post(body):
    handler = _Handler()
    assert help_events.handle_post(handler, body) is True
    assert handler.status == 204
    assert handler.raw == b""
    assert ("Content-Length", "0") in handler.response_headers
    return handler


def test_each_event_counts_per_page_or_tour_and_day(state):
    today = date.today().isoformat()
    for body in (
        {"event": "explain_clicked", "page": "tasks"},
        {"event": "explain_clicked", "page": "tasks"},
        {"event": "explain_clicked", "page": "memory"},
        {"event": "did_not_help", "page": "tasks"},
        {"event": "tour_started", "tour": "first_run"},
        {"event": "tour_completed", "tour": "first_run"},
    ):
        _post(body)
    stored = _stored(state)
    assert stored["version"] == 1
    (day,) = stored["days"]
    # The counter uses the UTC date; around midnight it can differ from local.
    assert abs((date.fromisoformat(day) - date.fromisoformat(today)).days) <= 1
    assert stored["days"][day] == {
        "explain_clicked": {"tasks": 2, "memory": 1},
        "did_not_help": {"tasks": 1},
        "tour_started": {"first_run": 1},
        "tour_completed": {"first_run": 1},
    }
    assert help_events.summary() == stored["days"][day]


def test_no_identity_or_request_detail_is_ever_stored(state, monkeypatch):
    import api.governance.enforce as enforce

    # Even with a resolvable signed-in person on the request, nothing about
    # them reaches the file: the handler is never asked who is calling.
    monkeypatch.setattr(enforce, "_request_identity",
                        lambda handler: SimpleNamespace(email=MEMBER, groups=["staff"]))
    _post({"event": "explain_clicked", "page": "tasks", "email": MEMBER,
           "user": MEMBER, "session_id": "s-123", "note": "free text from the client"})
    text = (state / help_events.FILE_NAME).read_text(encoding="utf-8")
    for leaked in (MEMBER, "ada", "s-123", "free text", "203.0.113.7", "198.51.100.9",
                   "secret-session-value", "HelpTest", "staff", "note", "email", "user"):
        assert leaked not in text, leaked
    stored = json.loads(text)
    assert set(stored) == {"version", "days"}
    for bucket in stored["days"].values():
        for counts in bucket.values():
            assert all(isinstance(v, int) for v in counts.values())


@pytest.mark.parametrize("body", [
    None,
    [],
    "explain_clicked",
    {},
    {"message": "x"},
    {"event": "tour_started"},
    {"event": "page_viewed", "page": "tasks"},
    {"event": "explain_clicked"},
    {"event": "explain_clicked", "page": ""},
    {"event": "explain_clicked", "page": "Tasks"},
    {"event": "explain_clicked", "page": "tasks/../x"},
    {"event": "explain_clicked", "page": "x" * 41},
    {"event": "explain_clicked", "page": 7},
    {"event": "explain_clicked", "tour": "first_run"},
    {"event": "tour_started", "page": "first_run"},
    {"event": "did_not_help", "page": "ada@example.com"},
])
def test_a_malformed_report_answers_204_and_stores_nothing(state, body):
    _post(body)
    assert _stored(state) is None


def test_dispatch_routes_the_post_to_the_counter(state, monkeypatch):
    import api.routes as routes

    body = {"event": "explain_clicked", "page": "kanban"}
    monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
    monkeypatch.setattr(routes, "read_body", lambda _handler: copy.deepcopy(body))
    monkeypatch.setattr(routes, "_guard_request_session_visibility",
                        lambda handler, parsed, body=None, method="GET": True)
    handler = _Handler()
    routes.handle_post(handler, SimpleNamespace(path="/api/help/events", query=""))
    assert handler.status == 204
    assert help_events.summary() == {"explain_clicked": {"kanban": 1}}


def test_route_is_an_authenticated_self_route():
    from api.governance import catalog

    # Every signed-in person may report a count; nobody else reaches it.
    assert "/api/help/events" in catalog._SELF_ROUTES


def test_counts_are_capped_and_new_ids_stop_at_the_daily_limit(state, monkeypatch):
    monkeypatch.setattr(help_events, "MAX_KEYS_PER_EVENT_PER_DAY", 3)
    for page in ("aa", "bb", "cc"):
        assert help_events.record("explain_clicked", page) is True
    assert help_events.record("explain_clicked", "dd") is False
    assert help_events.record("explain_clicked", "aa") is True
    totals = help_events.summary()["explain_clicked"]
    assert totals == {"aa": 2, "bb": 1, "cc": 1}
    monkeypatch.setattr(help_events, "MAX_COUNT", 2)
    assert help_events.record("explain_clicked", "aa") is True
    assert help_events.summary()["explain_clicked"]["aa"] == 2


def test_old_days_are_pruned_by_the_retention_window(state, monkeypatch):
    monkeypatch.setenv(help_events.RETENTION_ENV, "30")
    today = date(2026, 9, 28)
    help_events.record("explain_clicked", "tasks", today=today - timedelta(days=40))
    help_events.record("explain_clicked", "tasks", today=today - timedelta(days=29))
    help_events.record("explain_clicked", "memory", today=today)
    days = _stored(state)["days"]
    assert sorted(days) == [(today - timedelta(days=29)).isoformat(), today.isoformat()]
    assert help_events.retention_days() == 30
    for bad in ("0", "-5", "junk", "99999"):
        monkeypatch.setenv(help_events.RETENTION_ENV, bad)
        assert help_events.retention_days() == help_events.DEFAULT_RETENTION_DAYS


def test_a_tampered_file_is_cleaned_to_counts_only(state):
    path = state / help_events.FILE_NAME
    path.write_text(json.dumps({
        "version": 1,
        "people": {MEMBER: 3},
        "days": {
            "2026-09-27": {
                "explain_clicked": {"tasks": 4, MEMBER: 1, "chat": "7", "memory": True},
                "who": {"tasks": 1},
            },
            "yesterday": {"explain_clicked": {"tasks": 1}},
        },
    }), encoding="utf-8")
    help_events.record("did_not_help", "tasks", today=date(2026, 9, 28))
    stored = _stored(state)
    assert stored == {"version": 1, "days": {
        "2026-09-27": {"explain_clicked": {"tasks": 4}},
        "2026-09-28": {"did_not_help": {"tasks": 1}},
    }}


def test_an_unreadable_file_is_replaced_and_the_request_still_answers_204(state):
    (state / help_events.FILE_NAME).write_text("{not json", encoding="utf-8")
    _post({"event": "explain_clicked", "page": "tasks"})
    assert help_events.summary() == {"explain_clicked": {"tasks": 1}}


def test_a_write_failure_never_fails_the_request(state, monkeypatch):
    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(help_events, "_write", boom)
    _post({"event": "explain_clicked", "page": "tasks"})
    assert _stored(state) is None


def test_the_counter_file_is_private_to_the_service_account(state):
    help_events.record("explain_clicked", "tasks")
    mode = (state / help_events.FILE_NAME).stat().st_mode & 0o777
    assert mode == 0o600
    assert not list(state.glob(".help_events.*.tmp"))


def test_concurrent_reports_are_all_counted(state):
    def worker():
        for _ in range(25):
            help_events.record("explain_clicked", "chat")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert help_events.summary() == {"explain_clicked": {"chat": 200}}


def test_summary_filters_one_month(state):
    help_events.record("explain_clicked", "tasks", today=date(2026, 8, 31))
    help_events.record("explain_clicked", "tasks", today=date(2026, 9, 1))
    help_events.record("explain_clicked", "tasks", today=date(2026, 9, 2))
    assert help_events.summary("2026-09") == {"explain_clicked": {"tasks": 2}}
    assert help_events.summary("2026-08") == {"explain_clicked": {"tasks": 1}}
    with pytest.raises(ValueError):
        help_events.summary("September")
