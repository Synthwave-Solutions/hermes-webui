#!/usr/bin/env python3
"""Read-only VPS release inspection; writes only the fixed private report.

Run as synthwavehq on synthwave-vps. No application modules are imported, no
service is restarted, no provider is contacted, and no credentials are emitted.
Missing/inaccessible evidence is unknown rather than zero. Linux /proc environ
is launch-environment evidence, not a guarantee of later in-process mutation.
"""
from __future__ import annotations

import collections
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import shutil
import socket
import sqlite3
import ssl
import subprocess
import tempfile

EXPECTED_HOST = "synthwave-vps"
EXPECTED_USER = "synthwavehq"
OUTPUT = Path("/home/synthwavehq/work/synthpulse/qa-release-preflight-20260908.json")
PORT = 8787
MAX_FILE = 8 * 1024 * 1024
MAX_PROFILES = 200
PATH_KEYS = (
    "HOME", "HERMES_HOME", "HERMES_BASE_HOME", "HERMES_CONFIG_PATH",
    "HERMES_WEBUI_STATE_DIR", "HERMES_WEBUI_AGENT_DIR", "HERMES_WEBUI_PYTHON",
    "HERMES_WEBUI_GOVERNANCE_POLICY", "HERMES_WEBUI_DEFAULT_WORKSPACE",
    "HERMES_WEBUI_ATTACHMENT_DIR", "HERMES_WEBUI_TLS_CERT", "HERMES_WEBUI_TLS_KEY",
    "VIRTUAL_ENV",
)
SAFE_FLAGS = {"--foreground", "--no-browser", "--no-open", "-u", "-m"}
SCRIPT_NAMES = {"server.py", "bootstrap.py", "start.sh", "run.py", "hermes", "python", "python3"}
ERRORS: list[dict] = []


def issue(section, exc):
    # Exception messages may quote configuration or command arguments.
    ERRORS.append({"section": section, "error_type": type(exc).__name__})


def clean(value, limit=500):
    return "".join(c for c in str(value) if c.isprintable())[:limit]


def read_bytes(path, limit=MAX_FILE):
    with Path(path).open("rb") as stream:
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError("bounded read exceeded")
    return value


