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
