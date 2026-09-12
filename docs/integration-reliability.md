# Integration and delivery verification

The integration catalog now preserves each configured Nango integration, even
when multiple configurations use the same provider. Each Connect action uses
that configuration's unique key, and the catalog shows the key to distinguish
the entries. Connection ownership and approval checks remain on the server.

Both administrative Enable actions collect the credential fields specified by
the backend catalog before creating an OAuth integration. Client secrets use
password fields; private keys use a multiline field. Cancel and Escape create
no integration; closing the dialog clears its inputs. API-key providers need no application credential dialog. MCP_OAUTH2
providers use the Nango setup flow described below rather than a static credential
dialog. Existing configured providers
remain idempotent. Enabling does not prove an end-user account is connected:
the provider's subsequent authorization must complete successfully.

Capacity alerts use the installed Hermes `send_message_tool` transport directly,
without invoking a model. Delivery is confirmed only for an explicit boolean
`success: true`; malformed responses and transport failures stay failures.
The administrator must configure a destination and its platform credentials.
The in-app alert and the external delivery are separate outcomes.
An in-app alert counts only after its store write succeeds. If both storage
and external delivery fail, chat does not claim an administrator was notified.
The incident result exposes `recorded` and `dispatched` separately while
preserving `notified` for existing callers. Repeats within the cooldown do not
claim a new notification. Acknowledging an alert reports success only after the
acknowledgement is saved, so a failed write leaves it available for retry.
New alerts use unique IDs so incidents created in the same millisecond keep
their own delivery and acknowledgement state. Existing alert IDs are preserved.

Verification:

```
./scripts/test.sh -q tests/test_integration_delivery_repairs.py tests/test_integration_enable_frontend.py tests/test_integrations_oauth_credentials.py tests/test_capacity_alerts.py tests/test_cron_webui_delivery.py tests/test_selfservice_install_gate.py
```

For manual QA, open both Enable entry points at desktop and narrow widths,
cancel once, submit fixture credentials against an isolated Nango stub, and
verify the exact payload. Check two configured integrations of one provider,
each with a distinct Connect action. Test external delivery with a mocked
transport; an actual message requires an explicitly authorized recipient.

Remaining evidence gaps: live provider OAuth acceptance, live external delivery,
and platform-specific dependencies are not established by mocked regression
tests. Capacity-threshold configuration currently has no live balance poller;
its percentage helper alone does not provide proactive monitoring.

### MCP setup before Enable

Nango's public `POST /integrations` accepts an `MCP_OAUTH2` provider without
registering its OAuth client. In the inspected Nango 0.71 source, that lifecycle
runs in the authenticated dashboard create handler instead. The public API can
therefore create a row whose subsequent Connect authorization fails with
“missing client ID, secret and/or scopes.” A configured row alone is not proof
of usable authorization.

SynthPulse now prevents that incomplete creation. An administrator sees **Setup
needed**, a provider-specific **Setup guide**, and an explanation to finish OAuth
setup in Nango and refresh SynthPulse. The shared Enable helper covers both
Connections and Governance, and the server repeats the guard before any create
or implicit approval. Dynamic and CIMD providers are never asked for invented
static client credentials. Existing configured providers remain connectable;
the public integration API omits MCP credentials, and omission must not be
mistaken for missing configuration. Administrators also get the setup guide on
existing MCP cards for troubleshooting.

This is prevention and recovery guidance, not an automatic repair of existing
unregistered rows or proof of a completed user login. Repair existing provider
registration through a supported Nango management flow while preserving its
unique key and all existing connections. Do not delete and recreate a provider
to clear an error. A normal provider login and a read-only operation in the
intended user's account remain required for ticket closure.

Relevant upstream contracts:

- [Public integration creation](https://github.com/NangoHQ/nango/blob/v0.71.0/packages/server/lib/controllers/integrations/postIntegration.ts)
- [Dashboard client registration lifecycle](https://github.com/NangoHQ/nango/blob/v0.71.0/packages/server/lib/controllers/v1/integrations/postIntegration.ts)
- [MCP registration client](https://github.com/NangoHQ/nango/blob/v0.71.0/packages/shared/lib/clients/mcp.client.ts)
- [Public integration metadata](https://nango.dev/docs/reference/backend/http-api/integration/get)

Regression checks:

```sh
./scripts/test.sh -q tests/test_integrations_mcp_setup.py tests/test_integrations_oauth_credentials.py tests/test_integration_enable_frontend.py tests/test_integration_delivery_repairs.py tests/test_selfservice_install_gate.py
node tests/frontend/integrations-mcp-setup.cjs
```

The rendered-module browser test uses Playwright (`PLAYWRIGHT_MODULE_PATH` may
point at an existing installation) and writes evidence to
`SYNTHPULSE_QA_OUTPUT`, defaulting to `test-results/mcp-setup`. It loads the actual
integration script and stylesheet, exercises admin/member states at 1440px and
390px, checks setup-guide and Connect clicks for the selected configuration,
and checks that both Enable entry points avoid a write and credential dialog.
The API is a fixture and external requests are blocked; this test establishes
frontend behavior, not live OAuth success.
