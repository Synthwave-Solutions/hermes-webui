# Installed apps directory

Apps is a dedicated navigation destination for the installation's creative,
productivity, automation and platform tools. An app opens in a separate tab and
retains its own sign-in and permissions. A configured link means its address is
configured; it does not claim that the service is healthy, signed in or available
under the current subscription. The directory does not fetch app pages or health
endpoints, proxy services, create sessions or activate modules.

## Deployment configuration

`SP_APP_LINKS` is a JSON object mapping audited app IDs to HTTPS URLs. Only IDs
in `api/app_catalog.py` are accepted. Names, descriptions, categories, module
associations and access classes come from that registry, never from the supplied
JSON or request parameters. An absent ID is not listed. An explicit `null` or
empty string keeps a disabled `unconfigured` entry visible. Invalid URLs and
wrong value types are omitted. An invalid top-level JSON value exposes no named
entries and does not break independently valid legacy links.

Example using documentation-only addresses:

```json
{
  "opendesign": "https://design.example.test/",
  "craft_studio": "https://studio.example.test/",
  "photocraft": "https://studio.example.test/photo/",
  "n8n": "https://workflows.example.test/",
  "openwebui": null
}
```

The curated registry includes OpenDesign, Craft Studio and all eight editors,
HyperFrames, n8n, OmniRoute, Nango, DocuSeal, MSP Cockpit, Open WebUI, RAGFlow,
Langfuse and HermesOffice. Personal dashboards and the classic design entry are
omitted. HermesOffice is a desktop download, identified by
`launch_kind: desktop_download`. Its exact official GitHub latest-release URL is
the only audited external distribution exception; arbitrary GitHub links and
other app IDs do not receive that exception.

The URL boundary is the existing launcher boundary: HTTPS without credentials,
query parameters or fragments; an installation-owned `SP_DOMAIN` or subdomain on
port 443, or its exact `SP_MESH_FQDN` with an explicit service port if needed.
The existing internal-component hostname denylist still applies. Use deployment
aliases or the exact configured private hostname, not new implicit trust for an
app brand. Request Host headers do not establish trust. App names being visible
in the directory do not relax hostname validation.

## Access and module behavior

Members see only member entries whose associated module is active. Creative
apps use `design_studio`; DocuSeal uses `e_signing` and HermesOffice uses `office_apps`. n8n requires platform scope
unless `SP_WORKFLOWS_CLIENT_EDITOR=1` explicitly permits member access; it still
requires the `workflows` module for members.

OmniRoute, Nango, MSP Cockpit, Open WebUI, RAGFlow and Langfuse are platform-only entries. Organisation,
department and billing administrators do not thereby gain platform access.

Platform administrators can discover all explicitly configured named apps,
even if the corresponding WebUI module is inactive. This is an inventory of
external installed applications, not module activation: module route gates,
entitlements and each destination's access checks remain unchanged. For example,
a platform administrator may see an existing DocuSeal address while
`/api/signing/` remains blocked because `e_signing` is inactive.

Authentication-disabled and anonymous requests are refused. Failure to resolve
identity and policy returns 503 without revealing app entries.

## API and compatibility

`GET /api/apps` returns `{ "apps": [...] }`. Every entry has:

- `id`: the audited app ID, or the legacy module ID.
- `module`: its existing module association.
- `name` and `description`: objects with `nl` and `en` text.
- `category`: `creative`, `craft`, `productivity`, `automation` or `platform`.
- `access`: `member` or `platform` after applying the workflow editor opt-in.
- `url`: a validated HTTPS address, or `null`.
- `status`: `configured` or `unconfigured`.

`SP_MODULE_LINKS` retains its earlier active-module, workflow-scope and URL
validation behavior, including omission of empty links. These legacy entries
also carry the extended API fields. A configured named OpenDesign, n8n or
DocuSeal entry suppresses its corresponding legacy `design_studio`, `workflows`
or `e_signing` tile. An unconfigured or invalid named entry does not suppress a
working legacy link. Other Craft editors do not suppress the OpenDesign entry.

No new persistent state, permission, background process or outbound request is
introduced. Configuration remains owned by the deployment environment.

## Browser verification

The committed `scripts/e2e/server_fixture.py` seeds all 20 apps with synthetic
HTTPS addresses, one unconfigured destination and separate platform,
organisation-admin and member identities. Browser networking remains restricted
to loopback. Run `scripts/e2e/run_full.py --engine <engine-checkout>` with
`--grep 'Apps directory|every app has|organisation admin modules|member module boundary|platform launcher'`
to exercise Apps and module navigation, role gates, NL/EN copy, viewport widths,
loading failures, restored filters and drafts, and every app spotlight. The
runner creates private test state and stops its fixture processes on exit.
