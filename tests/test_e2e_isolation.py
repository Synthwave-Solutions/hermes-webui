"""Regression for provider discovery escaping the original QA fixture home."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qa_isolation", ROOT / "scripts/e2e/isolation.py")
isolation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(isolation)


def test_fixture_environment_excludes_host_secrets_and_cli_config(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "synthetic-secret-not-in-child")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-secret-not-in-child")
    monkeypatch.setenv("GH_CONFIG_DIR", str(tmp_path / "real-gh"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "real-config"))
    env = isolation.fixture_environment(tmp_path / "e2e-state")
    assert "GH_TOKEN" not in env and "OPENAI_API_KEY" not in env
    assert Path(env["HOME"]) == tmp_path / "e2e-state/os-home"
    assert Path(env["GH_CONFIG_DIR"]).is_relative_to(tmp_path / "e2e-state")
    assert Path(env["XDG_CONFIG_HOME"]).is_relative_to(tmp_path / "e2e-state")
    assert os.environ["GH_TOKEN"] == "synthetic-secret-not-in-child"


def test_child_guard_blocks_external_sockets_and_keychain_before_execution(tmp_path):
    state = tmp_path / "e2e-state"
    env = isolation.fixture_environment(state)
    script = r'''
import json, socket, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'loopback')
    def log_message(self, *args): pass
server = HTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
assert urlopen('http://127.0.0.1:'+str(server.server_port)).read() == b'loopback'
for action in [lambda:socket.getaddrinfo('example.invalid',443),
               lambda:socket.socket().connect(('192.0.2.1',443)),
               lambda:subprocess.run(['/usr/bin/security','find-generic-password']),
               lambda:subprocess.run(['gh','auth','token'])]:
    try: action()
    except PermissionError: pass
    else: raise AssertionError('guard did not reject unsafe QA discovery')
server.shutdown()
'''
    result = subprocess.run([sys.executable, "-c", script], env=env, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    events = [json.loads(line) for line in (state / "isolation-events.jsonl").read_text().splitlines()]
    assert [event["event"] for event in events] == ["external_dns", "external_connection", "credential_cli", "credential_cli"]


def test_guard_is_inherited_by_python_grandchildren(tmp_path):
    env = isolation.fixture_environment(tmp_path / "e2e-state")
    script = "import subprocess,sys; r=subprocess.run([sys.executable,'-c',\"import socket; socket.getaddrinfo('example.invalid',443)\"],capture_output=True,text=True); assert r.returncode!=0 and 'QA isolation blocked external_dns' in r.stderr"
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
