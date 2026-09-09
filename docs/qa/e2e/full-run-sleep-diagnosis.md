# Full-run timeout diagnosis

Run: `supplement-final-runs/20260909-101110-65363000`; frozen WebUI `0ded200599bb0f12a891c87ea9762eab40cf7791`. Original result remains **217 passed / 2 failed**; this note does not replace that receipt or convert either failed assertion into a pass.

Read-only trace and macOS power-log correlation on 2026-09-09 (Europe/Amsterdam, UTC+02:00):

| Evidence | Time / interval | Meaning |
| --- | --- | --- |
| macOS `pmset -g log` | 10:19:57 Clamshell Sleep, duration126s; 10:22:03 DarkWake | Host suspended while the bot-editor test started. |
| Bot trace | route.continue starts527045ms and completes650962ms; page.goto completes651014ms | Browser trace has123.9s without events during the initial navigation. |
| Bot first navigation click | starts651142ms and is aborted by651473ms | The90s test deadline already elapsed before this click; the log does not demonstrate a90s Bots handler hang. |
| macOS `pmset -g log` | 10:22:48 Maintenance Sleep, duration48s; 10:23:36 lid/HID Wake | Host suspended a second time. |
| Delayed-outline Send trace | events stop697887ms and resume744164ms | The46.28s gap covers a10s actionability deadline; three normal stability checks occurred before suspension. |

The two trace gaps align with the two actual sleep intervals. This supports host suspension as the cause of these timeout outcomes. It does not establish that every possible application race is absent. The unchanged cases and their preceding scenarios should be replayed on an awake host with the same assertions and deadlines, then a fresh unchanged full run should supply the final acceptance result. No source edits, forced clicks, timeout increases, test retries, or failed-result suppression are justified by this evidence.

A temporary `caffeinate -i` assertion can prevent idle sleep during the runner. It is not a guarantee against lid-close sleep; keep the Mac lid open for the run. Do not change global power settings. Only the selected power transition records were used; no application state, credentials, or unrelated power-log details are exported here.

Unchanged focused replay: `supplement-runs/20260909-103316-53593000`, all3 project/knowledge tests PASS, runner exit0, source unchanged, each uncaught-browser-errors attachment empty. The previously interrupted concurrent-editor case completed in4.2s; the preceding cases completed in11.9s and6.4s. The run used the original test deadlines and normal clicks with temporary `caffeinate -i`. Playwright emitted its previously observed secondary-context step-ID reporter warnings; these are preserved in the raw receipt and are not app page exceptions. A fresh full run remains the final acceptance authority.
