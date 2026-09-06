# Artifact download delivery

Workspace and generated chat download links fetch the authenticated response before starting a browser download. The browser saves a Blob snapshot of those bytes using the displayed filename. A missing file, denied access, redirect to login, timeout or failed transfer produces an in-app error with recovery guidance, instead of starting a known-broken browser download. The control remains available to retry after access is restored or the artifact is regenerated.

An explicit `download=1` takes precedence over inline preview for media and raw HTML endpoints. Existing file authorization and containment checks still apply. This does not recover deleted historical artifacts, provide durable server-side artifact versioning, or prove the browser saved the file to disk. A successful response only proves that bytes were handed to the browser.

Manual verification: download generated HTML and PNG through chat and workspace at desktop and narrow widths; verify saved filename and bytes. Repeat after removing the fixture and while signed out: no browser download should start, and the app must explain recovery. Repeat the successful save in supported browsers.
