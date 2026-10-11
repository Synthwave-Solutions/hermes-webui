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

The fixed registry includes OpenDesign and OpenDesign Classic, Craft Studio and
all eight editors (PhotoCraft, FilmCraft, EffectCraft, VectorCraft, LightCraft,
DesignCraft, PDFCraft and SoundCraft), HyperFrames, Vision Studio, n8n, OmniRoute,
Nango, DocuSeal, Pareltje, SlibDetect, MSP Cockpit, SilverBullet, Pixel Office,
Mnemosyne, Strategy Gantt and Open WebUI.

The URL boundary is the existing launcher boundary: HTTPS without credentials,
query parameters or fragments; an installation-owned `SP_DOMAIN` or subdomain on
port 443, or its exact `SP_MESH_FQDN` with an explicit service port if needed.
The existing internal-component hostname denylist still applies. Use deployment
aliases or the exact configured private hostname, not new implicit trust for an
app brand. Request Host headers do not establish trust. App names being visible
in the directory do not relax hostname validation.

## Access and module behavior

Members see only member entries whose associated module is active. Creative
apps use `design_studio`; DocuSeal uses `e_signing`. n8n requires platform scope
unless `SP_WORKFLOWS_CLIENT_EDITOR=1` explicitly permits member access; it still
requires the `workflows` module for members.

OmniRoute, Nango, MSP Cockpit, Pareltje, SlibDetect, SilverBullet, Pixel Office,
Mnemosyne, Strategy Gantt and Open WebUI are platform-only entries. Organisation,
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
