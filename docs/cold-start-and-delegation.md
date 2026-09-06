# Cold-start metadata and delegated activity

Claude sidebar rows now use a disposable claude-sidebar-index.json in the configured WebUI state directory. Only bounded titles, message counts and timestamps are stored, with private file permissions. The source path, mtime, ctime, size and parser message limit must match before reuse. The current source scan still excludes symlinks and enforces file limits; removed sources disappear and permission/profile filters still run on each request. Corrupt or missing indexes fall back to parsing. Transcript details always read the original JSONL. This changes derived sidebar cache state only, never conversation history or execution state.

Startup begins model discovery and transcript projection independently. Runtime provider authorization and configured model selection remain authoritative.

Local chat and both gateway chat transports emit a journaled subagent SSE event for queued/running/completed/failed/cancelled activity. Its bounded fields are id, optional parent_id, status, task_index, task_count, tool_count, optional duration_seconds and a short redacted assignment summary. Child reasoning, generated prose, arguments and credentials are excluded. UI fallback rows use subagent_progress and subagent:<id>; they are presentation metadata, not synthetic engine tool calls. Older engines without this optional normalization capability continue without these extra events.

The existing delegation executor owns concurrency, cancellation and results. No automatic extra agents or API calls are introduced merely by emitting activity.


## Optional fast profile list

list_profiles_api(fast=True) returns fresh profile metadata while skill counts are deferred.
Unknown skill_count/enabled_skills/total_skills are null with skill_counts_pending=true;
clients must hide the count or show pending, never convert unknown to zero. One daemon worker
warms at most 256 queued profile scopes through the existing per-profile cache and locks.
Subsequent fast reads validate the existing mtime freshness before showing counts. The default
API and profile detail retain synchronous exact counts. Permission filtering remains per request
at the route, after list construction. Isolated mode constructs only its own profile.

Read-only isolated process measurement on this VPS, 20 actual profiles: default cold builder
5.183s (4.553s skill stats), optional fast cold list 0.500s with 20 pending counts; after the
single worker completed, fast list 0.873s with zero pending counts. These are backend projection
measurements, not browser end-to-end latency. Synthetic 200 transcript files/100,000 messages:
first build 0.398s, persistent-index projection 0.015s, equal sidebar rows (27.3x).
