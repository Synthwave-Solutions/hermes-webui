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

To verify a deployment, enable a Scout, check its next scheduled run, trigger a
run and inspect the execution result and its private conversation. A successful
configuration save alone does not prove an agent ran or a result was delivered.

Regression coverage: `tests/test_bot_scout.py` checks idempotent enrollment and
that a host which does not serve the bot cannot leave an enabled job behind.
