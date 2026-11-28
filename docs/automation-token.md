# Automation service token

A narrow, fail-closed bearer token so the inbound-offer automation can create
group chats without a person's 30 day session cookie. It is off until a token
is created.

## Header

```
Authorization: Bearer <token>
```

The token starts with `hat_`. It is shown once by `create` and never stored:
only an HMAC-SHA256 hash (keyed with the WebUI signing key) is written to
`STATE_DIR/automation_token.json` (mode 0600), together with owner e-mail,
label, `created_at`, optional `expires_at` and the ids of sessions the token
created.

## Allowed routes (everything else with a bearer header: 403)

| Method | Route | Limit |
| --- | --- | --- |
| POST | `/api/session/import` | creates a session owned by the token owner |
| POST | `/api/session/participants` | only sessions this token created |
| POST | `/api/session/delete` | only sessions this token created |
| GET | `/api/session?session_id=...` | only sessions this token created |
| GET | `/api/file/raw?session_id=...` | only sessions this token created |

## Rules

- Loopback source only. A non-loopback peer, or a request carrying
  `X-Forwarded-For`, `X-Real-IP` or `Forwarded`, gets 403.
- Constant-time hash compare. Failures count against the login rate limiter
  (5 per minute per IP), after which the answer is 429.
- Expiry and revoke are checked on every request, no cache.
- The request acts as `owner_email` with no elevation: normal governance
  routes, ownership and participant validation (only governance-known
  addresses) apply. A `owner` or `owner_email` in the body is ignored.
  Admin-only routes are not on the allowlist.
- CSRF is skipped only for bearer requests on the allowlisted routes. Cookie
  requests keep Origin and CSRF token checks unchanged.
- Each bearer request writes an `automation_token_request` row to the
  governance audit log (route, session id, outcome, label). Never the token.

## Operate (run from the repo root, same state dir as the server)

```
python scripts/automation_token.py create --owner owner@example.test --label inbound-offerte --days 90
python scripts/automation_token.py status      # never prints the token
python scripts/automation_token.py revoke
```

Rotate: `create ... --rotate` replaces the active token (the old one stops
working at once; the created-session list is kept so earlier chats stay
manageable). Revoke: `revoke`, effective on the next request. Store the token
in the secret store of the helper, not in env vars, logs or chat.

## Switching the helper later

`bin/create_proposal_chat.py` today sends the personal session cookie and the
CSRF header. To switch, send `Authorization: Bearer <token>` instead, drop the
cookie and CSRF header, and call `http://127.0.0.1:<port>` directly (no proxy,
no public URL). Do it only after the token has been created and approved.
