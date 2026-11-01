# Bilingual feature guide

**Page guide / Explain this page** offers an introduction and at most five key
controls from `help-content.js`, filtered by visibility and access. It loads no
feature catalogs. **Browse all features** is the optional, searchable reference
with the complete WebUI catalog and a static MSP snapshot. Product, area and
availability filters, English/Dutch switching, related topics and deep links work
without a runtime connection to the MSP cockpit.

The reference starts with WebUI topics; the product filter or Clear filters also
exposes MSP topics. Desktop has independently scrolling results and reading panes.
On mobile, select a result to read it, then use Back to return to the same search
and focused result. Filters and permissions/limits use labeled disclosures. The
interactive-guide action sits beside the topic's purpose; detailed steps,
examples and access information remain available.

Each topic documents purpose, when to use it, steps, permissions, limits and an
example. Availability means implemented software, conditional configuration or
permissions, or planned work. It does not claim that a feature is active on the
current installation. The read-only owner-scoped memory explorer, audio routes,
model-gateway enforcement and optional diagnostic reporting keep their actual
limits. Browsing help never activates them.

## Interactive explanations

Every feature has **Start interactive guide**. **Guide through these results**
starts a tour of the current search/filter results, including MSP topics. One
step contains the complete explanation of one feature, with a topic picker,
Previous/Next, NL/EN switch and a link back to the selected catalogue entry.

The guide highlights an actual visible control only in its mapped panel. Hidden,
role-restricted, embedded, background and planned capabilities keep their full
explanation and an explicit context notice instead of a fabricated spotlight.
MSP topics in WebUI explain that their controls belong to the separate cockpit.
Selecting a feature automatically opens its mapped panel and Settings section
through the existing access guards. Unsaved settings (including clarification choices), project/connection drafts
and open bot, memory or task editors prevent the guide from leaving that editor.
Settings section changes also respect pending edits. Collapsed navigation containers are
opened temporarily and restored when the topic changes or the guide closes.
If a control lives in a closed form or menu, the guide marks its audited entry
button and explains how to reach it. It never clicks feature buttons, opens a
secret, changes a setting, sends a message or runs a job. Truly conditional
features show concrete usage instructions instead of a generic missing-control
warning. Planned and cross-product topics keep their explicit availability notice.

The tooltip traps keyboard focus, blocks background clicks and shortcuts, and
restores focus on close. Its text scrolls independently, stays readable on narrow
screens and respects reduced motion. Pending Guida transitions cannot reopen a
closed tour. If Guida cannot load, the complete static explanation remains open.

`static/help-feature-targets.js` is the reviewed inert map from all WebUI feature
IDs to panels, settings sections and candidate selectors. Keep it in sync with
new controls. Empty targets are intentional when no exact parent-DOM hook exists.

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
  `a72b3b4fefcc1a9bd86c63455d664e0067fb9f13`. Refresh it from the cockpit's
  `apps/cockpit/frontend/public/feature-guide.json`; review the diff and rerun
  catalog/browser tests. There is no network import or shared runtime dependency.
* `docs/feature-guide-coverage.json`: concrete control mappings, supplemental
  dynamic-feature entries and the current composer command aliases. Equivalent
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

`tests/e2e/full/feature-interactive.spec.ts` additionally visits every current topic in
both languages, checks the full chat tour, individual/filtered starts, real
spotlights, missing targets, late-close cleanup, drafts, request isolation and
390/900/1440-pixel layouts.

Customer MSP self service is covered by `webui.msp.overview`, `webui.msp.tickets`,
`webui.msp.billing`, `webui.apps.availability`, `webui.apps.request` and
`webui.apps.support`. See [the customer MSP contract](customer-msp.md).

`tests/e2e/full/workspace-clarity.spec.ts` checks the short explanation's lazy-load
boundary, local bot filtering without network requests or lost drafts, mobile
search/detail navigation and a useful error state when connectors are unavailable.

`tests/e2e/full/guide-responsive-recovery.spec.ts` checks short phone and landscape
windows with expanded filters, footer reachability, independent desktop panes
and recovery from an empty search when crossing the mobile breakpoint.
