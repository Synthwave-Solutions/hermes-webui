#!/usr/bin/env python3
"""Launch a WebUI component in the PM-selected Hermes dependency environment."""

import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
agent = Path(
    os.environ.get("HERMES_WEBUI_AGENT_DIR", str(Path.home() / ".hermes/hermes-agent"))
).expanduser()
sys.path.insert(0, str(agent))
from pm.environments import owning_home_root, project_python
from hermes_constants import set_hermes_home_override, reset_hermes_home_override

# Select dependencies from the checkout owner, without changing the executing
# profile's HOME/HERMES_HOME or importing that owner's user configuration.
owner = owning_home_root(agent)
token = set_hermes_home_override(owner) if owner else None
try:
    python = project_python(agent)
finally:
    if token is not None:
        reset_hermes_home_override(token)
env = dict(os.environ)
env["HERMES_WEBUI_PYTHON"] = str(python)
env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
env["PYTHONPATH"] = os.pathsep.join(
    [str(agent), str(root), env.get("PYTHONPATH", "")]
).rstrip(os.pathsep)
os.execve(str(python), [str(python), *sys.argv[1:]], env)
