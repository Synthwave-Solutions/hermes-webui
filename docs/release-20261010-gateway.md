# Network and model gateway boundaries

App connection setup now requires an explicit `HERMES_WEBUI_NANGO_CONNECT_URL`.
Without a valid HTTP(S) address the API returns `not_configured` without minting
a session or recording an approval. Existing connections remain usable. Webhook
publishing uses an explicitly configured public platform address when present;
HQ's existing CLI publishing path remains supported. User copy uses neutral
network descriptions.

Model gateway enforcement stays off by default. With enforcement enabled,
profile environment files cannot override installation gateway settings or add
provider credentials. Named profiles need their own gateway credential; they
cannot inherit an installation key file. Realtime calls use a configured gateway
route and retain that route for sideband and hangup; unavailable routes return
`gateway_required` with clear user copy. Server speech uses the engine gateway
adapter and refuses if it cannot verify gateway enforcement or audio support.
The existing hardened HQ speech adapters remain active while enforcement is off:
this preserves their byte limits, DNS pinning, redirect/proxy protection and
provider configuration without requiring new optional SDKs. Their entry point
also independently refuses under enforcement.

Deployment must explicitly retain HQ's existing Nango public connection address.
Do not enable `SP_MODEL_GATEWAY_ENFORCE`, `SP_MODEL_GATEWAY_AUDIO` or
`SP_MODEL_GATEWAY_REALTIME` until the matching engine gateway implementation,
per-profile key registry and routes are provisioned and verified. This release
neither provisions provider keys nor migrates the existing HQ shared-key setup.

Validation covers neutral connect/webhook behavior, profile key isolation,
voice routing/refusal and the existing hardened speech transport tests. Browser
checks exercise actual realtime HTTP and sideband WebSockets with a loopback
provider, two conversational turns without overwriting a draft, settings
persistence, and enforced speech refusal/restoration in isolated QA state.
