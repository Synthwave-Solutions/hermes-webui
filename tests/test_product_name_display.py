"""Exercise the real display-name resolver, including saved legacy defaults."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.skipif(not shutil.which("node"), reason="Node is required for frontend behavior")
def test_product_aliases_and_custom_bot_names():
    source = Path(__file__).resolve().parents[1] / "static/ui.js"
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const text = fs.readFileSync(process.argv[1], 'utf8');
const boundary = text.indexOf('const INFLIGHT=');
if (boundary < 0) throw new Error('Display resolver boundary missing');
const context = vm.createContext({window: {}});
vm.runInContext(text.slice(0, boundary), context);
const cases = [null, '', 'SynPulse', 'SynPulse Control', 'SynthPulse',
               'SynthPulse Control', 'Hermes', 'Hermes Control',
               'Research assistant', 'SynPulse Research'];
const names = cases.map(name => {
  context.window._botName = name;
  return vm.runInContext('assistantDisplayName()', context);
});
vm.runInContext("S.activeProfile='research'", context);
names.push(vm.runInContext('assistantDisplayName()', context));
process.stdout.write(JSON.stringify(names));
"""
    output = subprocess.check_output([shutil.which("node"), "-e", script, str(source)], text=True)
    assert json.loads(output) == ["SynthPulse"] * 8 + [
        "Research assistant", "SynPulse Research", "Research"
    ]
