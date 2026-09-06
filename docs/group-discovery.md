# Group conversations and discovery

People search refreshes the directory whenever the picker opens. A transient
directory failure is retryable and cannot pin an empty cached result forever.
Search folds accents for display names and email matching; stored email
identities remain unchanged. The signed-in person is excluded from their own
picker because the creator is already a member. Other people can find them.

An unavailable directory returns an explicit error. Adding participants fails
closed while membership cannot be validated: an invitation shares transcript
visibility, even though it grants no additional tool permissions.

Group reads and sends now use the same membership check. A group in another
Bot/profile is visible only to its explicitly named members who already have
permission to use that profile. Private conversations and isolated-profile
deployments preserve their profile boundary. The selected profile remains the
execution bot, and each human turn remains bound to that human's governance.
Groups use the governed in-process worker, including installations where
personal chats use a gateway backend.

Deployment should pin `HERMES_WEBUI_GOVERNANCE_POLICY` to the installation's
canonical policy path when profile workers change `HERMES_HOME`; otherwise a
directory request can temporarily resolve a different policy. This is a path
selection setting, not a grant or membership change.

Validation uses synthetic identities and no real invitations. Check directory
retry, accented search, a non-owner member sending, an unauthorized bot profile,
and an isolated-profile deployment. Real cross-user delivery requires a
separate authorized browser session; a creator's self-exclusion is not evidence
that colleagues cannot find them.


## Explicit bot participants

Persist `bot_participants` as up to six stable profile IDs independently of human email membership. The picker lists permitted profiles using bot presentation metadata; staged and saved groups preserve both kinds. With two or more bots, start the turn with `@profile-id`; one bot is an unambiguous default. Dispatch starts exactly one local governed worker. The conversation profile stays stable while the worker resolves the selected profile's model, SOUL/tools/MCP and profile-aware cache. Both request and worker recheck the original human sender's existing profile permission; group membership grants no tool permission. Runtime adapters and gateway backends cannot bypass this sender-bound path.

Each committed assistant turn receives server-selected `bot_profile` and `bot_name` metadata. Rendering uses this per-message identity and the guarded same-origin profile avatar endpoint after reload. Existing prior-turn authors are not overwritten. Autonomous bot fanout is intentionally not enabled; each human turn chooses one bot.

Validation: synthetic two-bot dispatch captures distinct execution profiles and original sender; serialization reload preserves both bot IDs; attribution preserves two sequential different authors. Directory tests include a non-Michael requester finding Michael and recovering from a failed initial directory response. The pre-existing cron-branch fixture returns403 on both clean71fbd228 and this change; it is not a group regression. No real colleagues were invited or messaged by these tests.
