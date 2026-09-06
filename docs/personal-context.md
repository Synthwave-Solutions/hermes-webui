# Personal context isolation

The Personal Memory API owns four actor-scoped documents: My Notes, User Profile,
personal Agent Soul preferences, and private Project Context. The authenticated
email is normalized and hashed into a server-generated directory under
`STATE_DIR/personal_context`. Selecting a bot, supplying an email/path/profile
override, or having an administrative role does not select another person's
documents. Missing identity fails closed. Chat access permits editing one's own
documents; it does not grant bot configuration access.

Project notes additionally use the explicit selected session's project ID, or
workspace when no project is selected. With no session, they are general personal
notes: there is no global workspace fallback. Shared project instructions are a
separate read-only field, resolved only for a selected authorized shared project,
with fresh file capability checks and bounded containment.

The browser worker binds the same private memory directory before constructing
an agent. MemoryStore captures it, including copied-context delegated workers,
and retains it after the parent context ends. Bot SOUL identity remains bot
configuration; personal preferences are a separate prompt overlay. Automatic
cwd/ancestor context discovery is disabled for these turns. Authenticated browser
turns use the local governed engine because the gateway transport does not yet
carry this private scope. Model/provider and tool authorization remain unchanged.

External memory plugins are not attached to private-scoped turns until they
provide a verified actor-isolation contract. Legacy bot MEMORY.md, USER.md,
SOUL.md and provider data are preserved in place and are not copied to users.
Historical transcripts and external provider records are not retroactively
rewritten or purged. Existing operators must review any intentional migration
explicitly, one owner at a time.

The private API and built-in memory tool reject symlink targets and parent
directories. This does not revoke separate host-administrator filesystem powers.
No private-context path is added to workspace or file-tool grants.


Shared projects and conversations with another human do not automatically load
personal notes, profiles or preferences. Their memory tool is unavailable, also
in delegated workers. They retain the bot persona and explicitly authorized
shared project instructions. Several bots in a single-human chat do not by
themselves make a conversation shared.


Generic host file tools and file APIs also reject another actor's private root,
and any private root in shared conversations. Recursive ancestor reads that
would include the private root are denied. Arbitrary privileged terminal code
and host administrators are not OS-sandboxed by this application-level policy;
dedicated process/filesystem isolation is a separate hardening requirement.
