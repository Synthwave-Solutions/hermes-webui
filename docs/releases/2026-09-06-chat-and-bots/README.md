# SynPulse chat and bot setup release

Release date: 6 September 2026. Publication and runtime verification are recorded in `qa-report.md`.

## Everyday use

- Choose **Chat** or **Super agent** at the top of a conversation. The selected mode is saved with the chat. A pending change visibly disables both buttons until the server responds.
- Choose a bot from the avatar row above the composer. In a personal chat this opens that bot's conversation. In a group chat it addresses the next message to that bot with `@bot-id`.
- Use the microphone for dictation and the circular waveform for realtime voice. Connections uses a plug; My approvals uses a shield/check. Ordinary voice messages describe service availability without provider configuration details.
- Open **Personal memory** for your own notes, user profile, personal agent preferences and project notes. Bot instructions and shared project instructions are separate from these personal documents.
- Open **Bots → Create a bot**. Complete Identity & photo, Instructions & skills, Connections & tools, then Access & review. Nothing is created until the final save.
- Upload a PNG, JPEG or WebP photo. The browser resizes it before saving; the editor and chat avatar row refresh after a successful upload.

## Technical design

The UI keeps bot identities stable. Display names and photos do not change the underlying bot ID. The chat roster is populated from the authenticated, filtered profile endpoint. Group recipients must be assigned to the conversation and accessible to the sender; the worker checks access again before execution.

Personal context is keyed by a hash of the authenticated identity, never an identity supplied in a request body. Project notes are additionally scoped to the selected authorized project or session workspace. A private turn binds this context for the full worker lifecycle, including memory writes. Shared conversations exclude personal context and the personal memory tool. Generic file routes reject access to another user's personal context storage, including resolved symlink and escaped-path variants.

Existing shared memory files are preserved and are not copied into every user's private memory. Administrators should review historic bot instructions for personal information before using those bots in shared chats. This is application-level isolation; it is not an operating-system sandbox against a host administrator or an independently privileged terminal tool.

The bot builder uses one revision-checked configuration endpoint for creation and editing. The final save validates instructions, selected skills, MCP connections, CLI tools and allowed people/groups together. New managed bots are private to their creator unless explicitly shared. Bootstrap administrators can edit their own bots through the same ownership checks; bootstrap status does not grant access to another person's private context. The legacy Gateway route remains available when authentication is explicitly disabled.

A bot's selected capabilities remain a ceiling on the human sender's current permissions, including after approval and when delegating work.

The bot roster shows loading immediately while chat history loads. Profile identity and chat enumeration skip unnecessary skill counts, and bot selection waits for the correct profile to finish loading.

Terminal errors are persisted as authoritative run outcomes and remain visible after reload. Late events from an older run cannot overwrite the current run's state.

## Interaction reference

The coworker/agent selection and channel concepts were reviewed in [CopilotKit OpenBot](https://github.com/CopilotKit/OpenBot/blob/main/README.md). SynPulse retains its own authenticated multi-user access checks and existing group-chat runtime.

## Deployment

Promote the paired engine and WebUI changes through dev, staging, then the repository's production branch (engine `main`, WebUI `master`). Record exact promoted commits and check both services after deployment. Stop and restart runtime services only after the active-run and active-stream guards report idle. Keep previous commit IDs available for a reviewed rollback.

Automated regression checks and isolated browser evidence do not prove a successful microphone or external speech-provider roundtrip. Report those separately.
