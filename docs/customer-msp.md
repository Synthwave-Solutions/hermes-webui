# Customer MSP service

The main WebUI exposes **My MSP / Mijn MSP** for tickets, support minutes,
per-app support subscriptions and payments. **Apps** exposes application requests,
launcher availability and Basic, Plus and Premium support requests.
All six topics have Dutch and English interactive guides.

## Connection and identity

Configure `SP_CONTROL_KEY_FILE` with the private, mode-0600 JSON **single control
key entry** returned by enrollment. Never use a reporter or ingest key.
Use `SP_CONTROL_URL` for a remote control API, or `SP_CONTROL_SOCKET` with an
absolute Unix socket path for a colocated installation. Socket transport preserves
HMAC authentication and signed acting-user headers; redirects are refused.
The installation key binds the organisation. No browser-supplied identity, role,
organisation, URL or key is forwarded. Known policy users and bootstrap admins
can use self service; anonymous and unrecognised accounts cannot.

Import the corresponding organisation membership artifact into the control API.
Organisation or billing administrators can see hours/payments and change app
availability and support. Members create and read their own tickets; department
and organisation scopes retain the central service's visibility rules. Internal
MSP notes are never included in the customer response.

## Availability and support

Availability is stored per organisation and app. Turning an app off removes its
launch destination from `/api/apps`, across reloads and users. It preserves files
and subscriptions. This is a launcher setting, not infrastructure shutdown or
revocation of direct access to an external application. Existing app/module/role
gates still apply. Once managed, an unavailable control API fails closed.

App and support requests create real MSP service tickets. Repeated pending
requests are deduplicated. Each app has Basic, Plus and Premium levels with
unset prices by default. The MSP sets the name, scope and monthly price excluding
VAT in Cockpit **App support**. Approval requires a real configured price, an
active customer contract and staff confirmation that the customer agreed.
A requested change retains the old active level and price until approved.
Cancellation is separate from disabling the app. Recording an agreement does
not provision an app, grant extra support hours or start recurring collection.
Recurring invoicing remains the MSP finance process.

Payment links appear only for invoiced requests with live Mollie payments.
No key, prices or contracts are invented. Mollie setup and payment verification
remain in the MSP administration; visiting the return URL does not settle an invoice.

## Verification

Run `./scripts/test.sh` with `tests/test_msp_service.py`,
`tests/test_apps_launcher.py`, `tests/test_org_modules_api.py`,
`tests/test_control_plane_client.py` and the feature-guide coverage tests.
Use disposable, isolated WebUI and control API state for browser tests. Do not
submit synthetic tickets, subscriptions or payments to production.

## Base package and Agentic Consultant

My MSP starts with the base package and weekly Agentic Consultant capacity.
The base status comes from the existing contract or an explicit package request.
Organisation/billing admins can request the base package, request consultant
capacity in half-day increments (0.5 to 7 days per week), change that capacity
or request consultant cancellation. Requests create real MSP tickets and never
schedule a consultant or collect money. The previous agreement remains active
while a change is pending. Consultant days are not converted to support minutes
or monthly day totals.

Cockpit Packages lets MSP admins record the agreed monthly rate, scope and
effective date and confirm customer acceptance. An active base customer contract
is required for activation. Stale ticket decisions fail closed. App support stays
separate, with its own Basic, Plus and Premium subscriptions. The interactive
features are `webui.msp.package` and `webui.msp.consultant`.

## Compact overview and prepaid requests

My MSP sits below Apps and above Settings, including when a saved navigation
order exists. The overview leads with available hours and open tickets. Package,
consultant and automation details expand on demand; invoice history is collapsed.
Paid service offers appear in Pay & request. HQ prepares a scoped, priced offer
against an existing accounting invoice. The customer pays through Mollie, checks
the payment, then explicitly submits the request. Payment alone creates no ticket.
Top-ups add hours once after verified payment and Add hours. New support tickets
and reopened support tickets require available hours; invoice questions and
existing ticket communication remain accessible. Draft ticket text is preserved.
An absent price or payment connection is never presented as a free purchase.
