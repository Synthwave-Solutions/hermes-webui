# Feature tour target audit

`static/help-feature-targets.js` exports a deeply frozen `window.SynthPulseFeatureTargets` object. It covers all 302 WebUI feature IDs in `help-features.js`. Each record contains a real `panel`, an optional Settings `section`, and an ordered array of candidate CSS `targets`. Optional `entryTargets` and bilingual `entryHint` distinguish a prerequisite entry from the actual feature control. They are considered only when no exact target is visible, and the hint must explicitly say what the highlight represents and how to reach the feature. These are inert navigation hints, not permission grants or evidence that a control is currently visible.

There are 271 records with exact candidate targets, 55 records with prerequisite entry hints, and 27 records without either kind of hook. The tour controller must check the current panel, current Settings section, actual element visibility and existing access rules before highlighting anything. Hidden native inputs, lazy content, unopened dialogs, missing data, responsive controls and role restrictions can all prevent a candidate from being available. Safe panel/section navigation and opening native disclosure containers may expose an exact target. Never click an action control, populate a field or submit a form to make a target appear. An entry target only points out a next step; it does not open that entry or claim the inner field is already visible.

## Navigation contexts

| Panel | Features |
| --- | ---: |
| chat | 77 |
| apps | 27 |
| settings | 98 |
| tasks | 15 |
| workspaces | 2 |
| kanban | 12 |
| memory | 25 |
| skills | 4 |
| profiles | 12 |
| projects | 5 |
| integrations | 6 |
| approvals | 1 |
| governance | 11 |
| logs | 1 |
| insights | 1 |
| modules | 5 |

Kanban has a real `panelKanban` and `switchPanel('kanban')` context even when no `data-panel="kanban"` navigation tab is present. The map does not add an entitlement or navigation tab.

Settings section IDs use the existing `switchSettingsSection` contract. Mapped counts are: `help` 3, `conversation` 5, `system` 15, `access` 1, `extensions` 3, `appearance` 21, `preferences` 49 and `providers` 1. The existing `plugins` section has no feature in this catalogue. Settings navigation may be refused or redirected by capability checks; callers must check the resulting section. A Settings call made while another panel is active can merely remember section state.

Conversation exports, imports, sharing and clearing are in Settings / Conversation. Capacity alerts, updates and MCP configuration are in Settings / System. OAuth configuration is in Providers, extension inventory in Extensions, and auxiliary or advanced model settings in Preferences. Theme, skin and font size point at their visible picker grids. Default model prefers the visible model chip over its native select.

## Chat coverage

Use the mapped panel to build a page tour, rather than only catalogue area `chat`. Chat has 77 applicable features across areas: composer sending, model and reasoning controls, people and groups, tool and context controls, attachments, saved prompts, mentions and slash commands; voice dictation, loop, realtime and message readout; bot selection; session creation, search and split; workspace selection and file browsing; individual approval choices and clarification; and relevant global controls.

Some controls are conditional. Message copy, edit and speech need an existing suitable message; edit, retry and fork use stable `data-help-action` hooks on the existing message action buttons. The edit textarea remains a secondary target after the user opens it. Slash commands target the real composer, not invented command buttons. Bot creation uses its existing entry button; detailed bot fields appear only after the user opens the builder. Module details target the actual explanatory summary or metadata container, not an inferred enable/purchase action.

## Explanatory fallback

The remaining absent exact hooks are intentional:

- Chat undo and replay have no rendered, sufficiently specific stable parent-DOM hook in this map. The undo button is constructed in the renderer but not inserted into the current footer.
- Session rename, pin, move, archive, delete, title regeneration and link use dynamically composed menus without stable per-action hooks. Their prerequisite entries point at the action-menu trigger or the closed chat-sidebar entry with an explicit explanation. The separate organize feature targets the menu trigger itself. No positional selector guesses an action.
- Memory identity has no unique parent control; search and the detailed explorer pages run inside an opaque sandboxed iframe. Their internal overview, today, visualiser, review, profile, lifecycle, graph, triples, recall, timeline, consolidations, structured overview, facts, structured timelines, instructions, structured graph and preferences controls cannot be queried from the parent document.
- Organisation governance, integration approval and operation errors have no exact grounded target here.
- Planned gateway, reporter and central memory describe planned capability and deliberately claim no current control.

An empty list means no audited exact target in this context. It does not mean that a feature lacks a UI or can never become available. The complete bilingual explanation remains accessible.

## Verification

`tests/test_help_feature_targets.py` checks exact catalogue coverage, supported panel and section names, existing application selector references, correct static Settings ancestors, cross-area Chat coverage, intentional iframe/planned fallback, and the deeply frozen, string-only browser export. It excludes help documents from selector source evidence so a fabricated selector in the guide cannot validate itself.

The tests prove metadata structure and source grounding. They do not prove a candidate is visible for every account or state. Browser integration and responsive runtime visibility are owned by the tour controller tests. The map contains no callback, executable action, network URL, automatic click or iframe traversal. Both selector arrays and the bilingual hint object are frozen.

## Prerequisite entry audit

- Mobile composer options use `composerMobileConfigBtn`; `ui.js` opens `composerMobileConfigPanel` from that button. Desktop controls remain the exact targets.
- Closed chat sidebars use the hamburger on mobile and the Chat rail icon on desktop; `switchPanel` only expands the collapsed sidebar for an actual rail click. `railExpandToggle` changes labels and must not be used as a sidebar-opening substitute.
- Agent-task form fields, including notifications, point to `data-tour="tasks-new"`. Notifications are rendered unconditionally by `_cronNotifyFieldsetHtml` in the creation form. The script path is different: New task creates an agent task, so a script explanation points only to an existing script-task row or its actual script card. Results target `cronDetailRuns` and use a task row as their prerequisite, never the generic refresh button. Task run/pause/edit/share point to a non-read-only `.cron-item`, whose real handler opens the selected task details. The guide never chooses or operates a task.
- Workspace controls use the actual files-panel toggles. File preview/actions can first point to a real file row; hidden-file preferences first point to `btnWorkspacePrefs`. `ui.js` creates `data-ws-type` on file rows and `workspace.js` owns the preview.
- Bot fields point to their actual `data-builder-tab` value when the editor is open, otherwise to a selectable `.profile-card[data-name]`. The description includes the configuration step before the tab. No bot is selected, created or saved automatically.
- Wiki search points to the existing `.wiki-browse-btn` when its browser overlay is closed.

Approvals, media output, active voice controls, restricted configuration, empty collections and opaque iframe pages still require their real state. No generic page, help button or unrelated control stands in for a missing feature.

## Apps directory

Apps has its own panel and 29 dedicated topics: overview, search, categories, language and
all 22 audited app entries. The legacy `webui.modules.apps` deep link also opens
the Apps overview. Each app points at its actual `data-app-id` card, including
intentional unconfigured cards. When starting a named app explanation, the tour
uses the directory's presentation-only `reveal(id)` API to clear filters and
reveal the permitted card; it does not open the external application. A returned
cleanup function is called on step changes, close or a cancelled preparation.
Cards omitted by server authorization are never recreated by the guide.
