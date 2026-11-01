# Dialog appearance

The shared dialog styles follow the active theme. Native dialogs retain their
centered position after the global CSS reset and scroll within short viewports.
App credentials, channel setup and rename/confirmation dialogs use the theme's
surface instead of a fixed light or dark gradient.

This also covers the project folder picker, conversation sections, scheduled-task
assignment, memory-access prompts and bot-screen confirmations. Filled form,
governance and guided-help buttons use a paired background/foreground through
`--sp-action-bg` and `--sp-on-action`. Their hover states preserve that pair.
Connection errors and warnings use theme colors instead of fixed pale text.

The checkpoint changes viewer now opens on its first invocation and displays
code against the theme's code surface. Opening or closing it does not restore
a checkpoint.

## Verification

```sh
node tests/frontend/dialog-readability.cjs
node tests/frontend/vault-dialog.cjs
```

Both use existing Playwright installations via `PLAYWRIGHT_MODULE_PATH` and an
optional Chromium executable via `CHROMIUM_PATH`. `SYNTHPULSE_QA_OUTPUT` saves
screenshots and the dialog audit report; `DIALOG_SOURCE` can select a baseline
checkout for the audit.

The audit runs the actual dialog renderers with fixture APIs, the real shared
prompt markup and bot-screen confirmation markup. It checks light and dark
themes at desktop, laptop, mobile and reduced mobile height. It measures text
contrast including gradient endpoints, checks primary-button hover states,
viewport bounds, first/repeated checkpoint opening and absence of writes when
opening or cancelling dialogs. The shared control-family samples cover page
forms, governance, guided-help buttons and connection feedback.

This is browser presentation coverage for the default SynthPulse light/dark
palettes, not a complete accessibility certification of all custom skins or
proof of live provider authentication. External requests are blocked and all
identities, credentials and checkpoint contents in the test are synthetic.
