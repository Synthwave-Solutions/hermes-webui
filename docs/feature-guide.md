# Bilingual feature guide

The Help section now includes **Browse all features**. Every **Explain this page**
flow also links to the matching area of the guide. The searchable modal contains
270 WebUI topics and a static snapshot of 178 MSP topics. Product, area and
availability filters, English/Dutch switching, related topics and deep links work
without a runtime connection to the MSP cockpit.

Each topic documents purpose, when to use it, steps, permissions, limits and an
example. Availability means implemented software, conditional configuration or
permissions, or planned work. It does not claim that a feature is active on the
current installation. The read-only owner-scoped memory explorer, audio routes,
model-gateway enforcement and optional diagnostic reporting keep their actual
limits. Browsing help never activates them.

## State and privacy

Only `sp-feature-guide-language` is stored locally. Search/filter/selection state
lives in the modal instance and never enters chat/session state, a server request
or telemetry. Closing restores focus. Native modal focus containment and local
keyboard handling prevent background application shortcuts. **Show control** only
focuses an already-visible control; it does not navigate, click, grant permissions
or modify a setting. User and bot drafts are untouched.

`?help_feature=webui.tasks.mute` and `?help_feature=msp.overview` open a topic.
Existing session URL components remain intact when a link is copied. Unknown
identifiers show an explicit notice. The downloaded JSON contains the two static
bilingual catalogs, without user, deployment or conversation data.

## Maintaining coverage

* `static/help-features.js`: public WebUI catalog, schema version 1.
* `static/help-msp-features.js`: static MSP catalog snapshot from cockpit
  `521669ca1fb6372c084592ae9d03ca076aa62630`. Refresh it from the cockpit's
  `apps/cockpit/frontend/public/feature-guide.json`; review the diff and rerun
  catalog/browser tests. There is no network import or shared runtime dependency.
* `docs/feature-guide-coverage.json`: 500 concrete control mappings, 60 supplemental
  dynamic-feature entries and all 30 composer command aliases. Equivalent
  responsive controls and save/cancel buttons map to their underlying feature.
  Multiline HTML controls are included. The picker documentation's example input
  and hidden vendor login/server/legacy visualizer controls are not active
  product workflows.

When adding a feature or control, add grounded English and Dutch content, status,
source references and its coverage mapping. Keep general catalog text free of
local paths, account identities, keys and deployment-specific addresses. Exported
`source_refs` are repository-relative review references, not navigation targets.

## Verification

Use `./scripts/test.sh` with `tests/test_feature_guide_catalog.py`,
`tests/test_help_content_coverage.py`, `tests/test_help_events.py` and
`tests/test_guida_vendored_assets.py`. Set `PLAYWRIGHT_MODULE` to an available Node
Playwright package for the existing tour behavior test.

`tests/e2e/full/feature-guide.spec.ts` runs against the isolated full-application
fixture only. It covers bilingual and cross-product search, availability filters,
JSON download, unknown/deep links, hidden-control handling, escaped search text,
keyboard focus, Escape, background shortcut isolation, draft preservation and
390/1440-pixel layouts. Never point the mutation fixture at production.
