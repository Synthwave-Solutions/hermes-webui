# Apps and local module overview

Apps is a dedicated primary navigation section on desktop and mobile. It groups
configured destinations by purpose, with name/description search (including the
OmniRouter alias), category filtering, independent Dutch/English copy, and an
interactive guide for each named app. Apps open in a new tab; each destination
still checks its own identity and permissions. Missing browser addresses appear
without an Open action. A configured link does not claim that a service is healthy.

The named stack directory uses `SP_APP_LINKS`; see [Apps registry](apps-registry.md)
for identities, URL validation and role gates. Platform administrators can see the
installed stack regardless of module discovery state. Ordinary users still need
the matching active module and app access. Legacy module links remain supported.
The directory handles loading, retry, empty and no-result states and clears loaded
app data if settings or access are unavailable.
Modules is a read-only view for organisation, billing and platform administrators
on an organisation installation. It is hidden at headquarters and unavailable to
members or department administrators. The catalogue has four Standard and six
Advanced entries, including office apps. The screen, Apps directory and feature guide
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
are not changed by viewing Apps or the module catalogue.
