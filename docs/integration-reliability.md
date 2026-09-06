# Integration and delivery verification

The integration catalog now preserves each configured Nango integration, even
when multiple configurations use the same provider. Each Connect action uses
that configuration's unique key, and the catalog shows the key to distinguish
the entries. Connection ownership and approval checks remain on the server.

Both administrative Enable actions collect the credential fields specified by
the backend catalog before creating an OAuth integration. Client secrets use
password fields; private keys use a multiline field. Cancel and Escape create
no integration; closing the dialog clears its inputs. API-key and MCP_OAUTH2
providers need no application credential dialog. Existing configured providers
remain idempotent. Enabling does not prove an end-user account is connected:
the provider's subsequent authorization must complete successfully.

Capacity alerts use the installed Hermes `send_message_tool` transport directly,
without invoking a model. Delivery is confirmed only for an explicit boolean
`success: true`; malformed responses and transport failures stay failures.
The administrator must configure a destination and its platform credentials.
The in-app alert and the external delivery are separate outcomes.

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