def command(args, *, cwd=None, timeout=10):
    env = {"HOME": pwd.getpwuid(os.getuid()).pw_dir, "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
           "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
        if key in os.environ:
            env[key] = os.environ[key]  # Used only for existing user-systemd; never emitted.
    result = subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError("read command failed")
    if len(result.stdout) > MAX_FILE:
        raise ValueError("bounded command output exceeded")
    return result.stdout.decode("utf-8", errors="replace")


def launch_environment(pid):
    return dict(part.decode("utf-8", errors="replace").split("=", 1)
                for part in read_bytes(Path("/proc") / str(pid) / "environ").split(b"\0") if b"=" in part)


def safe_argv(argv):
    # Never include arbitrary arguments, option values, URLs, inline Python or shell code.
    return {"executable": clean(argv[0]) if argv else None,
            "script_paths": [clean(a) for a in argv[1:] if Path(a).name in SCRIPT_NAMES and "\n" not in a][:5],
            "flags": [a for a in argv[1:] if a in SAFE_FLAGS],
            "omitted_argument_count": sum(a not in SAFE_FLAGS and Path(a).name not in SCRIPT_NAMES for a in argv[1:])}


def listener_pids():
    inodes = set()
    addresses = []
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            for line in Path(table).read_text().splitlines()[1:]:
                parts = line.split()
                if int(parts[1].rsplit(":", 1)[1], 16) == PORT and parts[3] == "0A":
                    inodes.add(parts[9]); addresses.append(parts[1])
        except Exception as exc:
            issue("listener_table", exc)
    found = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            for fd in (proc / "fd").iterdir():
                try:
                    if os.readlink(fd) in {"socket:[" + inode + "]" for inode in inodes}:
                        found.append(int(proc.name)); break
                except (FileNotFoundError, PermissionError):
                    pass
        except (FileNotFoundError, PermissionError):
            continue
    return {"port": PORT, "listener_addresses_hex": addresses, "pids_owned_by_expected_user": sorted(set(found)),
            "complete_for_other_users": False}


def process(pid):
    base = Path("/proc") / str(pid)
    argv = [part.decode("utf-8", errors="replace") for part in read_bytes(base / "cmdline").split(b"\0") if part]
    env = launch_environment(pid)
    cwd = Path(os.readlink(base / "cwd"))
    exe = os.readlink(base / "exe")
    data = {"pid": pid, "owner": pwd.getpwuid(base.stat().st_uid).pw_name,
            "cwd": str(cwd), "exe": exe, "cmdline": safe_argv(argv),
            "launch_environment_paths": {key: clean(env[key]) for key in PATH_KEYS if env.get(key)},
            "launch_environment_flags": {key: clean(env[key], 30) for key in (
                "HERMES_WEBUI_HOST", "HERMES_WEBUI_PORT", "SYNPULSE_REALTIME_VOICE_ENABLED",
                "HERMES_WEBUI_ISOLATED_PROFILE", "HERMES_WEBUI_AUTO_INSTALL") if key in env},
            "openai_key_present_in_launch_environment": bool(env.get("OPENAI_API_KEY", "").strip())}
    units = sorted(set(re.findall(r"(?:^|/)([^/\n]+\.service)(?:/|$)", (base / "cgroup").read_text(), re.M)))
    data["cgroup_service_units"] = [clean(unit) for unit in units]
    data["open_state_db_paths"] = []
    for fd in list((base / "fd").iterdir())[:4096]:
        try:
            target = os.readlink(fd)
            if target.endswith("/state.db") and target not in data["open_state_db_paths"]:
                data["open_state_db_paths"].append(target)
        except OSError:
            pass
    return data, argv, env, cwd, units


def service(unit):
    for user in (True, False):
        try:
            raw = command(["systemctl", *(["--user"] if user else []), "show", unit,
                           "--property=Id,ActiveState,SubState,MainPID,WorkingDirectory,FragmentPath,ExecStart"], timeout=8)
            values = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
            if values.get("MainPID") in (None, "0") and not values.get("FragmentPath"):
                continue
            start = values.pop("ExecStart", "")
            executable = re.search(r"(?:^|[ {;])path=([^ ;}]+)", start)
            start_args = re.search(r"argv\[\]=(.*?)(?:\s*;|\s*})", start)
            values["ExecStart_executable_only"] = clean(executable.group(1)) if executable else None
            values["ExecStart_arguments"] = "omitted; see listener process safe cmdline"
            data = {"scope": "user" if user else "system", **{k: clean(v) for k, v in values.items()}}
            if start_args:
                try: data["ExecStart_safe_argv"] = safe_argv(shlex.split(start_args.group(1)))
                except ValueError: pass
            return data
        except Exception as exc:
            issue("service_" + ("user" if user else "system"), exc)
    return {"unit": clean(unit), "status": "unknown"}


def repo_state(directory):
    try:
        directory = Path(command(["git", "rev-parse", "--show-toplevel"], cwd=directory).strip())
        sha = command(["git", "rev-parse", "HEAD"], cwd=directory).strip()
        status_items = command(["git", "status", "--porcelain=v1", "-z", "--untracked-files=normal"], cwd=directory).split("\0")
        status_items = [clean(item, 300) for item in status_items if item]
        return {"path": str(directory), "head": sha, "status_entries": status_items[:150],
                "status_entry_count": len(status_items), "status_truncated": len(status_items) > 150}
    except Exception as exc:
        issue("repo", exc)
        return {"path": str(directory), "status": "unknown"}


def health(env):
    connection = None
    try:
        cert = env.get("HERMES_WEBUI_TLS_CERT")
        native_tls = bool(cert and env.get("HERMES_WEBUI_TLS_KEY"))
        if native_tls:
            # Trust and pin the configured listener certificate; never verify=False.
            pem = read_bytes(Path(cert)).decode()
            der = ssl.PEM_cert_to_DER_cert(re.search(r"-----BEGIN CERTIFICATE-----[\s\S]+?-----END CERTIFICATE-----", pem).group(0))
            expected = hashlib.sha256(der).digest()
            context = ssl.create_default_context(cafile=cert)
            context.check_hostname = False  # Exact leaf pin binds the fixed loopback target.
            connection = http.client.HTTPSConnection("127.0.0.1", PORT, context=context, timeout=5)
            connection.connect()
            if hashlib.sha256(connection.sock.getpeercert(binary_form=True)).digest() != expected:
                raise ValueError("listener certificate pin mismatch")
        else:
            connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
        connection.request("GET", "/health", headers={"Host": "localhost", "Connection": "close"})
        response = connection.getresponse()
        payload = json.loads(response.read(1024 * 1024))
        allowed = ("status", "sessions", "active_streams", "active_runs", "last_run_finished_at",
                   "server_started_at", "uptime_seconds", "oldest_run_age_seconds", "idle_seconds_since_last_run")
        return {"http_status": response.status, "transport": "https-pinned" if native_tls else "http",
                **{key: payload[key] for key in allowed if isinstance(payload.get(key), (str, int, float, bool))},
                "run_private_details_omitted": True}
    except Exception as exc:
        issue("health", exc)
        return {"status": "unknown"}
    finally:
        if connection:
            connection.close()


def dotenv_presence(path):
    result = {"path": str(path), "exists": path.is_file()}
    if not result["exists"]:
        return result
    try:
        keys = {}
        for line in read_bytes(path).decode("utf-8", errors="replace").splitlines():
            match = re.match(r"\s*(?:export\s+)?(OPENAI_API_KEY|SYNPULSE_REALTIME_VOICE_ENABLED)\s*=\s*(.*)$", line)
            if match:
                words = shlex.split(match[2], comments=True, posix=True)
                value = words[0] if words else ""
                keys[match[1]] = bool(value)
                if match[1] == "SYNPULSE_REALTIME_VOICE_ENABLED":
                    result["voice_enabled_literal"] = value.lower() in {"1", "true", "yes", "on"}
        result["openai_key_assignment_present_nonempty"] = keys.get("OPENAI_API_KEY", False)
        result["interpretation"] = "assignment presence only; no shell expansion and no credentials printed"
    except Exception as exc:
        issue("dotenv_presence", exc); result["status"] = "unknown"
    return result


INSPECTOR = r'''
import importlib.metadata as meta,json,pathlib,sys
request=json.loads(sys.stdin.read())
out={'python':{'executable':sys.executable,'version':sys.version.split()[0],'prefix':sys.prefix,'base_prefix':sys.base_prefix},'dependencies':{}}
for name in ['PyYAML','cryptography','Pillow','requests','websockets','openai','hermes-agent']:
 try: out['dependencies'][name]=meta.version(name)
 except meta.PackageNotFoundError: out['dependencies'][name]=None
try:
 import yaml
except Exception as e:
 out['yaml_inspection_error_type']=type(e).__name__;print(json.dumps(out));raise SystemExit
def read(p):
 p=pathlib.Path(p)
 if not p.is_file():return {'_missing':True}
 if p.stat().st_size>8*1024*1024:raise ValueError('bounded YAML')
 value=yaml.safe_load(p.read_text())
 if not isinstance(value,dict):raise ValueError('object required')
 return value
def label(value):
 # Provider/model only; reject URL-like values or inline credentials.
 if not isinstance(value,str):return None
 if len(value)>160 or '://' in value or '@' in value or any(c.isspace() for c in value):return '[invalid-or-omitted]'
 return value
try:
 policy=read(request['policy'])
 roles=policy.get('roles',{});users=policy.get('users',{})
 out['policy']={'path':request['policy'],'exists':not policy.get('_missing',False),'mode':label(policy.get('mode')),
 'default_effect':label(policy.get('default_effect')),'bootstrap_owner_count':len(policy.get('bootstrap_admins',[])) if isinstance(policy.get('bootstrap_admins',[]),list) else None,
 'role_count':len(roles) if isinstance(roles,dict) else None,'role_names':[label(k) for k in list(roles)[:100]] if isinstance(roles,dict) else None,
 'user_count':len(users) if isinstance(users,dict) else None,'group_count':len(policy.get('groups',{})) if isinstance(policy.get('groups',{}),dict) else None,
 'explicit_managed_users':sum(isinstance(v,dict) and any(k in v for k in ('access_mode','access_level','approval')) for v in users.values()) if isinstance(users,dict) else None}
except Exception as e:out['policy']={'path':request['policy'],'status':'unknown','error_type':type(e).__name__}
out['configured_auxiliary_routes']=[]
for config in request['configs']:
 item={'config_path':config}
 try:
  cfg=read(config);aux=cfg.get('auxiliary',{});route=aux.get('approval_advice',{}) if isinstance(aux,dict) else {}
  item.update(exists=not cfg.get('_missing',False),approval_advice={'provider':label(route.get('provider')),'model':label(route.get('model'))} if isinstance(route,dict) else {'status':'invalid'},interpretation='configured fields only; missing/auto does not resolve a provider or prove a real decision call')
 except Exception as e:item.update(status='unknown',error_type=type(e).__name__)
 out['configured_auxiliary_routes'].append(item)
print(json.dumps(out))
'''


def interpreter_inspection(executable, policy, configs):
    try:
        env = {"HOME": pwd.getpwuid(os.getuid()).pw_dir, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
        result = subprocess.run([executable, "-B", "-I", "-c", INSPECTOR],
            input=json.dumps({"policy": str(policy), "configs": [str(p) for p in configs]}).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, timeout=15)
        if result.returncode or len(result.stdout) > 256 * 1024:
            raise RuntimeError("interpreter inspection failed")
        return json.loads(result.stdout)
    except Exception as exc:
        issue("interpreter", exc); return {"status": "unknown", "selected_executable": executable}


def ledger(home):
    path = home / "state.db"
    output = {"home": str(home), "path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return output
    connection = None
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        connection.execute("PRAGMA query_only=ON")
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='async_delegations'").fetchone():
            output.update(table_present=False, pending="unknown: older engine has no durable ledger"); return output
        columns = {row[1] for row in connection.execute("PRAGMA table_info(async_delegations)")}
        output["table_present"] = True
        if not {"state", "delivery_state"} <= columns:
            output["pending"] = "unknown: incomplete schema"; return output
        # No IDs, goals, results, principal, messages or task JSON are emitted.
        output["state_delivery_counts"] = [{"state": clean(state, 40), "delivery_state": clean(delivery, 40), "count": count}
            for state, delivery, count in connection.execute("SELECT state,delivery_state,COUNT(*) FROM async_delegations GROUP BY state,delivery_state")]
        where = "state IN ('running','stalling','finalizing') OR delivery_state IN ('pending','dropped')"
        output["unfinished_or_undelivered_count"] = connection.execute("SELECT COUNT(*) FROM async_delegations WHERE " + where).fetchone()[0]
        if "owner_pid" in columns:
            pids = [row[0] for row in connection.execute("SELECT DISTINCT owner_pid FROM async_delegations WHERE state IN ('running','stalling','finalizing')") if row[0]]
            output["unfinished_owner_pids_existing"] = sum(Path('/proc', str(pid)).exists() for pid in pids)
        if "task_json" in columns:
            # SQLite JSON checks derive a boolean; never pull private JSON into report.
            try:
                output["unfinished_missing_webui_authority_ref"] = connection.execute(
                    "SELECT COUNT(*) FROM async_delegations WHERE (" + where + ") AND "
                    "(NOT json_valid(COALESCE(task_json,'')) OR COALESCE(json_extract(CASE WHEN json_valid(task_json) THEN task_json ELSE '{}' END,'$.webui_continuation_ref'),'')='')").fetchone()[0]
            except sqlite3.Error:
                output["unfinished_missing_webui_authority_ref"] = None
    except Exception as exc:
        issue("ledger", exc); output["status"] = "unknown"
    finally:
        if connection:
            connection.close()
    return output


def cron_summary(home):
    path = home / "cron/jobs.json"
    output = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return output
    try:
        raw = json.loads(read_bytes(path)); jobs = raw.get("jobs", []) if isinstance(raw, dict) else raw
        if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
            raise ValueError("jobs shape")
        output.update(count=len(jobs), enabled_count=sum(job.get("enabled", True) is True for job in jobs),
                      states=dict(collections.Counter(clean(job.get("state", "unspecified"), 40) for job in jobs)),
                      certainty="durable job state only; in-memory recurring execution may not be represented")
    except Exception as exc:
        issue("cron", exc); output["status"] = "unknown"
    return output


def main():
    host = socket.gethostname().split(".", 1)[0]
    account = pwd.getpwuid(os.geteuid())
    # These checks precede every possible report or temporary-file write.
    if host != EXPECTED_HOST or account.pw_name != EXPECTED_USER or os.getuid() != os.geteuid():
        raise SystemExit("Refused: expected synthwave-vps as synthwavehq")
    parent = OUTPUT.parent
    if parent.resolve() != parent or parent.stat().st_uid != os.geteuid() or not parent.is_dir():
        raise SystemExit("Refused: unexpected output directory ownership/path")
    if OUTPUT.exists() and (OUTPUT.is_symlink() or OUTPUT.stat().st_uid != os.geteuid()):
        raise SystemExit("Refused: unexpected output file ownership/path")
    report = {"observed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "assertions": {"hostname": host, "user": account.pw_name, "uid": os.getuid()},
        "read_only_scope": "Only fixed output JSON is written; loopback GET /health, systemctl show, git metadata, /proc, bounded config and SQLite mode=ro inspection. No source/application imports, provider calls or service changes."}
    listeners = listener_pids(); report["listener"] = listeners
    report["services"] = []; report["processes"] = []
    usage = shutil.disk_usage(parent)
    report["output_filesystem_disk_bytes"] = {"total": usage.total, "used": usage.used, "free": usage.free}
    for pid in listeners["pids_owned_by_expected_user"][:8]:
        try:
            data, argv, env, cwd, units = process(pid)
            report["processes"].append(data)
            report["services"].extend(service(unit) for unit in units)
            homes = Path(env.get("HERMES_HOME") or str(Path(account.pw_dir) / ".hermes")).expanduser()
            base = Path(env.get("HERMES_BASE_HOME") or homes).expanduser()
            if base.parent.name == "profiles": base = base.parent.parent
            state_dir = Path(env.get("HERMES_WEBUI_STATE_DIR") or str(homes / "webui")).expanduser()
            policy = Path(env.get("HERMES_WEBUI_GOVERNANCE_POLICY") or str(homes / "dashboard-governance.yaml")).expanduser()
            webui = cwd
            for item in argv[1:]:
                if Path(item).name == "server.py":
                    webui = (cwd / item).resolve().parent; break
            candidates = [Path(env["HERMES_WEBUI_AGENT_DIR"])] if env.get("HERMES_WEBUI_AGENT_DIR") else []
            candidates += [homes / "hermes-agent", webui.parent / "hermes-agent", webui.parent,
                           Path(account.pw_dir) / ".hermes/hermes-agent", Path(account.pw_dir) / "hermes-agent",
                           Path(account.pw_dir) / ".local/share/hermes-agent", Path("/opt/hermes-agent")]
            agent = next((p.expanduser().resolve() for p in candidates if (p.expanduser() / "run_agent.py").is_file()), None)
            data["repository_candidates"] = {"webui": repo_state(webui), "engine": repo_state(agent) if agent else {"status": "unknown"},
                "engine_path_certainty": "launch override or static source-discovery inference; verify actual import origin before upgrade"}
            profile_homes = [homes, base]
            if (base / "profiles").is_dir():
                discovered = sorted(p for p in (base / "profiles").iterdir() if p.is_dir())
                profile_homes += discovered[:MAX_PROFILES]
                data["profile_scan_truncated"] = len(discovered) > MAX_PROFILES
            profile_homes += [Path(path).parent for path in data["open_state_db_paths"]]
            profile_homes = list(dict.fromkeys(p.resolve() for p in profile_homes))
            configs = [Path(env["HERMES_CONFIG_PATH"]).expanduser()] if env.get("HERMES_CONFIG_PATH") else []
            configs += [p / "config.yaml" for p in profile_homes if (p / "config.yaml").is_file()]
            executable = argv[0] if argv and Path(argv[0]).is_absolute() and Path(argv[0]).is_file() else data["exe"]
            data["inspection"] = interpreter_inspection(executable, policy, list(dict.fromkeys(configs)))
            data["resolved_launch_paths"] = {"hermes_home": str(homes), "base_home": str(base), "webui_state": str(state_dir), "policy": str(policy),
                "certainty": "launch environment and current source conventions; not cached runtime globals"}
            data["voice"] = {"enabled_in_launch_environment": env.get("SYNPULSE_REALTIME_VOICE_ENABLED", "").lower() in {"1","true","yes","on"},
                "openai_key_present_in_launch_environment": bool(env.get("OPENAI_API_KEY", "").strip()),
                "existing_hermes_dotenv": [dotenv_presence(p / ".env") for p in profile_homes if p in {homes.resolve(), base.resolve()}],
                "real_provider_or_audio_check": "not performed"}
            data["health"] = health(env)
            data["async_ledgers"] = [ledger(p) for p in profile_homes]
            data["cron_stores"] = [cron_summary(p) for p in profile_homes]
            authorities = state_dir / "continuation-authority"
            data["continuation_authority"] = {"path": str(authorities), "exists": authorities.is_dir(),
                "record_count": sum(1 for p in authorities.glob("*.json") if p.is_file()) if authorities.is_dir() else None}
            usage = shutil.disk_usage(state_dir if state_dir.exists() else parent)
            data["disk_bytes"] = {"total": usage.total, "used": usage.used, "free": usage.free}
        except Exception as exc:
            issue("process_" + str(pid), exc)
    report["errors"] = ERRORS
    report["restart_readiness"] = "Not certified. Combine health counts with every durable ledger, recurring jobs, separate gateway services and current terminal activity; missing/unknown evidence is not idle. Repeat immediately before restart."
    report["elapsed_snapshot_note"] = "A point-in-time snapshot; work can start or finish during inspection. Credential values, transcripts, task IDs/goals/results, URLs with credentials and arbitrary command arguments are excluded."
    payload = json.dumps(report, indent=2, ensure_ascii=False).encode() + b"\n"
    fd, temporary = tempfile.mkstemp(prefix=".qa-release-preflight-", suffix=".tmp", dir=parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, OUTPUT)
        directory_fd = os.open(parent, os.O_DIRECTORY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


if __name__ == "__main__":
    main()
