import ast
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from api.usage_cost import agent_cost_usage

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("status,amount,expected", [
    ("unknown", 0.0, None), ("unknown", 1.2, None),
    ("included", 0.0, 0.0), ("actual", 0.0, 0.0),
    ("estimated", 1.2, 1.2), (None, 0.4, 0.4),
])
def test_engine_cost_projection(status, amount, expected):
    result = agent_cost_usage(SimpleNamespace(
        session_cost_status=status, session_estimated_cost_usd=amount,
        session_cost_source="none"))
    assert result == dict(estimated_cost=expected, cost_status=status, cost_source="none")


def test_session_roundtrip_unknown_and_known_zero():
    from api.models import Session
    for status, expected in [("unknown", None), ("included", 0.0)]:
        session = Session(workspace="/tmp", estimated_cost=0.0,
                          cost_status=status, cost_source="none")
        compact = session.compact()
        assert compact["estimated_cost"] == expected
        assert compact["cost_status"] == status
        restored = Session(**compact)
        assert restored.cost_status == status
        assert restored.estimated_cost == expected


def test_actual_done_usage_dict_forwards_cost_contract():
    tree = ast.parse((ROOT / "api/streaming.py").read_text())
    candidates = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "usage" for t in n.targets)
                  and isinstance(n.value, ast.Dict)]
    payload = next(n.value for n in candidates if any(
        isinstance(v, ast.Name) and v.id == "cost_usage" for v in n.value.values))
    cost = agent_cost_usage(SimpleNamespace(session_cost_status="unknown",
        session_estimated_cost_usd=0.0, session_cost_source="none"))
    # Execute the real dictionary's cost fields, independently of provider/runtime setup.
    fields = ast.Dict(keys=[None], values=[next(v for v in payload.values
                        if isinstance(v, ast.Name) and v.id == "cost_usage")])
    actual = eval(compile(ast.fix_missing_locations(ast.Expression(fields)), "", "eval"),
                  {"cost_usage": cost})
    assert actual["estimated_cost"] is None
    assert actual["cost_status"] == "unknown"


@pytest.mark.parametrize("status,cost,expected", [
    ("unknown", None, "Cost unavailable"), ("included", 0, "$0.0000"),
    ("estimated", 1.2, "$1.20"),
])
def test_real_context_cost_rendering(status, cost, expected):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for frontend behavior")
    source = (ROOT / "static/ui.js").read_text()
    start = source.index("  let costText='';", source.index("function _syncCtxIndicator"))
    end = source.index("  _syncMobileCtxDisplay", start)
    script = ("const usage=" + json.dumps({"cost_status": status}) +
              ";const cost=" + json.dumps(cost) +
              ";const costLine={style:{}};const cacheText='';" + source[start:end] +
              ";console.log(costLine.textContent)")
    result = subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)
    assert expected in result.stdout

def test_unknown_cost_does_not_resurrect_stale_price():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for frontend behavior")
    source = (ROOT / "static/ui.js").read_text()
    start = source.index("function _mergeUsageForCtxIndicator(")
    end = source.index("\nfunction ", start + 10)
    script = source[start:end] + """
console.log(JSON.stringify(_mergeUsageForCtxIndicator(
{estimated_cost:null,cost_status:'unknown',cost_source:'none'},
{estimated_cost:1.2,cost_status:'estimated'})));
"""
    result = subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)
    actual = json.loads(result.stdout)
    assert actual["estimated_cost"] is None
    assert actual["cost_status"] == "unknown"
