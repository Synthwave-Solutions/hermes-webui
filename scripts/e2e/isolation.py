"""Disposable credentials and loopback-only networking for QA processes.

This is test tooling, not an application authorization boundary or OS sandbox.
The audit hook also runs in Python children through the adjacent sitecustomize.
"""
from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import shutil
import sys

_INSTALLED = False
_CREDENTIAL_CLIS = {"gh", "security", "op", "aws", "az", "gcloud", "claude", "codex"}


def fixture_environment(state: Path) -> dict[str, str]:
    state = state.resolve()
    if state.name != "e2e-state":
        raise ValueError("QA isolation requires a private e2e-state directory")
    fixture_home = state / "os-home"
    bin_dir = state / "bin"
    for directory in (fixture_home, bin_dir, fixture_home / ".config", state / "tmp"):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    # The actual application may run git, sh and standard system utilities.
    # Keep credential-bearing developer CLIs out of automatic discovery.
    for name in ("python", "python3", "node"):
        target = sys.executable if name.startswith("python") else shutil.which(name)
        if target and not (bin_dir / name).exists():
            (bin_dir / name).symlink_to(Path(target).resolve())
    return {
        "HOME": str(fixture_home),
        "PATH": str(bin_dir) + os.pathsep + os.defpath,
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "SHELL": "/bin/sh",
        "TMPDIR": str(state / "tmp"),
        "XDG_CONFIG_HOME": str(fixture_home / ".config"),
        "XDG_CACHE_HOME": str(fixture_home / ".cache"),
        "XDG_DATA_HOME": str(fixture_home / ".local/share"),
        "GH_CONFIG_DIR": str(fixture_home / ".config/gh"),
        "AZURE_CONFIG_DIR": str(fixture_home / ".azure"),
        "CLOUDSDK_CONFIG": str(fixture_home / ".config/gcloud"),
        "AWS_SHARED_CREDENTIALS_FILE": str(fixture_home / ".aws/credentials"),
        "AWS_CONFIG_FILE": str(fixture_home / ".aws/config"),
        "AWS_EC2_METADATA_DISABLED": "true",
        "QA_ISOLATION_STATE": str(state),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(Path(__file__).resolve().parent),
    }


def _loopback(host: object) -> bool:
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="replace")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def install_guard(state: Path) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    state = state.resolve()
    if state.name != "e2e-state" or not state.is_dir():
        raise ValueError("QA guard requires an existing private e2e-state")
    evidence = state / "isolation-events.jsonl"

    def blocked(kind: str, target: str) -> None:
        # No arguments, URLs, headers, credential contents or query strings.
        with evidence.open("a") as stream:
            stream.write(json.dumps({"event": kind, "target": target}) + "\n")
        raise PermissionError("QA isolation blocked " + kind)

    def audit(event: str, args: tuple) -> None:
        if event == "socket.getaddrinfo" and not _loopback(args[0]):
            blocked("external_dns", str(args[0]))
        elif event == "socket.connect":
            address = args[1]
            if isinstance(address, tuple) and not _loopback(address[0]):
                blocked("external_connection", str(address[0]))
        elif event == "subprocess.Popen":
            executable = Path(os.fsdecode(args[0])).name
            if executable in _CREDENTIAL_CLIS:
                blocked("credential_cli", executable)

    sys.addaudithook(audit)
    _INSTALLED = True
