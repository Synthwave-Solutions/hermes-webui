#!/usr/bin/env python3
"""Manage the automation service token (create, revoke, status).

create prints the token once to stdout; only its hash is written to
STATE_DIR/automation_token.json. status never prints the token.
Run from the repo root so the webui state dir and signing key resolve the same
way as the server does (honours HERMES_WEBUI_STATE_DIR).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import automation_token as at  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("--owner", required=True)
    c.add_argument("--label", required=True)
    c.add_argument("--days", type=int, default=None)
    c.add_argument("--rotate", action="store_true", help="replace an active token")
    sub.add_parser("revoke")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "create":
        try:
            token = at.create(a.owner, a.label, a.days, rotate=a.rotate)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(token)
        return 0
    if a.cmd == "revoke":
        print("revoked" if at.revoke() else "no token to revoke")
        return 0
    print(json.dumps(at.status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
