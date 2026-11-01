# Scout background execution

Scout settings are stored per bot and person. Enabling Scout creates or resumes
one job in that bot's native cron store. Its result belongs to that person's
private Scout conversation. A quiet run may deliberately return `[SILENT]`;
a failed run is not evidence that there is nothing useful to report.

Deployments that keep background profiles on a separate multiplex gateway can
set `webui.background_gateway_home` to its absolute home in the **root**
`config.yaml`. Leave it unset for ordinary native gateway discovery. This is an
operator setting; individual bots cannot choose another host.

When configured, enabling Scout verifies the private local gateway, registers
the existing bot through a profile symlink and requests a native hot rescan.
The gateway must report that it serves the exact canonical bot home before the
job is enabled. A collision, inaccessible gateway or parked profile returns an
actionable error and restores the previous Scout settings. Existing profile
links are never overwritten. A valid new link remains after a transient rescan
failure so the gateway's regular watcher and a later save can retry it safely.
No restart or competing per-profile daemon is started.

The engine must support discovering linked profiles through their live owner's
control socket. This preserves the profile's own identity, tool configuration,
credentials, cron store and user governance; the shared host only supplies the
execution process. Root-owned messaging credentials remain subject to the
existing adapter ownership checks.

Scout jobs leave `enabled_toolsets` unset. The engine's managed-Scout resolver
uses the bot's current CLI tool configuration on each run, including its enabled
MCP connections. A stored list would instead make every listed MCP a mandatory
dependency, so an unrelated unavailable connector could block all preparation.
Unavailable sources still need to be reported honestly; ordinary jobs with
explicit tool requirements retain their existing preflight checks. Saving an
existing Scout upgrades its stored tool selection to this inherited mode.

The collector records a pending attempt in the person's Scout ledger. Preparation,
topic and source-warning cooldowns advance only after its saved output confirms
an agent response (including a deliberate `[SILENT]`). A blocked, failed, missing
or script-gated run consumes no cooldown or item display budget. Items remain
available for retry, and only successful unclassified rounds count toward their
display limit. Old pending attempts release only cooldowns stamped by that exact
attempt. Deploy collector and ledger scripts together; saving a Scout installs
the current pair in its bot profile.

An explicit **Run now** always performs a preparation round, including during the
automatic retry cooldown. Automatic scheduled fires continue to debounce. The
server-owned cron trigger supplies this distinction; prompt text cannot change it.
The Scout must attempt necessary source checks before choosing `[SILENT]`, and
report a material source failure when it prevents reliable preparation.

CLI credentials must resolve in the background process's actual environment.
When a deployment uses the governed Workspace wrappers with central credentials,
configure their existing `GWS_DWD_SA_KEY` and `GMAIL_DWD_SA_KEY` references in the
authorized bot's secret scope and `terminal.env_passthrough`. Do not copy a
private key or replace the sandbox HOME with the administrator's HOME. Verify
read access as the job owner and denial for a mismatched bound identity. This
is an operator configuration choice for deployments using those wrappers, not
a requirement to connect Google accounts or grant other bots access.

To verify a deployment, enable a Scout, check its next scheduled run, trigger a
run and inspect the execution result and its private conversation. A successful
configuration save alone does not prove an agent ran or a result was delivered.

Regression coverage: `tests/test_bot_scout.py` checks idempotent enrollment and
that a host which does not serve the bot cannot leave an enabled job behind.
