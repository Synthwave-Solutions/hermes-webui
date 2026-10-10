"""Coverage for per-cron completion toast notification settings."""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[1]
PANELS_JS = (REPO / "static" / "panels.js").read_text(encoding="utf-8")
CRON_NOTIFY_CSS = (REPO / "static" / "cron-notify.css").read_text(encoding="utf-8")
I18N_JS = (REPO / "static" / "i18n" / "en.js").read_text(encoding="utf-8")
NODE = shutil.which("node")
NOTIFY_START = "// \u2500\u2500 Scheduled task notifications (plan 3.1)"
NOTIFY_END = "// \u2500\u2500 End of scheduled task notifications"
# Appendix G of the plan: the only new strings the notification UI may show.
APPENDIX_G_KEYS = {
    "cron_notify_legend": "Notifications",
    "cron_notify_me_label": "Notify me",
    "cron_notify_me_all": "Every run",
    "cron_notify_me_failures": "Only failures",
    "cron_notify_me_never": "Never",
    "cron_notify_me_off_admin": "Off (admin setting)",
    "cron_notify_delivery_failures_only": "Only send when it fails",
    "cron_notify_delivery_off_notice": "Delivery is off for this task.",
    "cron_notify_hint": "Output is always saved in Scheduled tasks.",
    "cron_notify_hint_managed": "Synthwave support is notified when this fails.",
    "cron_notify_delivery_off_warning": "The messages of this task are its output. With delivery off, nobody receives them.",
    "cron_notify_chip_change": "Change",
    "cron_notify_mute_for_me": "Mute for me",
    "cron_notify_unmute_for_me": "Unmute for me",
    "cron_notify_muted": "Muted",
    "cron_notify_saved": "Notification setting saved",
    "cron_notify_conflict": "This setting changed elsewhere. Reload and try again.",
}


class _JSONHandler:
    def __init__(self):
        self.status = None
        self.headers = {}
        self.response_headers = []
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass


def _payload(handler):
    return json.loads(handler.wfile.getvalue().decode("utf-8"))


