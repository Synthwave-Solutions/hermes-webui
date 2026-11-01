# Scout background execution

Scout settings are stored per bot and person. Enabling Scout creates or resumes
one job in that bot's native cron store. Its result belongs to that person's
private Scout conversation. A quiet run may deliberately return `[SILENT]`;
a failed run is not evidence that there is nothing useful to report.

Private conversations show the Scout's advice and prepared material. Its internal
`SCOUT-LEDGER` and `SCOUT-WEB` lines stay in the native run output for the next
collector round; the delivery bridge removes those lines from chat messages.

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

For native agent runs whose execution profile is also their owning cron store,
**Run now** creates one native execution record before spawning its worker. The
child adopts that record and uses the native output, delivery queue and terminal
bookkeeping with the same execution ID. Receipt reconciliation leaves a live
owner alone and recovers an interrupted child; the WebUI parent accepts an
explicit, verified native completion instead of saving and delivering again.
A lost child reply cannot overwrite a completed run. Older engines and script
jobs retain their existing manual path. The separate execution-profile/store
compatibility path also stays unchanged: native receipt recovery currently
assumes those homes coincide, so this lifecycle guarantee does not cover that
split. Scout jobs use one bot home for both roles.

CLI credentials must resolve in the background process's actual environment.
When a deployment uses the governed Workspace wrappers with central credentials,
configure their existing `GWS_DWD_SA_KEY` and `GMAIL_DWD_SA_KEY` references in the
authorized bot's secret scope and `terminal.env_passthrough`. Do not copy a
private key or replace the sandbox HOME with the administrator's HOME. Verify
read access as the job owner and denial for a mismatched bound identity. This
is an operator configuration choice for deployments using those wrappers, not
a requirement to connect Google accounts or grant other bots access.

An isolated gateway `HOME` also changes governance and login-shell resolution.
For installations using the Synthwave policy plugin, point its existing
`SYNTHWAVE_POLICY_ROOT` setting at the authoritative installation root, or link
the gateway's `policy` directory to that existing central policy directory.
Preserve the enforce markers, rules and profile-specific restrictions. A missing
policy under a home that was previously enforced correctly refuses every tool;
removing the marker or changing the mode is not a deployment repair.

Policy source changes also need to be installed for the intended profiles with
`deploy/synthwave-policy/install.sh`, followed by a gateway reload or restart.
Verify that the installed plugin matches the reviewed source; updating only the
engine checkout leaves already-installed policy copies unchanged.

Keep approved CLI directories in that gateway HOME's login-shell initialization
(for example its `.profile`, or configured `terminal.shell_init_files`). The
service's `PATH` alone is insufficient: a login-shell snapshot can replace it.
Use absolute installed CLI directories and preserve the isolated HOME. Do not
source an administrator's whole shell configuration or copy credentials to fix
command discovery. Verify this with a fresh native terminal backend, not just a
direct subprocess: resolve the CLI names, read a source as the owner, and check
that an unrelated bound identity remains denied. Confirm that legitimate reads
pass the existing policy and policy-tampering attempts remain blocked.

Verify MCP launchers in the gateway's selected Python environment and bound bot
profile. A maintenance interpreter can report Node/npm installed while the live
profile resolves a different tool store. Provision the missing locked toolchain
through an explicit `hermes pm install npm` in that runtime; do not enable
unrestricted lazy installation to hide the missing dependency. Check the
configured servers with native `hermes mcp test` and confirm an actual authorized
source read as well as tool discovery. Reload their connections after repair.

External CLI wrappers must resolve their installed program and credential-file
paths independently of a sandbox `HOME`. Keep the existing authorized credential
reference and isolated HOME; do not copy keys or broaden bot grants. Missing
provider permissions remain a separate issue: for example, Workspace Tasks
reads need an authorized Tasks scope. A rejected scope requires the Workspace
administrator's authorization, not a governance bypass or a silent Scout run.

To verify a deployment, enable a Scout, check its next scheduled run, trigger a
run and inspect the execution result and its private conversation. A successful
configuration save alone does not prove an agent ran or a result was delivered.

Regression coverage: `tests/test_bot_scout.py` checks idempotent enrollment and
that a host which does not serve the bot cannot leave an enabled job behind.
`tests/test_cron_manual_native_lifecycle.py` exercises native receipt recovery,
one completion and one delivery, including a crashed child and a lost reply.
