"""Catalog coverage regression net (governance port, builder B3).

Walks the api/routes.py dispatch source with ast and collects every /api/*
path literal used in a dispatch comparison (``parsed.path == ...``,
``parsed.path in (...)``, ``parsed.path.startswith(...)``). Every collected
route must be classified by the governance catalog (route_permission
resolves a permission, or the route is an authenticated self route, or it
is one of the pre-auth public paths that never reach the hook).

Unknown /api/* routes fail closed under enforce (reason unknown_route), so
this test is the net that catches a NEW endpoint added to routes.py without
a catalog entry: the author either classifies it or consciously adds it to
the public/self sets.
"""
import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.auth import PUBLIC_PATHS  # noqa: E402
from api.governance.catalog import _SELF_ROUTES, route_permission  # noqa: E402

ROUTES_PY = Path(__file__).resolve().parent.parent / "api" / "routes.py"

_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")

# Routes that legitimately have no catalog entry because they never reach
# the enforcement hook as authenticated traffic:
# - the pre-auth public paths (check_auth lets them through unauthenticated;
#   login/OIDC/passkey ceremonies must work before any identity exists)
# - /api/csp-report (bypasses check_auth AND the hook in server._handle_write)
# - the bare "/api/" prefix marker used by generic guards, not a route
_PUBLIC_OK = frozenset(PUBLIC_PATHS) | {"/api/csp-report", "/api/"}


def _is_path_attr(node) -> bool:
    """Match ``<anything>.path`` (parsed.path and friends)."""
    return isinstance(node, ast.Attribute) and node.attr == "path"


def _string_consts(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node.value
    elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for elt in node.elts:
            yield from _string_consts(elt)


class _DispatchWalker(ast.NodeVisitor):
    """Collect route literals from path comparisons across routes.py."""

    def __init__(self):
        self.exact: set[str] = set()
        self.prefixes: set[str] = set()

    def visit_Compare(self, node):
        if _is_path_attr(node.left):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq, ast.In, ast.NotIn)):
                    self.exact.update(_string_consts(comp))
        self.generic_visit(node)

    def visit_Call(self, node):
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "startswith"
            and _is_path_attr(func.value)
        ):
            for arg in node.args:
                self.prefixes.update(_string_consts(arg))
        self.generic_visit(node)


def _walk_dispatch():
    walker = _DispatchWalker()
    walker.visit(ast.parse(ROUTES_PY.read_text(encoding="utf-8")))
    return walker


def _classified(path: str, *, prefix: bool) -> bool:
    if path in _SELF_ROUTES:
        return True
    if any(route_permission(path, method) for method in _METHODS):
        return True
    if prefix:
        # A startswith guard governs children too; a catalog prefix rule
        # that classifies the subtree counts.
        child = path.rstrip("/") + "/x"
        return any(route_permission(child, method) for method in _METHODS)
    return False


@pytest.fixture(scope="module")
def dispatch():
    return _walk_dispatch()


def test_dispatch_walk_finds_the_route_surface(dispatch):
    """Guard the walker itself: if routes.py changes dispatch idiom and the
    walk goes blind, this fails loudly instead of vacuously passing."""
    api_routes = {p for p in dispatch.exact | dispatch.prefixes if p.startswith("/api/")}
    assert len(api_routes) > 150, (
        f"dispatch walk only found {len(api_routes)} /api/* literals; "
        "routes.py dispatch style may have changed, update the walker"
    )


def test_every_dispatched_api_route_is_classified(dispatch):
    unclassified = []
    for path in sorted(p for p in dispatch.exact if p.startswith("/api/")):
        if path in _PUBLIC_OK:
            continue
        if not _classified(path, prefix=False):
            unclassified.append(path)
    for path in sorted(p for p in dispatch.prefixes if p.startswith("/api/")):
        if path in _PUBLIC_OK:
            continue
        if not _classified(path, prefix=True):
            unclassified.append(path + "*")

    assert not unclassified, (
        "routes.py dispatches /api/* paths the governance catalog does not "
        "classify; they would fail closed (unknown_route) under enforce for "
        "every non-bootstrap user. Add RouteRule entries to "
        "api/governance/catalog.py (or, only if genuinely pre-auth/self, "
        "extend _PUBLIC_OK / _SELF_ROUTES): " + ", ".join(unclassified)
    )


def test_public_routes_stay_out_of_the_catalog_by_design():
    """The pre-auth ceremonies must not require a permission: check_auth
    admits them without a session, and the hook would otherwise deny them
    as unauthenticated under enforce (login lockout)."""
    for path in ("/api/auth/login", "/api/auth/oidc/start", "/api/auth/oidc/callback",
                 "/api/auth/passkey/options", "/api/auth/passkey/login"):
        assert path in PUBLIC_PATHS
        for method in _METHODS:
            assert route_permission(path, method) is None, path


def test_unknown_api_routes_stay_unclassified():
    """The fail-closed mechanism: an uncataloged route resolves no
    permission, so enforcement returns unknown_route."""
    for method in _METHODS:
        assert route_permission("/api/definitely-not-a-real-route", method) is None
