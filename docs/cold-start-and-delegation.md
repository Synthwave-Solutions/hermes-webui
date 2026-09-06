# Cold-start metadata and delegated activity

Claude sidebar rows now use a disposable claude-sidebar-index.json in the configured WebUI state directory. Only bounded titles, message counts and timestamps are stored, with private file permissions. The source path, mtime, ctime, size and parser message limit must match before reuse. The current source scan still excludes symlinks and enforces file limits; removed sources disappear and permission/profile filters still run on each request. Corrupt or missing indexes fall back to parsing. Transcript details always read the original JSONL. This changes derived sidebar cache state only, never conversation history or execution state.

Startup begins model discovery and transcript projection independently. Runtime provider authorization and configured model selection remain authoritative.

Local chat and both gateway chat transports emit a journaled subagent SSE event for queued/running/completed/failed/cancelled activity. Its bounded fields are id, optional parent_id, status, task_index, task_count, tool_count, optional duration_seconds and a short redacted assignment summary. Child reasoning, generated prose, arguments and credentials are excluded. UI fallback rows use subagent_progress and subagent:<id>; they are presentation metadata, not synthetic engine tool calls. Older engines without this optional normalization capability continue without these extra events.

The existing delegation executor owns concurrency, cancellation and results. No automatic extra agents or API calls are introduced merely by emitting activity.
