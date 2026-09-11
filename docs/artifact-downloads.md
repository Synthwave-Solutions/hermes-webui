# Artifact download delivery

Workspace and generated chat download links fetch the authenticated response before starting a browser download. The browser saves a Blob snapshot of those bytes using the displayed filename. A missing file, denied access, redirect to login, timeout or failed transfer produces an in-app error with recovery guidance, instead of starting a known-broken browser download. The control remains available to retry after access is restored or the artifact is regenerated.

An explicit `download=1` takes precedence over inline preview for media and raw HTML endpoints. Existing file authorization and containment checks still apply. This does not recover deleted historical artifacts, provide durable server-side artifact versioning, or prove the browser saved the file to disk. A successful response only proves that bytes were handed to the browser.

Manual verification: download generated HTML and PNG through chat and workspace at desktop and narrow widths; verify saved filename and bytes. Repeat after removing the fixture and while signed out: no browser download should start, and the app must explain recovery. Repeat the successful save in supported browsers.

## Assistant delivery syntax

The WebUI's per-turn instructions ask the assistant to verify a requested file and include its attachment or preview in the visible reply. A standalone `MEDIA:/absolute/path/to/report.pdf` token renders supported media inline; other file types, such as ZIP or DOCX, become download attachments. Use the real tool-reported artifact path, not a guessed host equivalent of a container path. A friendly filename and brief description identify the deliverable without exposing implementation paths in prose.

For a path with spaces, use a file URI such as `MEDIA:file:///absolute/path/to/Quarterly%20Report.pdf`. Keep the token outside code formatting. For an existing workspace file, `[Open report](workspace://outputs/Quarterly%20Report.pdf)` opens the workspace preview using a path relative to the current workspace. A bare `workspace://` string is not a clickable link. These examples describe existing rendering syntax; they do not create files or grant access.

The guidance is assembled through `api.streaming._webui_ephemeral_system_prompt` on each governed WebUI turn, including turns that reuse an agent. It does not modify profile instructions, session history, or cache state. Tests execute the prompt builder and render its examples with the actual JavaScript renderer; model compliance and browser download completion require separate evidence.