def _function_span(name: str) -> tuple[int, int, int]:
    """(start of the declaration, its opening brace, one past its closing brace)."""
    match = re.search(r"(?:async\s+)?function\s+" + re.escape(name) + r"\s*\(", PANELS_JS)
    assert match, f"{name} not found"
    paren = PANELS_JS.index("(", match.start())
    depth = 0
    for idx in range(paren, len(PANELS_JS)):
        ch = PANELS_JS[idx]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                brace = PANELS_JS.find("{", idx)
                break
    else:
        raise AssertionError(f"{name} params did not terminate")
    assert brace != -1, f"{name} body not found"
    depth = 0
    for idx in range(brace, len(PANELS_JS)):
        ch = PANELS_JS[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return match.start(), brace, idx + 1
    raise AssertionError(f"{name} body did not terminate")


def _function_body(name: str) -> str:
    _, brace, end = _function_span(name)
    return PANELS_JS[brace + 1 : end - 1]


def _function_source(name: str) -> str:
    start, _, end = _function_span(name)
    return PANELS_JS[start:end]


def test_cron_recent_marks_muted_jobs_without_requesting_toast(monkeypatch):
    import api.routes as routes

    cron_pkg = types.ModuleType("cron")
    cron_pkg.__path__ = []
    cron_jobs = types.ModuleType("cron.jobs")
    cron_jobs.list_jobs = lambda include_disabled=True: [
        {
            "id": "loud",
            "name": "Loud job",
            "last_run_at": 20,
            "last_status": "success",
        },
        {
            "id": "muted",
            "name": "Muted job",
            "last_run_at": 30,
            "last_status": "success",
            "toast_notifications": False,
        },
    ]
    monkeypatch.setattr(
        routes,
        "_latest_cron_session_info_for_jobs",
        lambda job_ids, completed_job_ids=None: {
            str(job_id): {
                "session_id": f"cron_{job_id}_latest",
                "message_count": 3 if str(job_id) == "loud" else 5,
            }
            for job_id in (completed_job_ids or job_ids)
        },
    )
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    monkeypatch.setitem(sys.modules, "cron.jobs", cron_jobs)

    handler = _JSONHandler()
    routes._handle_cron_recent(handler, SimpleNamespace(query="since=10"))

    body = _payload(handler)
    assert handler.status == 200
    by_id = {item["job_id"]: item for item in body["completions"]}
    assert by_id["loud"]["toast_notifications"] is True
    assert by_id["loud"]["session_id"] == "cron_loud_latest"
    assert by_id["loud"]["message_count"] == 3
    assert by_id["muted"]["toast_notifications"] is False
    assert by_id["muted"]["session_id"] == "cron_muted_latest"
    assert by_id["muted"]["message_count"] == 5


def test_cron_create_persists_muted_toast_setting_after_create(monkeypatch):
    import api.routes as routes

    created = {"id": "job-toast", "name": "Muted", "prompt": "ping"}
    calls = []
    cron_pkg = types.ModuleType("cron")
    cron_pkg.__path__ = []
    cron_jobs = types.ModuleType("cron.jobs")
    cron_jobs.create_job = lambda **kwargs: calls.append(("create", kwargs)) or dict(created)
    cron_jobs.update_job = lambda job_id, updates: calls.append(("update", job_id, updates)) or {**created, **updates}
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    monkeypatch.setitem(sys.modules, "cron.jobs", cron_jobs)

    handler = _JSONHandler()
    routes._handle_cron_create(
        handler,
        {
            "prompt": "ping",
            "schedule": "every 1h",
            "toast_notifications": False,
        },
    )

    assert handler.status == 200
    assert calls[0][0] == "create"
    assert calls[1] == ("update", "job-toast", {"toast_notifications": False, "notify": {"in_app": "quiet", "delivery": "all"}})
    assert _payload(handler)["job"]["toast_notifications"] is False


def _run_node(script: str) -> dict:
    result = subprocess.run([NODE, "-e", script], check=True, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


def _optional_functions(*names: str) -> str:
    """The declarations that exist (a base without them runs the old code)."""
    return "\n".join(_function_source(name) for name in names
                     if re.search(r"function\s+" + re.escape(name) + r"\s*\(", PANELS_JS))


# Owner-only actions (W0 follow-up).

_HEADER_BUTTONS = ("Run", "Pause", "Resume", "Edit", "Share", "Duplicate", "Delete", "Cancel", "Save")


def _detail_buttons_for(me: dict, job: dict) -> dict:
    """Render the task detail header for ``job`` as the signed-in ``me``."""
    ids = [f"btn{name}TaskDetail" for name in _HEADER_BUTTONS]
    script = f"""
const els = {{}};
for (const id of {json.dumps(ids)}) els[id] = {{ style: {{ display: 'none' }} }};
els.mainTasks = {{ querySelector: () => ({{ style: {{}} }}) }};
globalThis.window = globalThis;
window.__GOV_ME__ = {json.dumps(me)};
function $(id) {{ return els[id] || null; }}
function t(key) {{ return key; }}
function esc(s) {{ return String(s); }}
function _canUseFeature(p) {{ return !!(window.__GOV_ME__.feature_permissions || {{}})[p]; }}
function _cronStatusMeta() {{ return {{ state: 'active' }}; }}
{_optional_functions("_cronIsCronAdmin", "_cronCanEdit", "_cronCanCreate")}
{_function_source("_setCronHeaderButtons")}
_setCronHeaderButtons('read', {json.dumps(job)});
const out = {{}};
for (const name of {json.dumps(list(_HEADER_BUTTONS))}) out[name] = els['btn' + name + 'TaskDetail'].style.display !== 'none';
process.stdout.write(JSON.stringify(out));
"""
    return _run_node(script)


@pytest.mark.skipif(NODE is None, reason="node not on PATH")
def test_sharee_sees_no_owner_only_task_actions():
    """W0 follow-up: a sharee got Run, Pause, Resume and Delete buttons that
    all answer 403 (only the owner or a cron admin may use them)."""
    job = {"id": "job-1", "state": "scheduled", "owner_email": "owner@example.com",
           "shared_with": ["sharee@example.com"], "origin": {"platform": "webui", "user_id": "owner@example.com"}}
    sharee = {"email": "sharee@example.com", "mode": "enforce", "method": "oidc",
              "permissions": ["cron:read", "cron:write"], "feature_permissions": {"cron:write": True}}
    shown = _detail_buttons_for(sharee, job)
    assert shown == {"Run": False, "Pause": False, "Resume": False, "Edit": False, "Share": False,
                     "Duplicate": True, "Delete": False, "Cancel": False, "Save": False}
    owner = {**sharee, "email": "owner@example.com"}
    assert _detail_buttons_for(owner, job) == {"Run": True, "Pause": True, "Resume": False, "Edit": True,
                                               "Share": True, "Duplicate": True, "Delete": True,
                                               "Cancel": False, "Save": False}
    # The server's can_edit flag, when it sends one, decides.
    assert _detail_buttons_for(sharee, {**job, "can_edit": True})["Run"] is True


# Copies of a task (W0 follow-up).

@pytest.mark.skipif(NODE is None, reason="node not on PATH")
def test_duplicate_of_a_custom_delivery_target_falls_back_to_local():
    """W0 follow-up: duplicating a task with a custom delivery target answered
    403 for a non-admin, because the form kept that target selected."""
    script = f"""
function el(tag) {{ return {{ tag, value: '', selected: false, children: [], disabled: false,
  set innerHTML(v) {{ this.children = []; }}, get innerHTML() {{ return ''; }},
  appendChild(c) {{ this.children.push(c); return c; }}, prepend(c) {{ this.children.unshift(c); }},
  querySelector(s) {{ const m = /option\\[value="([^"]*)"\\]/.exec(s); return m ? this.children.find(c => c.value === m[1]) || null : null; }} }}; }}
const sel = el('select');
globalThis.document = {{ createElement: el }};
globalThis.CSS = {{ escape: v => String(v) }};
function $(id) {{ return id === 'cronFormDeliver' ? sel : null; }}
async function api() {{ return {{ platforms: [{{ value: 'local', label: 'Local' }}, {{ value: 'telegram', label: 'Telegram' }}] }}; }}
var _cronDeliveryOptionsCache = null;
function _syncCronNotifyDeliveryControl() {{}}
{_function_source("_populateCronDeliverOptions")}
(async () => {{
  await _populateCronDeliverOptions('telegram:12345', false);
  const copy = sel.children.map(o => [o.value, !!o.selected]);
  _cronDeliveryOptionsCache = null;
  await _populateCronDeliverOptions('telegram:12345', true);
  const edit = sel.children.map(o => [o.value, !!o.selected]);
  process.stdout.write(JSON.stringify({{ copy, edit }}));
}})().catch(e => {{ console.error(e); process.exit(1); }});
"""
    result = _run_node(script)
    assert result["copy"] == [["local", True], ["telegram", False]]
    assert result["edit"] == [["telegram:12345", True], ["local", False], ["telegram", False]]
    body = _function_body("_renderCronForm")
    assert "_populateCronDeliverOptions(deliver, isEdit || _cronIsCronAdmin());" in body


@pytest.mark.skipif(NODE is None, reason="node not on PATH")
def test_duplicate_drops_skills_outside_the_viewers_grants():
    """W0 follow-up: a copy carrying a skill the viewer may not use answered 403."""
    script = f"""
globalThis.window = globalThis;
window.__GOV_ME__ = {{ email: 'sharee@example.com', mode: 'enforce', method: 'oidc', permissions: ['cron:write'], feature_permissions: {{ 'cron:write': true }} }};
var _currentCronDetail = {{ id: 'j', name: 'Report', skills: ['granted-skill', 'secret-skill'], deliver: 'local', schedule: {{ kind: 'cron', expr: '0 9 * * *' }} }};
var _cronPreFormDetail = null, _editingCronId = null, _cronMode = 'empty', _cronIsDuplicate = false;
var _cronSelectedSkills = [], _cronSkillsCache = null, _cronList = [], _currentPanel = 'tasks';
function t(k) {{ return k; }}
function esc(s) {{ return String(s); }}
function _canUseFeature() {{ return true; }}
function _renderCronForm() {{}}
function _renderCronSkillTags() {{}}
function _bindCronSkillPicker() {{}}
function _cronEditableSchedule() {{ return '0 9 * * *'; }}
async function api() {{ return {{ skills: [{{ name: 'granted-skill' }}] }}; }}
function _cronDuplicateNotify() {{ return null; }}
{_optional_functions("_cronIsCronAdmin")}
{_function_source("duplicateCurrentCron")}
duplicateCurrentCron();
setTimeout(() => process.stdout.write(JSON.stringify({{ skills: _cronSelectedSkills }})), 20);
"""
    assert _run_node(script) == {"skills": ["granted-skill"]}


# Notification settings (plan 3.1).

def _notify_block() -> str:
    start = PANELS_JS.index(NOTIFY_START)
    return PANELS_JS[start:PANELS_JS.index(NOTIFY_END, start)]


def test_cron_form_has_notify_controls_and_saves_levels():
    render_body = _function_body("_renderCronForm")
    save_body = _function_body("saveCronForm")
    edit_body = _function_body("openCronEdit")
    create_body = _function_body("openCronCreate")
    duplicate_body = _function_body("duplicateCurrentCron")
    detail_body = _function_body("_renderCronDetail")
    fieldset = _function_body("_cronNotifyFieldsetHtml")

    # "Notify me" in a Notifications fieldset; "Only send when it fails"
    # beside the delivery target.
    assert "_cronNotifyFieldsetHtml(notifyState, support_notified === true)" in render_body
    assert "_cronNotifyDeliveryHtml(notifyState, 'cronFormNotifyDeliveryFailures', deliver)" in render_body
    assert render_body.index('id="cronFormDeliver"') < render_body.index("_cronNotifyDeliveryHtml(")
    assert "cronFormToastNotifications" not in render_body
    assert 'data-tour="tasks-notify"' in fieldset
    assert "t('cron_notify_legend')" in fieldset
    assert "'cronFormNotifyInApp'" in fieldset
    assert "_cronFormNotifyBase = { in_app: notifyState.in_app, delivery: notifyState.delivery };" in render_body

    # Defaults for new tasks and the task's own levels for edits and copies.
    assert "notify:_cronDefaultNotify('')" in create_body
    assert "notify: _cronNotifyOf(job)" in edit_body
    assert "support_notified: job.support_notified === true" in edit_body
    assert "notify: _cronDuplicateNotify(job, isCronAdmin)" in duplicate_body

    # toast_notifications follows the in-app level for older clients; notify
    # is written on create and only when a level changed on edit.
    assert "const notify=_cronNotifyFromControls('cronForm', notifyBase);" in save_body
    assert "const toastNotifications=_cronLegacyToast(notify.in_app);" in save_body
    assert "toast_notifications: toastNotifications" in save_body
    assert "if (_cronNotifySupported && _cronNotifyChanged(notify, notifyBase)) updates.notify = notify;" in save_body
    assert "if(_cronNotifySupported) body.notify=notify;" in save_body

    assert "_cronNotifyDetailRowHtml(job)" in detail_body
    assert "job.delivery_status === 'muted'" in detail_body
    assert "t('cron_notify_muted')" in detail_body


def test_cron_polling_uses_flags_with_toast_notifications_fallback():
    body = _function_body("startCronPolling")
    flags = _function_body("_cronCompletionFlags")

    assert "const flags=_cronCompletionFlags(c);" in body
    # A hidden tab polls only for desktop notifications the viewer turned on.
    assert "if(document.hidden && !(typeof window!=='undefined' && window._notificationsEnabled)) return;" in body
    assert "if(flags.toast){" in body
    assert "showToast(statusText,4000);" in body
    assert "t('cron_completion_status', c.name" in body
    assert "if(flags.desktop && typeof sendBrowserNotification==='function')" in body
    assert "if(!flags.badge) continue;" in body
    assert "if(c.job_id) _cronNewJobIds.add(String(c.job_id));" in body
    # Absent flags (a server without notify): toast_notifications decides.
    assert "c.toast_notifications !== false" in flags
    assert "const silent = c.silent === true;" in flags


def test_cron_toast_i18n_keys_exist():
    assert "cron_toast_notifications_label" in I18N_JS
    assert "cron_toast_notifications_hint" in I18N_JS
    assert "cron_toast_notifications_enabled" in I18N_JS
    assert "cron_toast_notifications_disabled" in I18N_JS


def test_cron_notify_keys_are_appendix_g_in_fallback_locale():
    # Runtime locale merging inherits new strings from en.js.
    for key, value in APPENDIX_G_KEYS.items():
        assert re.search(r"\n\s*" + key + r":\s*'", I18N_JS), key


def test_notify_ui_adds_no_string_outside_appendix_g():
    block = _notify_block()
    used = set(re.findall(r"\bt\('([a-z0-9_]+)'", block))
    used |= set(re.findall(r"'(cron_notify_[a-z_]+)'", block))
    assert used <= set(APPENDIX_G_KEYS) | {"cancel", "save", "error_prefix"}, used
    assert set(APPENDIX_G_KEYS) <= used, set(APPENDIX_G_KEYS) - used
    # Every visible text in the block comes from t(): no hard-coded fallbacks.
    assert not re.search(r"\|\|\s*'[A-Z]", block)
    for name in ("_renderCronDetail", "_renderCronForm", "startCronPolling", "_setCronHeaderButtons"):
        body = _function_body(name)
        for key in re.findall(r"\bt\('(cron_notify_[a-z_]+)'", body):
            assert key in APPENDIX_G_KEYS, (name, key)


def test_no_en_or_em_dash_in_notify_ui():
    dashes = re.compile("[\u2013\u2014]")
    assert not dashes.search(_notify_block())
    assert not dashes.search(CRON_NOTIFY_CSS)
    assert not dashes.search((REPO / "tests" / "cron_notify_ui.cjs").read_text(encoding="utf-8"))
    for name in ("startCronPolling", "_setCronHeaderButtons", "_cronMetaBarHtml", "duplicateCurrentCron"):
        assert not dashes.search(_function_body(name)), name


def test_cron_notify_css_styles_the_new_controls():
    for selector in (".cron-notify-fieldset", ".cron-notify-deliver-row", ".cron-notify-failures-only[hidden]",
                     ".cron-notify-chip", ".cron-notify-muted-icon", ".cron-notify-dialog", "@media (max-width:640px)"):
        assert selector in CRON_NOTIFY_CSS, selector
    # Theme tokens only: no hard-coded colours.
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", CRON_NOTIFY_CSS)



def test_cron_notify_ui_behaviour_harness():
    result = subprocess.run([NODE, str(REPO / "tests" / "cron_notify_ui.cjs"), str(REPO)],
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "cron notification UI scenarios passed" in result.stdout
