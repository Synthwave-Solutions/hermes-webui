"""The upstream memory dashboard's read helpers, vendored and hardened.

``dashboard_core.py`` is the pristine upstream file of
``wysie/mnemosyne-dashboard`` at a918e5e0841fdc85baad7ab582432b2b7499b2f2
(v0.14.0, MIT, see ``LICENSE``); its sha256 is pinned in
``tests/test_memdash_vendor.py``. It is never edited: ``patches.py`` hardens
it at import time (plan addendum 6.6.7). Only the Memory explorer's reader
child (``python -m api.memdash_reader``) imports this package; the WebUI
process never opens a memory store itself.

Upstream's ``server.py``, ``config.py`` and plugin ``__init__.py`` (the agent
tools that accept a host, a database path and a password) are deliberately
not vendored, so there is no second listener and no configuration route.
"""

from __future__ import annotations

import sys

# dashboard_core optionally imports the upstream memory package for its
# pattern detector and sync diagnostics. That package resolves default data
# directories under the service home on import, so it is blocked here: the
# dashboard then degrades to its own taxonomy, which is what the reader needs.
_BLOCKED = ("mnemosyne", "mnemosyne.core", "mnemosyne.core.streaming")
_previous = {name: sys.modules.get(name, KeyError) for name in _BLOCKED}
for _name in _BLOCKED:
    sys.modules[_name] = None  # type: ignore[assignment]
try:
    from . import dashboard_core  # noqa: E402
finally:
    for _name, _value in _previous.items():
        if _value is KeyError:
            sys.modules.pop(_name, None)
        else:
            sys.modules[_name] = _value

from . import patches  # noqa: E402

patches.apply(dashboard_core)

DashboardStore = dashboard_core.DashboardStore
allow_paths = patches.allow_paths
set_deadline = patches.set_deadline

__all__ = ["DashboardStore", "allow_paths", "set_deadline", "dashboard_core", "patches"]
