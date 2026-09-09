#!/usr/bin/env python3
"""Bounded API smoke against an explicitly selected deployed loopback service.

Prepared only: no requests occur without --execute. Run with the deployed
interpreter and HERMES_WEBUI_PASSWORD inherited from the service environment.
Never pass a password or cookie on the command line. This is not browser QA.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import requests


class SmokeFailure(Exception):
    pass


def require(condition, label):
    if not condition:
        raise SmokeFailure(label)


def source(directory):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=directory, stderr=subprocess.DEVNULL)
    head = git("rev-parse", "HEAD").decode().strip()
    require(bool(re.fullmatch(r"[0-9a-f]{40,64}", head)), "invalid_source_revision")
    dirty = git("status", "--porcelain", "--untracked-files=normal")
    tracked = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=directory,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode
    require(tracked in (0, 1), "cannot_verify_tracked_source")
    raw_untracked = git("ls-files", "--others", "--exclude-standard", "-z")
    untracked = sorted(path for path in raw_untracked.decode().split("\0") if path)
    return {"commit": head, "dirty": bool(dirty), "tracked_dirty": tracked != 0,
            "untracked_paths": untracked, "untracked_count": len(untracked),
            "untracked_sha256": hashlib.sha256(raw_untracked).hexdigest(),
            "status_sha256": hashlib.sha256(dirty).hexdigest()}


def require_permitted_source(metadata, allowed_untracked_dirs):
    # Only this known browser artifact directory may be explicitly permitted.
    # Its tracked contents are still code and can never bypass the diff gate.
    require(set(allowed_untracked_dirs) <= {".playwright-mcp"}, "unsupported_untracked_exception")
    require(not metadata["tracked_dirty"], "deployed_tracked_source_is_dirty")
    require(all(any(path.startswith(directory + "/") for directory in allowed_untracked_dirs)
                for path in metadata["untracked_paths"]), "deployed_untracked_source_is_unreviewed")


class Smoke:
    def __init__(self, args):
        self.args = args
        self.http = requests.Session()
        self.http.trust_env = False
        self.anon = requests.Session()
        self.anon.trust_env = False
        self.deadline = time.monotonic() + 120
        self.cleanup_mode = False
        self.nonce = uuid.uuid4().hex
        self.title = "QA production smoke " + self.nonce
        self.revised_title = self.title + " refreshed"
        self.messages = [{"role": "user", "content": "Synthetic release verification " + self.nonce},
                         {"role": "assistant", "content": "Synthetic snapshot fixture; no model execution."}]
        self.sid = None
        self.token = None
        self.board = None
        self.task_ids = set()
        self.task_details = {}
        self.board_requested = "qa-smoke-" + self.nonce[:20]
        self.initial_board = None
        self.report = {"kind": "deployed_api_smoke", "run_id": self.nonce,
            "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "http": [], "checks": {}, "cleanup": {}, "assets": {},
            "browser_viewports": [{"width": 1440, "height": 1000, "status": "NOT_RUN_API_ONLY"},
                                  {"width": 390, "height": 844, "status": "NOT_RUN_API_ONLY"}],
            "voice": {"provider_negotiation": "NOT_RUN_REQUIRES_REAL_BROWSER",
                      "physical_microphone": "NOT_TESTABLE_BY_VPS_API_SCRIPT",
                      "audio_quality": "NOT_TESTED"}}

    def call(self, label, method, path, body=None, *, anonymous=False, expected=(200,)):
        require(path.startswith("/") and not path.startswith("//"), "invalid_request_path")
        if not self.cleanup_mode:
            require(time.monotonic() < self.deadline, "smoke_deadline_exceeded")
        client = self.anon if anonymous else self.http
        response = client.request(method, self.args.base_url + path, json=body,
                                  timeout=10, allow_redirects=False)
        # Labels are fixed code strings: no public token, cookie, URL, or body.
        self.report["http"].append({"operation": label, "method": method, "status": response.status_code})
        require(response.status_code in expected, label + "_unexpected_http_status")
        return response

    def payload(self, label, method, path, body=None, **kwargs):
        response = self.call(label, method, path, body, **kwargs)
        try:
            result = response.json()
        except ValueError:
            raise SmokeFailure(label + "_invalid_json") from None
        require(isinstance(result, dict), label + "_invalid_envelope")
        return result

    @staticmethod
    def persisted_task_detail(detail):
        # The API computes these two aliases from the current clock. All
        # persisted task fields, events, comments, links and runs stay exact.
        task = {key: value for key, value in detail.get("task", {}).items()
                if key not in {"age", "age_seconds"}}
        return {**detail, "task": task}

    def assert_manual_transition(self, detail, status):
        """Accept the engine's instant audit row, never a claimed worker run."""
        task = detail.get("task") or {}
        require(task.get("status") == status, "task_status_not_persisted_" + status)
        require(not detail.get("comments") and detail.get("links") == {"parents": [], "children": []}, "unexpected_task_external_activity")
        require(all(task.get(key) is None for key in ("assignee", "worker_pid", "current_run_id", "claim_lock", "claim_expires")),
                "unexpected_task_worker_state")
        event_kinds = [event.get("kind") for event in detail.get("events", [])]
        expected_event = "completed" if status == "done" else "blocked"
        require(event_kinds == ["created", "status", expected_event], "unexpected_task_worker_events")
        runs = detail.get("runs") or []
        require(len(runs) == 1, "unexpected_manual_audit_run_count")
        run = runs[0]
        outcome = "completed" if status == "done" else "blocked"
        summary = "Synthetic manual transition" if status == "done" else "Synthetic release smoke"
        require(run.get("task_id") == task.get("id") and run.get("status") == outcome
                and run.get("outcome") == outcome and run.get("summary") == summary,
                "unexpected_manual_audit_content")
        require(isinstance(run.get("started_at"), (int, float))
                and run["started_at"] == run.get("ended_at"), "unexpected_manual_audit_duration")
        require(all(run.get(key) is None for key in ("profile", "step_key", "worker_pid", "claim_lock", "claim_expires",
                    "last_heartbeat_at", "max_runtime_seconds", "metadata", "error")), "unexpected_task_worker_run")

    def run(self):
        self.report["source_before"] = {"webui": source(self.args.webui_repo), "engine": source(self.args.engine_repo)}
        if self.args.expect_webui:
            require(self.report["source_before"]["webui"]["commit"] == self.args.expect_webui, "webui_revision_mismatch")
        if self.args.expect_engine:
            require(self.report["source_before"]["engine"]["commit"] == self.args.expect_engine, "engine_revision_mismatch")
        allowed_untracked_dirs = getattr(self.args, "allow_untracked_dir", []) or []
        self.report["allowed_untracked_artifact_dirs"] = allowed_untracked_dirs
        for item in self.report["source_before"].values():
            require_permitted_source(item, allowed_untracked_dirs)
        password = os.environ.get("HERMES_WEBUI_PASSWORD", "").strip()
        require(bool(password), "runtime_password_environment_missing")
        self.http.headers["Origin"] = self.args.base_url
        self.payload("password_login", "POST", "/api/auth/login", {"password": password})
        password = None
        require(bool(self.http.cookies), "authenticated_session_cookie_missing")
        shell = self.call("authenticated_shell", "GET", "/").text
        found = re.search(r'csrfToken:("(?:\\.|[^"\\])*")', shell)
        require(found is not None, "authenticated_csrf_token_missing")
        self.http.headers["X-Hermes-CSRF-Token"] = json.loads(found.group(1))
        require(bool(self.http.headers["X-Hermes-CSRF-Token"]), "empty_csrf_token")
        del shell, found
        for name in ("governance.js", "realtime_voice.js", "messages.js", "ui.js", "style.css", "share.js"):
            response = self.call("asset_" + name, "GET", "/static/" + name)
            served = hashlib.sha256(response.content).hexdigest()
            disk = hashlib.sha256((self.args.webui_repo / "static" / name).read_bytes()).hexdigest()
            self.report["assets"][name] = {"response_sha256": served, "disk_sha256": disk,
                                           "bytes": len(response.content), "matches_disk": served == disk}
            require(served == disk, "served_asset_revision_mismatch_" + name)

        # Import creates exactly one NEW authenticated-owned session and invokes
        # no model, connector, skill, shell, provider or messaging transport.
        created = self.payload("create_synthetic_session", "POST", "/api/session/import",
            {"title": self.title, "workspace": str(self.args.workspace), "messages": self.messages})
        self.sid = str((created.get("session") or {}).get("session_id") or "")
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", self.sid)), "created_session_id_missing")
        require(created["session"]["title"] == self.title, "created_session_marker_mismatch")
        self.report["created_session_id"] = self.sid

        published = self.payload("share_create", "POST", "/api/share/create", {"session_id": self.sid})
        self.token = str((published.get("share") or {}).get("token") or "")
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]{24}", self.token)), "invalid_created_share_token")
        require(published["share"].get("url") == "/share/" + self.token, "invalid_created_share_url")
        self.report["share_token_sha256"] = hashlib.sha256(self.token.encode()).hexdigest()
        before = self.payload("anonymous_share_read", "GET", "/api/share/" + self.token, anonymous=True)["share"]
        require(before.get("title") == self.title and before.get("messages") == self.messages, "public_snapshot_mismatch")
        require(set(before) <= {"title", "messages", "message_count", "created_at", "updated_at"}, "public_metadata_leak")
        self.call("anonymous_share_page", "GET", "/share/" + self.token, anonymous=True)
        self.payload("rename_owned_session", "POST", "/api/session/rename", {"session_id": self.sid, "title": self.revised_title})
        unchanged = self.payload("immutable_share_read", "GET", "/api/share/" + self.token, anonymous=True)["share"]
        require(unchanged == before, "snapshot_changed_without_refresh")
        refreshed = self.payload("share_explicit_refresh", "POST", "/api/share/create", {"session_id": self.sid})
        require(refreshed["share"]["token"] == self.token, "refresh_replaced_active_url")
        current = self.payload("refreshed_share_read", "GET", "/api/share/" + self.token, anonymous=True)["share"]
        require(current.get("title") == self.revised_title and current.get("messages") == self.messages, "refresh_not_persisted")
        self.payload("share_revoke", "POST", "/api/share/revoke", {"session_id": self.sid})
        self.call("revoked_share_page", "GET", "/share/" + self.token, anonymous=True, expected=(404,))
        self.call("revoked_share_json", "GET", "/api/share/" + self.token, anonymous=True, expected=(404,))
        self.report["checks"]["share_create_read_immutable_refresh_revoke"] = True

        boards = self.payload("boards_before", "GET", "/api/kanban/boards?include_archived=1")
        self.initial_board = boards.get("current")
        require(not any(b.get("slug") == self.board_requested for b in boards.get("boards", [])), "synthetic_board_collision")
        created_board = self.payload("create_owned_board", "POST", "/api/kanban/boards",
            {"slug": self.board_requested, "name": self.title, "description": self.nonce, "switch": False})
        require((created_board.get("board") or {}).get("slug") == self.board_requested, "created_board_mismatch")
        self.board = self.board_requested
        require(created_board.get("current") == self.initial_board, "active_board_changed_by_create")
        self.report["created_board_slug"] = self.board
        for status in ("done", "blocked"):
            created_task = self.payload("create_todo_for_" + status, "POST", "/api/kanban/tasks",
                {"board": self.board, "title": self.title + " " + status, "body": self.nonce,
                 "status": "todo", "assignee": None, "workspace_kind": "scratch"})
            task = created_task.get("task") or {}
            task_id = str(task.get("id") or "")
            require(bool(re.fullmatch(r"[A-Za-z0-9_-]+", task_id)) and task.get("status") == "todo", "todo_creation_mismatch")
            self.task_ids.add(task_id)
            path = "/api/kanban/tasks/" + task_id + "?board=" + self.board
            initial = self.payload("verify_fresh_todo_" + status, "GET", path)
            require(not initial.get("comments") and not initial.get("runs") and initial.get("links") == {"parents": [], "children": []},
                    "fresh_task_has_external_activity")
            initial_events = initial.get("events", [])
            require([event.get("kind") for event in initial_events] == ["created", "status"],
                    "fresh_task_has_unexpected_events")
            require(initial_events[1].get("payload") == {"status": "todo", "source": "webui"},
                    "fresh_task_has_unexpected_status_event")
            self.task_details[task_id] = self.persisted_task_detail(initial)
            self.payload("todo_to_" + status, "PATCH", path,
                         {"status": status, "reason": "Synthetic release smoke", "summary": "Synthetic manual transition"})
            durable = self.payload("verify_" + status, "GET", path)
            self.assert_manual_transition(durable, status)
            self.task_details[task_id] = self.persisted_task_detail(durable)
            self.report["checks"]["todo_to_" + status] = True
        voice = self.payload("voice_capability", "GET", "/api/voice/realtime/capability")
        self.report["voice"]["capability_available"] = voice.get("available") is True
        self.report["voice"]["configured_model"] = voice.get("model") if isinstance(voice.get("model"), str) else None
        self.report["source_after"] = {"webui": source(self.args.webui_repo), "engine": source(self.args.engine_repo)}
        require(self.report["source_before"] == self.report["source_after"], "source_changed_during_smoke")
        self.report["api_smoke_passed"] = True

    def cleanup(self):
        self.cleanup_mode = True
        cleanup = self.report["cleanup"]
        if self.sid:
            try:
                current = self.payload("cleanup_owned_session_read", "GET", "/api/session?session_id=" + self.sid).get("session") or {}
                require(current.get("title") in (self.title, self.revised_title) and current.get("messages") == self.messages,
                        "cleanup_session_contains_unexpected_user_changes")
                self.payload("cleanup_share_revoke", "POST", "/api/share/revoke", {"session_id": self.sid})
                if self.token:
                    self.call("cleanup_confirm_revoke", "GET", "/api/share/" + self.token, anonymous=True, expected=(404,))
                self.payload("cleanup_owned_session_delete", "POST", "/api/session/delete", {"session_id": self.sid})
                self.call("cleanup_confirm_session_deleted", "GET", "/api/session?session_id=" + self.sid, expected=(404,))
                cleanup["synthetic_session_deleted"] = True
                cleanup["public_link_unavailable"] = True
                cleanup["revoked_snapshot_tombstone"] = "retained_by_application"
            except Exception as exc:  # noqa: BLE001 - sanitize failure and continue owned cleanup.
                cleanup["session_error"] = str(exc) if isinstance(exc, SmokeFailure) else type(exc).__name__
        if self.board:
            try:
                boards = self.payload("cleanup_owned_board_read", "GET", "/api/kanban/boards?include_archived=1")
                owned = next((b for b in boards.get("boards", []) if b.get("slug") == self.board), None)
                require(owned and owned.get("name") == self.title and owned.get("description") == self.nonce,
                        "cleanup_board_marker_mismatch")
                require(boards.get("current") != self.board, "cleanup_board_is_now_selected")
                content = self.payload("cleanup_owned_board_tasks", "GET", "/api/kanban/board?board=" + self.board + "&include_archived=1")
                tasks = [task for column in content.get("columns", []) for task in column.get("tasks", [])]
                require({task.get("id") for task in tasks} == self.task_ids, "cleanup_board_contains_unexpected_tasks")
                for task in tasks:
                    require(task.get("title") in {self.title + " done", self.title + " blocked"}
                            and task.get("body") == self.nonce and not task.get("assignee"), "cleanup_task_was_changed")
                    detail = self.payload("cleanup_verify_task_ownership", "GET", "/api/kanban/tasks/" + task["id"] + "?board=" + self.board)
                    # Exact readback includes events, timestamps, attachments and
                    # the expected instant manual audit row. Any later edits or
                    # worker activity make this unequal and refuse deletion.
                    require(self.persisted_task_detail(detail) == self.task_details.get(task["id"]), "cleanup_task_has_external_activity")
                self.payload("cleanup_owned_board_delete", "DELETE", "/api/kanban/boards/" + self.board + "?delete=1", {})
                after = self.payload("cleanup_confirm_board_deleted", "GET", "/api/kanban/boards?include_archived=1")
                require(not any(b.get("slug") == self.board for b in after.get("boards", [])), "cleanup_board_still_exists")
                cleanup["synthetic_board_deleted"] = True
                cleanup["active_board_unchanged"] = after.get("current") == self.initial_board
            except Exception as exc:  # noqa: BLE001 - sanitize failure and continue owned cleanup.
                cleanup["board_error"] = str(exc) if isinstance(exc, SmokeFailure) else type(exc).__name__
        try:
            if self.http.cookies:
                self.call("logout_smoke_auth_session", "POST", "/api/auth/logout", {})
                cleanup["smoke_auth_session_logged_out"] = True
        except Exception:  # noqa: BLE001 - never expose auth transport diagnostics.
            cleanup["logout_error"] = "Logout failed"
        self.http.close()
        self.anon.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Perform the bounded mutation smoke; default prepares only")
    parser.add_argument("--base-url", required=True, help="Explicit deployed http://127.0.0.1:PORT")
    parser.add_argument("--webui-repo", type=Path, required=True)
    parser.add_argument("--engine-repo", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True, help="Explicit already-authorized workspace for synthetic session metadata")
    parser.add_argument("--output", type=Path, required=True, help="New private non-secret JSON evidence file")
    parser.add_argument("--expect-webui")
    parser.add_argument("--expect-engine")
    parser.add_argument("--allow-untracked-dir", action="append", default=[], choices=[".playwright-mcp"],
                        help="Explicitly allow only untracked files in this known browser artifact directory; tracked changes always fail")
    args = parser.parse_args()
    parsed = urlsplit(args.base_url)
    try:
        loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        loopback = False
    if not (loopback and parsed.scheme == "http" and parsed.port and not parsed.username
            and not parsed.password and parsed.path in ("", "/") and not parsed.query and not parsed.fragment):
        parser.error("base URL must be a literal loopback HTTP origin with an explicit port")
    args.base_url = args.base_url.rstrip("/")
    for directory in (args.webui_repo, args.engine_repo, args.workspace):
        if not directory.is_absolute() or not directory.is_dir():
            parser.error("repository and workspace directories must exist and be absolute")
    if not args.output.is_absolute() or args.output.exists():
        parser.error("output must be a new absolute filename")
    if not args.output.parent.is_dir():
        parser.error("output parent directory must already exist")
    if not args.execute:
        print("Prepared only. No HTTP requests or mutations performed. Use --execute after candidate deployment.")
        return 0
    smoke = Smoke(args)
    try:
        smoke.run()
    except Exception as exc:  # noqa: BLE001 - sanitize failure and continue owned cleanup.
        smoke.report["api_smoke_passed"] = False
        smoke.report["failure"] = str(exc) if isinstance(exc, SmokeFailure) else type(exc).__name__
    finally:
        smoke.cleanup()
        smoke.report["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            json.dump(smoke.report, output, indent=2)
        print("Non-secret evidence saved:", args.output)
    cleanup_failed = any(key.endswith("_error") for key in smoke.report["cleanup"])
    return 0 if smoke.report.get("api_smoke_passed") and not cleanup_failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
