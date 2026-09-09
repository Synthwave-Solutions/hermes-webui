# Public conversation snapshots

Share explicitly publishes the selected conversation at an unpredictable public
link. Anyone with the link can read its snapshot without signing in. New chat
messages do not appear until the owner chooses **Refresh snapshot**. **Stop
sharing** makes both the page and its data endpoint return 404; the original
conversation stays private and remains available to its authorized members.

Creating, refreshing and revoking require authenticated `sessions:write` access,
the source conversation's profile and workspace authorization, and ownership or
administrative access. A group participant's ability to read and write the chat
does not permit publication. Browser mutations retain CSRF protection. An owner
who loses source access needs an authorized bootstrap administrator to revoke
the existing snapshot; revocation does not bypass the source access checks.

The existing share sanitizer publishes only the title and user/assistant text,
with always-on credential and known local-path redaction. System messages, raw
tool payloads, provider diagnostics and session configuration are excluded.
Explicit local image references may embed permitted PNG/JPEG/GIF/WebP files up
to 512 KiB; these image bytes are published as images, not text-redacted.
Source-session attachments and otherwise authorized workspace images can be
included. Other conversations' attachments, private personal context and denied
files are omitted. Image reads use the existing anchored file-open helper.

Snapshots live in `STATE_DIR/shares`; source session metadata retains the link
for reload and revocation. Tokens are bound to their source session, and imported
or stale metadata cannot overwrite another share or reactivate a revoked URL.
Public responses are uncached, excluded from indexing and use `no-referrer`.

Verification covers real frontend create/read/refresh/cancel/revoke, anonymous
and cross-origin mutation denial, group ownership, source-profile ACLs, image
privacy and failed-persistence rollback using disposable synthetic state.
