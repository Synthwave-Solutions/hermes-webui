# Artifact download delivery

Workspace and generated chat download links fetch the authenticated response before starting a browser download. The browser saves a Blob snapshot of those bytes using the server's filename, including UTF-8 names with spaces. This preserves file extensions when a chat image has a friendly caption. A missing file, denied access, redirect to login, timeout or failed transfer produces an in-app error with recovery guidance, instead of starting a known-broken browser download. The control remains available to retry after access is restored or the artifact is regenerated.

All three authenticated download endpoints (`/api/media`, `/api/file/raw` and `/api/escape/file/raw`) return `Content-Disposition: attachment` for `download=1`. The client requires that response contract before saving bytes, so an HTTP 200 login or proxy error page without attachment disposition cannot masquerade as the requested document. HTML artifacts remain downloadable with their normal attachment header. A 404 specifically explains that the agent must regenerate and attach a new file; retrying the old link cannot reconstruct deleted bytes.

An explicit `download=1` takes precedence over inline preview for media and raw HTML endpoints. Existing file authorization and containment checks still apply. This does not recover deleted historical artifacts, provide durable server-side artifact versioning, or prove the browser saved the file to disk. A successful response only proves that bytes were handed to the browser.

Manual verification: download generated HTML and PNG through chat and workspace at desktop and narrow widths; verify saved filename and bytes. Repeat after removing the fixture and while signed out: no browser download should start, and the app must explain recovery. Repeat the successful save in supported browsers.

## Isolated download regression fixture

Run `node scripts/test-artifact-download-browser.cjs --serve-only` and open the printed loopback URL with your browser testing tool. The fixture loads the actual `static/workspace.js`, uses a fixture-only cookie, and offers HTML/PDF/PNG/ZIP downloads, workspace/external download buttons, and explicit missing, denied, login, redirect and network error scenarios. Save the files and compare their names and bytes with the fixture definitions. Use 1440px and 390px viewports for the recovery text. Stop the fixture process when finished.

For CI with Playwright already installed, run the script without `--serve-only`; it asserts saved filenames/bytes and error handling in both viewports. Set `ARTIFACT_QA_BROWSER` to an installed `chromium`, `firefox` or `webkit` engine, and `ARTIFACT_QA_OUTPUT` to retain evidence. It creates no production sessions and contacts only loopback. The fixture tests frontend delivery with small synthetic byte payloads; it does not prove PDF/image rendering or real provider generation. The Python endpoint regressions separately verify the existing backend's disposition, MIME and byte contract for all three download endpoints. Production permissions and historical missing-file recovery require separate verification.

## Assistant delivery syntax

The WebUI's per-turn instructions ask the assistant to verify a requested file and include its attachment or preview in the visible reply. A standalone `MEDIA:/absolute/path/to/report.pdf` token renders supported media inline; other file types, such as ZIP or DOCX, become download attachments. Use the real tool-reported artifact path, not a guessed host equivalent of a container path. A friendly filename and brief description identify the deliverable without exposing implementation paths in prose.

For a path with spaces, use a file URI such as `MEDIA:file:///absolute/path/to/Quarterly%20Report.pdf`. Keep the token outside code formatting. For an existing workspace file, `[Open report](workspace://outputs/Quarterly%20Report.pdf)` opens the workspace preview using a path relative to the current workspace. A bare `workspace://` string is not a clickable link. These examples describe existing rendering syntax; they do not create files or grant access.

The guidance is assembled through `api.streaming._webui_ephemeral_system_prompt` on each governed WebUI turn, including turns that reuse an agent. It does not modify profile instructions, session history, or cache state. Tests execute the prompt builder and render its examples with the actual JavaScript renderer; model compliance and browser download completion require separate evidence.
