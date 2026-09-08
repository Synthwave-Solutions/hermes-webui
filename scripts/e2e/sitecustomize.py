"""Install QA-only network/credential guards before a Python child imports code."""
import os
from pathlib import Path

if os.environ.get("QA_ISOLATION_STATE"):
    from isolation import install_guard
    install_guard(Path(os.environ["QA_ISOLATION_STATE"]))
