#!/usr/bin/env python3
"""Paired, host-bound SynPulse deployment. Launch in its own user systemd unit.

Requires exact reviewed commits and idle runtime. Never rewrites governance,
credentials, task ledgers or session history. Reports contain no secret values.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import http.client
import importlib.metadata
import importlib.util
import json
import os
import pwd
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

BASE = Path("/home/synthwavehq")
WEB = BASE / "hermes-webui"
ENGINE = BASE / "work/codex-20260906-pantheon-engine"
WORK = BASE / "work/synthpulse"
OUTPUT = WORK / "qa-release-deployment-v4-20260909.json"
OLD = {
    "webui": "6d67853c5e2b41754e081a93a72d42f0a12a6c0e",
    "engine": "97fbbecd35984d5e28a3482d60a1165121333fc9",
}
RELEASE_REMOTES = {
    "webui": "https://github.com/Synthwave-Solutions/hermes-webui.git",
    "engine": "https://github.com/Synthwave-Solutions/hermes-agent.git",
}
UNIT = "hermes-webui.service"
GATEWAY_UNITS = ("hermes-gateway.service", "hermes-mux-gateway.service")
UNITS = (UNIT, *GATEWAY_UNITS)
GATEWAY_HOMES = {
    GATEWAY_UNITS[0]: BASE / ".hermes",
    GATEWAY_UNITS[1]: BASE / ".hermes-mux",
}
PROC = Path("/proc")
CGROUP = Path("/sys/fs/cgroup")
DEPLOY_UNIT = "synthpulse-release-v4-20260909.service"
REPORT = {"status": "preparing", "events": [], "old_commits": OLD}
HOST_VERIFIED = False
REVIEWED_HELPERS = {}


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def record(phase, **data):
    REPORT.update(
        phase=phase,
        updated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **data,
    )
    REPORT["events"].append({"phase": phase, "at": REPORT["updated_at_utc"]})
    fd, name = tempfile.mkstemp(prefix=".qa-release-", dir=OUTPUT.parent)
    with os.fdopen(fd, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(REPORT, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(name, OUTPUT)


def run(args, cwd=None, timeout=60):
    result = subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )
    require(result.returncode == 0, "command_failed_" + Path(args[0]).name)
    return result.stdout.decode().strip()


def git(path, *args):
    return run(["git", "-C", str(path), *args])


def clean(path, allowed):
    status = git(
        path, "status", "--porcelain=v1", "--untracked-files=normal"
    ).splitlines()
    require(
        all(line in allowed for line in status),
        "unexpected_repository_changes_" + path.name,
    )
    return status


def fetch_reviewed(path, key, branch, revision):
    """Fetch the reviewed fork explicitly; never rewrite the user's upstream origin."""
    remote = RELEASE_REMOTES[key]
    branch_ref = "refs/heads/" + branch
    advertised = git(path, "ls-remote", "--exit-code", remote, branch_ref)
    require(
        advertised.splitlines() == [revision + "\t" + branch_ref],
        "release_branch_changed_" + key,
    )
    run(["git", "-C", str(path), "fetch", "--no-tags", remote, branch_ref], timeout=120)
    require(
        git(path, "rev-parse", "FETCH_HEAD^{commit}") == revision,
        "fetched_release_changed_" + key,
    )
    run(["git", "-C", str(path), "merge-base", "--is-ancestor", OLD[key], revision])


def health():
    connection = http.client.HTTPConnection("127.0.0.1", 8787, timeout=5)
    try:
        connection.request(
            "GET", "/health", headers={"Host": "localhost", "Connection": "close"}
        )
        response = connection.getresponse()
        require(response.status == 200, "health_http_error")
        value = json.loads(response.read(1024 * 1024))
        return {
            key: value.get(key)
            for key in ("status", "active_runs", "active_streams", "server_started_at")
        }
    finally:
        connection.close()


class BusyWork(RuntimeError):
    """Proven live work: wait for natural completion, never force it down."""


def read_json(path):
    with path.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    require(len(raw) <= 1024 * 1024, "runtime_metadata_too_large")
    return json.loads(raw)


