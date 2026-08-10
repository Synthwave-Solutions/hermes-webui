# `api/governance/`

Dashboard governance for this application: policy loading, access resolution, a
route-to-permission catalog, request enforcement, audit, usage counters, the
per-turn agent binding and the profile-sync bridge. Added by the SynthPulse fork;
it is a port of the engine's `dashboard_governance` package with the engine
imports removed (standard library plus `yaml` only, no FastAPI, no `hermes_cli`).

The package is deliberately independent from authentication: `api/auth.py`
verifies **who** the caller is, this package decides **what** that caller may do.
The admin HTTP surface lives one level up, in `api/governance_api.py`.

| Module | Responsibility |
|---|---|
| `loader.py` | Parse, validate, cache and atomically persist `~/.hermes/dashboard-governance.yaml` (override: `HERMES_WEBUI_GOVERNANCE_POLICY`) |
| `models.py` | `GrantSet` and the policy/role/group/user/subject dataclasses, plus the merge and deny-subtract algebra |
| `resolver.py` | Subject to `EffectiveAccess`, with a grant source recorded for every merge |
| `catalog.py` | Route to permission for this application's API surface. Unknown `/api/*` fails closed |
| `enforce.py` | The decision core plus the `http.server` adapter called from `server.py`. Never reads the request body |
| `audit.py` | JSONL audit trail with hashed subjects and secret redaction |
| `usage.py` | Usage counters and caps (read-only consumer today) |
| `agent_context.py` | Binds the caller's access around an in-process agent turn |
| `profile_sync.py` | Fire-and-forget trigger for the engine-side per-user profile provisioner |

Two rules when editing:

- A new `/api/*` endpoint must be classified in `catalog.py` in the same change.
  `tests/test_governance_catalog_coverage.py` is the net, and it also keeps
  `_ANON_ROUTES` aligned with `api.auth.PUBLIC_PATHS`.
- Keep the decision order in `enforce.evaluate_request` intact. The pre-policy
  branches are what stop a broken policy file from locking everyone out of the
  login page.

Full documentation: [`docs/SYNTHPULSE-GOVERNANCE.md`](../../docs/SYNTHPULSE-GOVERNANCE.md).
Design notes and decision log: [`docs/governance-port-design.md`](../../docs/governance-port-design.md).
