# Configure a bot before creating it

New bots open a four-step draft: identity and photo, system instructions and
skills, MCP connections and CLI tools, then allowed users/groups and review.
No creation request is sent before the last step. Available choices come from
the authenticated builder catalog; credentials are never displayed. Existing
bots use the same editor with their configuration revision. System instructions
belong to the bot, independently of personal Memory.

The browser accepts PNG, JPEG and WebP photos up to 10 MB and resizes them to
a PNG at most 512 pixels wide or high before upload. The server retains its
own image validation and size limit. Upload progress and errors remain visible;
successful updates refresh the current photo and chat roster. The same file
can be selected again after a failed upload.

The backend remains authoritative for ownership, access and revision checks.
A failed save keeps the draft available for correction.

## Browser regression

Run `node tests/bot_builder_browser.cjs` with Playwright installed. Set
`PLAYWRIGHT_MODULE` or `CHROMIUM_PATH` when using an existing local runtime.
The synthetic catalog fixture checks all four steps, selected capabilities,
photo conversion, no early creation request and a 390-pixel viewport.
Backend tests separately verify persistence and access enforcement.
