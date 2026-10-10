# Apps and local module overview

Apps opens configured module links in a new tab. A signed-in person sees only
active modules with valid links. Each target app still checks its own identity
and permissions. With no valid links, the launcher shows an explicit empty state.

Modules is a read-only view for organisation, billing and platform administrators
on an organisation installation. It is hidden at headquarters and unavailable to
members or department administrators. The catalogue has four Standard and six
Advanced entries, including office apps. The screen, launcher and feature guide
have independent Dutch and English explanations.

The local resolver reads only `SP_ENABLED_MODULES`. Empty, malformed or unavailable
configuration resolves to Standard; `*` only includes Advanced at headquarters.
The environment describes configuration, not health, commercial entitlement or
provider readiness. Advanced pilot availability requires confirmation. Prices and
requests are not connected: the contact disclosure sends nothing, and an
otherwise authorised `POST /api/org/modules/request` returns 503
`requests_not_connected`. No screen activates modules, connections or purchases.

App links are a JSON map from module id to URL in `SP_MODULE_LINKS`. Links must use
HTTPS, have no credentials, query or fragment, and use the installation's
`SP_DOMAIN` (or a subdomain) on port 443, or its exact `SP_MESH_FQDN` with the
configured service port. No domain comes from the request Host header. Internal
component names in hosts are refused. Workflow editor links require platform
scope unless `SP_WORKFLOWS_CLIENT_EDITOR=1` explicitly enables them for users.

The connection registry explains Works with, its configured state, required
modules and any consent condition. Expanding it does not transmit data. Consumers
must still check runtime prerequisites and actual consent before acting.

The backend applies module gates after authentication and governance. Client
visibility never grants access. Module-derived settings are discarded on settings
writes. A failed settings fetch keeps module surfaces hidden. Existing chat drafts
are not changed by viewing the launcher or catalogue.