def process_start(pid):
    require(type(pid) is int and pid > 1, "invalid_runtime_pid")
    return (PROC / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()[19]


def matching_live_pid(pid, started):
    require(type(pid) is int and pid > 1, "unknown_work_owner")
    try:
        current = process_start(pid)
    except FileNotFoundError:
        return False
    require(started is not None, "unknown_work_owner_instance")
    return str(started) == current


def load_reviewed_helpers(path, expected_hash):
    """Accept only the operator's private, exact process-identity review receipt."""
    require(
        re.fullmatch(r"[0-9a-f]{64}", expected_hash or ""),
        "helper_manifest_hash_required",
    )
    path = Path(path)
    require(
        path.is_absolute() and path.resolve() == path and path.is_relative_to(WORK),
        "helper_manifest_path_untrusted",
    )
    metadata = path.stat()
    require(
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.getuid()
        and stat.S_IMODE(metadata.st_mode) == 0o600
        and metadata.st_size <= 256 * 1024,
        "helper_manifest_not_private",
    )
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected_hash, "helper_manifest_changed")
    value = json.loads(raw)
    require(
        isinstance(value, dict)
        and set(value) == {"version", "helpers"}
        and type(value["version"]) is int
        and value["version"] == 1
        and isinstance(value["helpers"], list)
        and len(value["helpers"]) <= 512,
        "helper_manifest_schema_unknown",
    )
    fields = {
        "unit",
        "pid",
        "start_ticks",
        "parent_pid",
        "parent_start_ticks",
        "exe",
        "cwd",
        "argv_sha256",
    }
    result = {}
    for entry in value["helpers"]:
        require(
            isinstance(entry, dict) and set(entry) == fields,
            "helper_identity_schema_unknown",
        )
        require(
            entry["unit"] in UNITS
            and all(
                type(entry[key]) is int and entry[key] > 1
                for key in ("pid", "parent_pid")
            )
            and all(
                isinstance(entry[key], str) and re.fullmatch(r"[0-9]+", entry[key])
                for key in ("start_ticks", "parent_start_ticks")
            )
            and all(
                isinstance(entry[key], str) and Path(entry[key]).is_absolute()
                for key in ("exe", "cwd")
            )
            and isinstance(entry["argv_sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", entry["argv_sha256"]),
            "helper_identity_invalid",
        )
        key = (entry["unit"], entry["pid"])
        require(key not in result, "duplicate_reviewed_helper")
        result[key] = entry
    return result


def reviewed_helper_matches(unit, pid, control_group):
    expected = REVIEWED_HELPERS.get((unit, pid))
    if expected is None:
        return False
    try:
        proc = PROC / str(pid)
        require(proc.stat().st_uid == os.getuid(), "helper_owner_changed")
        fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        current = {
            "unit": unit,
            "pid": pid,
            "start_ticks": fields[19],
            "parent_pid": int(fields[1]),
            "parent_start_ticks": process_start(int(fields[1])),
            "exe": os.readlink(proc / "exe"),
            "cwd": os.readlink(proc / "cwd"),
            "argv_sha256": hashlib.sha256((proc / "cmdline").read_bytes()).hexdigest(),
        }
        groups = [
            line.split(":", 2)[2] for line in (proc / "cgroup").read_text().splitlines()
        ]
        return current == expected and any(
            group == control_group or group.startswith(control_group + "/")
            for group in groups
        )
    except (OSError, RuntimeError, ValueError, IndexError):
        return False


def unit_state(unit):
    require(unit in (*UNITS, DEPLOY_UNIT), "unexpected_service_unit")
    raw = run(
        [
            "systemctl",
            "--user",
            "show",
            unit,
            "--property=MainPID,ActiveState,SubState,ControlGroup",
        ]
    )
    value = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
    require(
        set(value) == {"MainPID", "ActiveState", "SubState", "ControlGroup"},
        "unknown_service_state",
    )
    value["pid"] = int(value.pop("MainPID"))
    return value


def cgroup_pids(control_group):
    require(
        isinstance(control_group, str)
        and control_group.startswith("/")
        and ".." not in Path(control_group).parts,
        "invalid_service_cgroup",
    )
    root = CGROUP / control_group.lstrip("/")
    require(root.is_dir(), "service_cgroup_missing")
    paths = list(root.rglob("cgroup.procs"))
    require(paths and len(paths) <= 512, "unknown_service_cgroup_processes")
    pids = {
        int(line) for path in paths for line in path.read_text().splitlines() if line
    }
    require(len(pids) <= 4096, "service_cgroup_process_limit")
    return pids


def verify_gateway_engine(pid, helper):
    # Read installation metadata, never import the engine or run its startup.
    argv = [
        part.decode()
        for part in helper.read_bytes(PROC / str(pid) / "cmdline").split(b"\0")
        if part
    ]
    require(argv and Path(argv[0]).is_absolute(), "unknown_gateway_interpreter")
    prefix = Path(argv[0]).parent.parent
    match = re.search(r"python(\d+\.\d+)", os.readlink(PROC / str(pid) / "exe"))
    require(match is not None, "unknown_gateway_python_version")
    sites = [
        prefix / ("lib/python" + match.group(1)) / suffix
        for suffix in ("site-packages", "dist-packages")
    ]
    origins = []
    for distribution in importlib.metadata.distributions(
        path=[str(path) for path in sites]
    ):
        if (distribution.metadata.get("Name") or "").lower().replace(
            "_", "-"
        ) == "hermes-agent":
            origin = json.loads(distribution.read_text("direct_url.json") or "{}")
            origins.append(origin)
    require(
        len(origins) == 1
        and origins[0].get("dir_info", {}).get("editable") is True
        and origins[0].get("url") == ENGINE.as_uri(),
        "gateway_shared_engine_changed",
    )


def runtime_snapshot(helper, *, allow_inactive=False):
    snapshots = {}
    for unit in UNITS:
        item = unit_state(unit)
        if item["pid"] == 0 and item["ActiveState"] in {"inactive", "failed"}:
            require(allow_inactive, "required_service_not_running")
            require(
                not item["ControlGroup"] or item["ControlGroup"].endswith("/" + unit),
                "inactive_runtime_cgroup_mismatch",
            )
            snapshots[unit] = item
            continue
        require(
            item["ActiveState"] == "active"
            and item["SubState"] == "running"
            and item["pid"] > 1,
            "service_not_stably_running",
        )
        proc = PROC / str(item["pid"])
        require(proc.stat().st_uid == os.getuid(), "runtime_process_owner_changed")
        require(
            item["ControlGroup"].endswith("/" + unit)
            and item["pid"] in cgroup_pids(item["ControlGroup"]),
            "runtime_cgroup_mismatch",
        )
        item["start_time"] = process_start(item["pid"])
        env = helper.launch_environment(item["pid"])
        if unit == UNIT:
            require(
                env.get("HERMES_WEBUI_AGENT_DIR") == str(ENGINE)
                and env.get("HERMES_WEBUI_STATE_DIR") == str(BASE / ".hermes/webui"),
                "runtime_paths_changed",
            )
            require(
                helper.listener_pids()["pids_owned_by_expected_user"] == [item["pid"]],
                "service_listener_mismatch",
            )
        else:
            verify_gateway_engine(item["pid"], helper)
            home = Path(env.get("HERMES_HOME") or str(BASE / ".hermes"))
            require(
                home.is_absolute()
                and home.resolve() == GATEWAY_HOMES[unit]
                and home.stat().st_uid == os.getuid(),
                "gateway_home_unverified",
            )
            item["home"] = str(home.resolve())
        snapshots[unit] = item
    live = [item["pid"] for item in snapshots.values() if item["pid"]]
    require(len(live) == len(set(live)), "service_pid_overlap")
    homes = [item["home"] for item in snapshots.values() if item.get("home")]
    require(len(homes) == len(set(homes)), "gateway_home_overlap")
    return snapshots


def gateway_state(record, runtime, *, after=None, expected_code=None, draining=True):
    """Strict persisted gateway contract; unknown values never mean idle."""
    require(isinstance(record, dict), "gateway_status_not_object")
    require(
        type(record.get("pid")) is int
        and record["pid"] == runtime["pid"]
        and str(record.get("start_time")) == runtime["start_time"],
        "gateway_status_wrong_process",
    )
    stamp = datetime.datetime.fromisoformat(record["updated_at"])
    require(stamp.tzinfo is not None, "gateway_status_timestamp_unzoned")
    age = (datetime.datetime.now(datetime.timezone.utc) - stamp).total_seconds()
    require(-5 <= age <= 10, "gateway_status_not_fresh")
    require(after is None or stamp > after, "gateway_status_not_advanced")
    require(
        record.get("gateway_state") == ("draining" if draining else "running"),
        "gateway_drain_not_acknowledged",
    )
    require(
        type(record.get("active_agents")) is int and record["active_agents"] >= 0,
        "unknown_gateway_work_count",
    )
    require(
        expected_code is None or record.get("code_sha") == expected_code,
        "gateway_loaded_revision_mismatch",
    )
    return stamp, record["active_agents"]


def require_idle_children(snapshots):
    for unit, item in snapshots.items():
        group = item["ControlGroup"]
        if not item["pid"]:
            if not group:
                continue
            root = CGROUP / group.lstrip("/")
            try:
                root.stat()
            except FileNotFoundError:
                continue
        expected = {item["pid"]} if item["pid"] else set()
        members = cgroup_pids(group)
        require(expected <= members, "service_main_left_cgroup_during_idle_check")
        children = members - expected
        # An inactive service's surviving children are unfinished work, even if
        # they used to be reviewed helpers of its now-dead main process.
        if children and (
            not item["pid"]
            or not all(reviewed_helper_matches(unit, pid, group) for pid in children)
        ):
            raise BusyWork("service_child_processes_must_finish_or_be_reviewed")


def require_idle_worker_scope(unit):
    """Read the recorded worker scope even when its wrapper PID is already dead."""
    require(
        isinstance(unit, str)
        and re.fullmatch(r"hermes-worker-[A-Za-z0-9_-]{1,128}\.scope", unit),
        "unknown_background_worker_scope",
    )
    raw = run(
        [
            "systemctl",
            "--user",
            "show",
            unit,
            "--property=LoadState,ActiveState,ControlGroup",
        ]
    )
    value = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
    require(
        set(value) == {"LoadState", "ActiveState", "ControlGroup"},
        "unknown_background_worker_scope_state",
    )
    group = value["ControlGroup"]
    if group:
        require(group.endswith("/" + unit), "background_worker_scope_cgroup_mismatch")
        root = CGROUP / group.lstrip("/")
        try:
            root.stat()
        except FileNotFoundError:
            pass
        else:
            if cgroup_pids(group):
                raise BusyWork("background_worker_scope_must_finish")
    require(
        value["LoadState"] in {"loaded", "not-found"},
        "unknown_background_worker_scope_load",
    )
    if value["ActiveState"] not in {"inactive", "failed"}:
        raise BusyWork("background_worker_scope_must_finish")


def require_idle_webui():
    value = health()
    require(
        value["status"] == "ok"
        and all(
            type(value[key]) is int and value[key] >= 0
            for key in ("active_runs", "active_streams")
        ),
        "unknown_webui_work_count",
    )
    if value["active_runs"] or value["active_streams"]:
        raise BusyWork("active_webui_work_must_finish")
    return value


def runtime_homes():
    # Both actual gateway process homes own separate durable work registries.
    roots = [BASE / ".hermes", BASE / ".hermes-mux"]
    homes = [
        home
        for root in roots
        for home in [root, *(root / "profiles").glob("*")]
        if home.is_dir()
    ]
    require(len(homes) <= 400, "runtime_home_scan_limit")
    return homes


def require_idle_background():
    for home in runtime_homes():
        checkpoint = home / "processes.json"
        if checkpoint.is_file():
            entries = read_json(checkpoint)
            require(isinstance(entries, list), "unknown_background_process_schema")
            for entry in entries:
                require(
                    isinstance(entry, dict) and entry.get("pid_scope") == "host",
                    "unknown_background_process_scope",
                )
                if matching_live_pid(entry.get("pid"), entry.get("host_start_time")):
                    raise BusyWork("background_host_process_must_finish")
                scope = entry.get("systemd_unit", "")
                if scope:
                    require_idle_worker_scope(scope)
        cron = home / "cron/executions.db"
        if cron.is_file():
            connection = sqlite3.connect(
                cron.resolve().as_uri() + "?mode=ro", uri=True, timeout=2
            )
            try:
                connection.execute("PRAGMA query_only=ON")
                rows = connection.execute(
                    "SELECT pid,process_started_at FROM executions WHERE status IN ('claimed','running')"
                ).fetchall()
                for pid, started in rows:
                    if matching_live_pid(pid, started):
                        raise BusyWork("cron_execution_must_finish")
            finally:
                connection.close()


class GatewayDrain:
    """Own only newly created native markers; preserve every prior marker."""

    def __init__(self, snapshots):
        self.homes = [Path(snapshots[unit]["home"]) for unit in GATEWAY_UNITS]
        self.owned = {}
        self.principal = "synthpulse-release-" + uuid.uuid4().hex
        self.requested = datetime.datetime.now(datetime.timezone.utc)

    def begin(self):
        require(
            all(
                not (home / ".drain_request.json").exists()
                and not (home / ".drain_request.json").is_symlink()
                for home in self.homes
            ),
            "preexisting_gateway_drain_preserved",
        )
        epoch = (
            (PROC / "sys/kernel/random/boot_id").read_text().strip()
            + ":"
            + (PROC / "1/stat").read_text().rsplit(")", 1)[1].split()[19]
        )
        # PID1 is valid for the native VM epoch even though it cannot own work.
        payload = {
            "action": "drain",
            "requested_at": self.requested.isoformat(),
            "principal": self.principal,
            "epoch": epoch,
            "suppress_notification": True,
        }
        content = json.dumps(payload).encode()
        for home in self.homes:
            path = home / ".drain_request.json"
            descriptor, temporary = tempfile.mkstemp(prefix=".release-drain-", dir=home)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    os.fchmod(stream.fileno(), 0o600)
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                # Atomic no-clobber publication, including a concurrent owner.
                os.link(temporary, path)
                self.owned[path] = content
            finally:
                Path(temporary).unlink(missing_ok=True)

    def verify(self):
        require(len(self.owned) == len(self.homes), "incomplete_owned_gateway_drain")
        require(
            all(path.read_bytes() == content for path, content in self.owned.items()),
            "gateway_drain_owner_changed",
        )

    def clear(self):
        errors = []
        for path, content in list(self.owned.items()):
            try:
                require(path.read_bytes() == content, "gateway_drain_owner_changed")
                path.unlink()
                del self.owned[path]
            except Exception as error:  # noqa: BLE001 - attempt cleanup for every owned marker.
                errors.append(type(error).__name__)
        require(not errors, "owned_gateway_drain_cleanup_failed")


def same_runtime(left, right):
    return all(
        left[unit]["pid"] == right[unit]["pid"]
        and left[unit].get("start_time") == right[unit].get("start_time")
        for unit in UNITS
    )


def wait_drained(helper, snapshots, drain, timeout):
    deadline = time.monotonic() + timeout
    last = {}
    next_report = 0
    while True:
        drain.verify()
        current = runtime_snapshot(helper)
        require(same_runtime(current, snapshots), "service_restarted_during_drain")
        counts, stamps = {}, {}
        acknowledged = True
        for unit in GATEWAY_UNITS:
            try:
                stamps[unit], counts[unit] = gateway_state(
                    read_json(Path(current[unit]["home"]) / "gateway_state.json"),
                    current[unit],
                    after=drain.requested,
                )
            except (RuntimeError, ValueError, KeyError, OSError):
                acknowledged = False
        try:
            require_idle_ledgers(helper)
            require_idle_background()
            value = require_idle_webui()
            if not acknowledged or any(count != 0 for count in counts.values()):
                raise BusyWork("gateway_work_or_admission_not_idle")
            require_idle_children(current)
            idle = True
        except BusyWork as exc:
            REPORT["last_busy_reason"] = str(exc)
            idle = False
            value = None
        if idle and all(
            unit in last and stamps[unit] > last[unit] for unit in GATEWAY_UNITS
        ):
            return value
        last = stamps if idle else {}
        if time.monotonic() >= next_report:
            record(
                "draining_shared_services",
                gateway_counts=counts,
                gateways_acknowledged=acknowledged,
                webui_idle=value is not None,
            )
            next_report = time.monotonic() + 5
        require(
            time.monotonic() < deadline,
            "shared_service_drain_timeout_no_stop_performed",
        )
        time.sleep(1)


def require_stoppable(helper, drain):
    drain.verify()
    snapshots = runtime_snapshot(helper, allow_inactive=True)
    for unit in GATEWAY_UNITS:
        item = snapshots[unit]
        if item["pid"]:
            _, count = gateway_state(
                read_json(Path(item["home"]) / "gateway_state.json"),
                item,
                after=drain.requested,
            )
            if count:
                raise BusyWork("gateway_work_started_before_stop")
    require_idle_ledgers(helper)
    require_idle_background()
    if snapshots[UNIT]["pid"]:
        require_idle_webui()
    require_idle_children(snapshots)
    return snapshots


def stop_units(helper):
    before = [unit_state(unit) for unit in UNITS]
    error = None
    try:
        run(["systemctl", "--user", "stop", *UNITS], timeout=90)
    except Exception as caught:  # noqa: BLE001 - reconcile actual state after any stop failure.
        error = caught
    states = [unit_state(unit) for unit in UNITS]
    stopped = all(
        item["pid"] == 0 and item["ActiveState"] in {"inactive", "failed"}
        for item in states
    )
    stopped = stopped and not helper.listener_pids()["pids_owned_by_expected_user"]
    for item in before:
        group = item["ControlGroup"]
        if group and (CGROUP / group.lstrip("/")).is_dir():
            stopped = stopped and not cgroup_pids(group)
    if not stopped and error:
        raise error
    require(stopped, "shared_service_survived_stop")


def wait_services_healthy(helper, excluded, expected_engine, drain, *, released=False):
    deadline = time.monotonic() + 120
    while True:
        try:
            current = runtime_snapshot(helper)
            require(
                all(current[unit]["pid"] != excluded[unit]["pid"] for unit in UNITS),
                "old_service_process_survived",
            )
            for unit in GATEWAY_UNITS:
                gateway_state(
                    read_json(Path(current[unit]["home"]) / "gateway_state.json"),
                    current[unit],
                    after=drain.requested,
                    expected_code=expected_engine,
                    draining=not released,
                )
            value = health()
            require(value["status"] == "ok", "webui_not_healthy")
            return value, current
        except (RuntimeError, ValueError, KeyError, OSError):
            require(time.monotonic() < deadline, "shared_service_health_timeout")
            time.sleep(2)


def switch_pair(helper, new, snapshots, policy, policy_hash, drain):
    stop_attempted = False
    try:
        require_stoppable(helper, drain)
        stop_attempted = True
        REPORT["stop_attempted"] = True
        stop_units(helper)
        record("all_shared_services_stopped")
        for key, path in [("engine", ENGINE), ("webui", WEB)]:
            require(
                git(path, "rev-parse", "HEAD") == OLD[key],
                "source_changed_during_stop_" + key,
            )
            clean(path, {"?? .playwright-mcp/"} if key == "engine" else set())
            git(path, "merge", "--ff-only", new[key])
            require(
                git(path, "rev-parse", "HEAD") == new[key],
                "checkout_revision_mismatch_" + key,
            )
        record("paired_sources_updated")
        run(["systemctl", "--user", "start", *UNITS], timeout=90)
        value, current = wait_services_healthy(helper, snapshots, new["engine"], drain)
        require(
            hashlib.sha256(policy.read_bytes()).hexdigest() == policy_hash,
            "policy_changed_during_deploy",
        )
        record(
            "all_shared_services_healthy",
            status="deployed_pending_live_smoke",
            new_services=current,
            health_after=value,
            governance_policy_preserved=True,
        )
        return new["engine"]
    except Exception as error:
        best_effort_record(
            "deployment_failed", status="failed", failure_type=type(error).__name__
        )
        if stop_attempted:
            # If new work exists or its ownership is unknown, leave the current
            # coherent candidate alive for review; never kill it to roll back.
            require_stoppable(helper, drain)
            stop_units(helper)
            require(
                hashlib.sha256(policy.read_bytes()).hexdigest() == policy_hash,
                "rollback_requires_policy_review",
            )
            for key, path in [("engine", ENGINE), ("webui", WEB)]:
                clean(path, {"?? .playwright-mcp/"} if key == "engine" else set())
                require(
                    git(path, "rev-parse", "HEAD") in {OLD[key], new[key]},
                    "rollback_source_changed_" + key,
                )
                git(path, "checkout", "--detach", OLD[key])
            run(["systemctl", "--user", "start", *UNITS], timeout=90)
            restored, current = wait_services_healthy(
                helper, snapshots, OLD["engine"], drain
            )
            require(
                all(
                    git(path, "rev-parse", "HEAD") == OLD[key]
                    for key, path in [("webui", WEB), ("engine", ENGINE)]
                ),
                "rollback_revision_not_restored",
            )
            record(
                "all_shared_services_rolled_back",
                status="rolled_back",
                rollback_health=restored,
                rollback_services=current,
                rollback_checkout_state="detached at recorded old commits",
            )
        raise


def best_effort_record(*args, **kwargs):
    try:
        record(*args, **kwargs)
    except Exception:  # noqa: BLE001,S110 - report IO must never prevent rollback.
        pass


def require_idle_ledgers(helper):
    for home in runtime_homes():
        info = helper.ledger(home)
        require(info.get("status") != "unknown", "unreadable_ledger")
        if not info.get("exists"):
            continue
        require(
            info.get("table_present")
            and type(info.get("unfinished_owner_pids_existing")) is int
            and info["unfinished_owner_pids_existing"] >= 0,
            "unknown_ledger_schema",
        )
        connection = sqlite3.connect(
            (home / "state.db").resolve().as_uri() + "?mode=ro", uri=True, timeout=2
        )
        try:
            connection.execute("PRAGMA query_only=ON")
            # A finished child with undelivered output still belongs to its live owner.
            owners = connection.execute(
                "SELECT DISTINCT owner_pid,owner_started_at FROM async_delegations WHERE "
                "state IN ('running','stalling','finalizing') OR delivery_state='pending'"
            ).fetchall()
            for owner_pid, started in owners:
                if matching_live_pid(owner_pid, started):
                    raise BusyWork("live_delegated_work_or_delivery_must_finish")
        finally:
            connection.close()


def wait_aborted_drains_released(helper, snapshots, homes, cleared_after):
    """Prove a pre-stop abort restored only our admission gates, still live."""
    deadline = time.monotonic() + 30
    while True:
        try:
            current = runtime_snapshot(helper)
            require(
                same_runtime(current, snapshots), "service_changed_during_drain_abort"
            )
            for unit in GATEWAY_UNITS:
                if Path(current[unit]["home"]) in homes:
                    gateway_state(
                        read_json(Path(current[unit]["home"]) / "gateway_state.json"),
                        current[unit],
                        after=cleared_after,
                        draining=False,
                    )
            require(health()["status"] == "ok", "webui_unhealthy_after_drain_abort")
            require(
                all(
                    git(path, "rev-parse", "HEAD") == OLD[key]
                    for key, path in [("webui", WEB), ("engine", ENGINE)]
                ),
                "source_changed_during_drain_abort",
            )
            return current
        except (RuntimeError, ValueError, KeyError, OSError):
            require(time.monotonic() < deadline, "drain_abort_resume_not_proven")
            time.sleep(1)


def deploy_with_drain(helper, new, snapshots, policy, policy_hash, drain_timeout):
    drain = GatewayDrain(snapshots)
    released_engine = None
    try:
        drain.begin()
        record("native_gateway_drains_requested", notification_suppressed=True)
        value = wait_drained(helper, snapshots, drain, drain_timeout)
        record("ready_to_switch_all_shared_services", health_before=value)
        released_engine = switch_pair(
            helper, new, snapshots, policy, policy_hash, drain
        )
    finally:
        owned_homes = {path.parent for path in drain.owned}
        cleared_after = datetime.datetime.now(datetime.timezone.utc)
        drain.clear()
        if REPORT.get("status") == "rolled_back":
            released_engine = OLD["engine"]
        if released_engine:
            value, current = wait_services_healthy(
                helper, snapshots, released_engine, drain, released=True
            )
            record(
                "owned_gateway_drains_released",
                gateway_drains_released=True,
                services_after_release=current,
            )
        else:
            if owned_homes and not REPORT.get("stop_attempted"):
                current = wait_aborted_drains_released(
                    helper, snapshots, owned_homes, cleared_after
                )
                best_effort_record(
                    "prestop_abort_services_preserved",
                    services_after_abort=current,
                    original_services_alive=True,
                    original_sources_unchanged=True,
                )
            best_effort_record(
                "owned_gateway_drains_removed_after_abort",
                owned_gateway_drains_released=True,
            )


def main():
    global HOST_VERIFIED, REVIEWED_HELPERS
    import socket

    require(
        socket.gethostname() == "synthwave-vps"
        and pwd.getpwuid(os.geteuid()).pw_name == "synthwavehq"
        and os.getuid() == os.geteuid() == 1000,
        "unexpected_host_or_user",
    )
    require(
        WORK.resolve() == WORK and WORK.stat().st_uid == os.getuid(),
        "unexpected_output_owner",
    )
    require(not OUTPUT.is_symlink(), "unexpected_output_symlink")
    HOST_VERIFIED = True
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    p = argparse.ArgumentParser()
    p.add_argument("--webui", required=True)
    p.add_argument("--engine", required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--drain-timeout", type=int, default=600)
    p.add_argument("--reviewed-helper-manifest")
    p.add_argument("--helper-manifest-sha256")
    args = p.parse_args()
    require(
        args.execute
        and all(re.fullmatch("[0-9a-f]{40}", x) for x in (args.webui, args.engine)),
        "explicit_exact_commits_required",
    )
    require(10 <= args.drain_timeout <= 1800, "drain_timeout_out_of_bounds")
    require(
        bool(args.reviewed_helper_manifest) == bool(args.helper_manifest_sha256),
        "helper_manifest_and_hash_required_together",
    )
    if args.reviewed_helper_manifest:
        REVIEWED_HELPERS = load_reviewed_helpers(
            args.reviewed_helper_manifest, args.helper_manifest_sha256
        )
        REPORT["reviewed_helper_manifest_sha256"] = args.helper_manifest_sha256
        REPORT["reviewed_helper_count"] = len(REVIEWED_HELPERS)
    new = {"webui": args.webui, "engine": args.engine}
    REPORT["new_commits"] = new
    require(
        git(WEB, "rev-parse", "HEAD") == OLD["webui"]
        and git(ENGINE, "rev-parse", "HEAD") == OLD["engine"],
        "production_base_changed",
    )
    before = {
        "webui": clean(WEB, set()),
        "engine": clean(ENGINE, {"?? .playwright-mcp/"}),
    }
    REPORT["preexisting_untracked"] = before
    require(shutil.disk_usage(WORK).free > 1024**3, "insufficient_disk")
    record("fetching_reviewed_commits")
    for key, path, branch in [("webui", WEB, "master"), ("engine", ENGINE, "main")]:
        fetch_reviewed(path, key, branch, new[key])
    python = ENGINE / ".venv/bin/python"
    # Metadata-only check; deployed environment already contains these exact compatible releases.
    versions = json.loads(
        run(
            [
                str(python),
                "-B",
                "-I",
                "-c",
                'import importlib.metadata as m,json;print(json.dumps({n:m.version(n) for n in ["Pillow","requests","websockets","PyYAML","cryptography","openai"]}))',
            ]
        )
    )
    require(
        versions["Pillow"].startswith("12.")
        and versions["requests"].startswith("2.")
        and versions["websockets"].startswith("15."),
        "runtime_dependency_family_changed",
    )
    REPORT["dependency_versions"] = versions
    helper_path = WORK / "qa-release-preflight-20260908.py"
    spec = importlib.util.spec_from_file_location("release_readonly", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    snapshots = runtime_snapshot(helper)
    REPORT["old_services"] = snapshots
    # This per-user rollout must remain in the existing enforcement mode and preserve recovery owners.
    policy = BASE / ".hermes/dashboard-governance.yaml"
    policy_hash = hashlib.sha256(policy.read_bytes()).hexdigest()
    backup = (
        BASE
        / ".local/state/synthpulse-releases"
        / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    shutil.copy2(policy, backup / "dashboard-governance.yaml")
    (backup / "dashboard-governance.yaml").chmod(0o600)
    (backup / "release.json").write_text(
        json.dumps(
            {
                "old": OLD,
                "new": new,
                "policy_sha256": policy_hash,
                "dependencies": versions,
            }
        )
    )
    (backup / "release.json").chmod(0o600)
    REPORT["backup_directory"] = str(backup)
    cgroup = Path("/proc/self/cgroup").read_text()
    require(
        DEPLOY_UNIT in cgroup
        and all(unit not in cgroup for unit in UNITS)
        and run(
            [
                "systemctl",
                "--user",
                "show",
                DEPLOY_UNIT,
                "--property=MainPID",
                "--value",
            ]
        )
        == str(os.getpid()),
        "deployment_must_have_verified_independent_unit",
    )
    REPORT["deployment_unit"] = DEPLOY_UNIT
    deploy_with_drain(helper, new, snapshots, policy, policy_hash, args.drain_timeout)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001 - sanitized terminal failure receipt.
        if HOST_VERIFIED:
            best_effort_record(
                "stopped_with_error",
                status=REPORT.get("status", "failed"),
                error_type=type(error).__name__,
                error_code=str(error)[:120],
            )
        raise SystemExit(1) from None
