#!/usr/bin/env python3
"""Add the Studio, Organisation and Management routes to internal route allowlists.

Every handler decides access itself (api/org_structure.request_scope), but a
role or group with a route allowlist cannot reach a route that is not on it.
This adds the new routes to the internal Synthwave roles and groups only.
Freelancers, clients and viewers are left out on purpose.

The file is edited as text: new ``- /api/...`` lines go right after the last
item of each target's ``routes:`` list, with the same indentation, so every
other byte of the policy (comments, wrapping, nulls) stays as it is.

    python3 scripts/governance_add_studio_routes.py --plan
    python3 scripts/governance_add_studio_routes.py --apply    (backup next to the policy)
"""
import argparse
import os
import re
import shutil
import sys
import time

import yaml

POLICY = os.environ.get("HERMES_WEBUI_GOVERNANCE_POLICY", os.path.expanduser("~/.hermes/dashboard-governance.yaml"))
ROUTES = ["/api/studio/usecases", "/api/studio/usecase", "/api/studio/step", "/api/studio/delete",
          "/api/org/structure/me", "/api/org/structure", "/api/org/chart",
          "/api/management/overview", "/api/management/job", "/api/management/pricing",
          "/api/value/job", "/api/value/chat", "/api/value/collect"]
TARGETS = {"roles": ["admin_delivery", "operator", "tech_lead"], "groups": ["sw-medewerker", "sw-commercie"]}


def _block(lines, start, indent):
    """Index after the block that starts at ``start`` with ``indent``."""
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if line.strip() and (len(line) - len(line.lstrip(" "))) <= indent and not line.lstrip().startswith("#"):
            return i
        i += 1
    return i


def insert(text: str, kind: str, name: str, missing: list[str]) -> str:
    lines = text.split("\n")
    top = next(i for i, l in enumerate(lines) if l == f"{kind}:")
    end_top = _block(lines, top, 0)
    entry = next(i for i in range(top + 1, end_top) if re.fullmatch(rf"\s+{re.escape(name)}:\s*", lines[i]))
    e_indent = len(lines[entry]) - len(lines[entry].lstrip(" "))
    end_entry = _block(lines, entry, e_indent)
    routes = next(i for i in range(entry + 1, end_entry) if re.fullmatch(r"\s+routes:(\s+&\S+)?\s*", lines[i]))
    r_indent = len(lines[routes]) - len(lines[routes].lstrip(" "))
    last = routes
    item_prefix = None
    for i in range(routes + 1, end_entry):
        stripped = lines[i].lstrip(" ")
        ind = len(lines[i]) - len(stripped)
        if stripped.startswith("- ") and ind >= r_indent:
            last = i
            item_prefix = lines[i][: ind] + "- "
        elif stripped and ind <= r_indent:
            break
    if item_prefix is None:
        raise SystemExit(f"{kind}.{name}: routes list not found in block form")
    lines[last + 1:last + 1] = [item_prefix + r for r in missing]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    text = open(POLICY, encoding="utf-8").read()
    data = yaml.safe_load(text)
    changes = []
    seen = set()
    for kind, names in TARGETS.items():
        for name in names:
            routes = (((data.get(kind) or {}).get(name) or {}).get("grants") or {}).get("routes")
            if not isinstance(routes, list) or "*" in routes:
                continue
            # A YAML alias (routes: *id002) shares the list of another entry:
            # adding it there once covers both.
            if id(routes) in seen:
                print(f"{kind}.{name}: shares its routes with an entry above")
                continue
            seen.add(id(routes))
            missing = [r for r in ROUTES if r not in routes]
            if missing:
                changes.append((kind, name, missing))
    for kind, name, missing in changes:
        print(f"{kind}.{name}: + {len(missing)} routes")
    if not changes:
        print("nothing to add")
        return 0
    if args.apply:
        new = text
        for kind, name, missing in changes:
            new = insert(new, kind, name, missing)
        check = yaml.safe_load(new)
        for kind, name, missing in changes:
            assert set(missing) <= set(check[kind][name]["grants"]["routes"]), (kind, name)
        backup = f"{POLICY}.bak-studio-routes-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(POLICY, backup)
        tmp = POLICY + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(new)
        os.replace(tmp, POLICY)
        print("applied; backup", backup)
    return 0


if __name__ == "__main__":
    sys.exit(main())
