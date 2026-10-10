"""A stand-in reader child that answers the init line and then never answers.

Used by tests/test_memdash_interim_sqlite.py to prove that the WebUI kills a
reader that stops answering and starts a new one for the next request.
"""
import json
import sys
import time

for line in sys.stdin:
    message = json.loads(line)
    if message.get("op") == "init":
        sys.stdout.write(json.dumps({"ok": True, "init": len(message.get("allow") or [])}) + "\n")
        sys.stdout.flush()
        continue
    time.sleep(60)
