# Run timing breakdown

The existing preparation milestones cannot distinguish module imports, waiting
for the environment lock, or MCP discovery. Likewise, `agent_ready` includes
construction and synchronous closure of evicted cached agents. Additive
`run_timing` journal records measure these actual boundaries without changing
their order, profile handling, toolsets, model, reasoning, timeouts or caching.

Each record contains only a fixed `stage`, monotonic `elapsed_ms` since worker
preparation began, `duration_ms`, and a fixed `outcome`. Stages are
`skill_modules`, `cron_wrapper`, `env_lock_wait`, `env_lock_hold`,
`mcp_discovery`, `agent_constructor`, `cache_eviction_close`, `agent_run`, and
`checkpoint_join`. No prompt, identity, file path, connector name, exception text
or evicted session identifier is copied. Existing preparation payloads are
unchanged. Records use the existing run-scoped journal and are not sent directly
to the live SSE queue or added to the transcript; journal replay can carry them
as an unhandled event type.

`completed` means the measured call returned, not that an answer, connection or
memory commit succeeded. `raised` preserves the original exception or
cancellation. MCP discovery additionally reports `skipped` for normal chat mode
and `unavailable` for its existing non-fatal exception path. A cache hit has no
constructor record. Each attempted stale/identity/LRU close gets a separate
record, without identifying the other session. These records are outside the
cache lock. Environment wait/hold records are written only after releasing the
environment lock; a failure inside that critical section may omit them.

`agent_run` ends when the foreground agent call returns, so its endpoint can be
compared with the last token timestamp. `checkpoint_join` measures the existing
join before normal response writeback, retaining its 15-second timeout. The
earlier cancelled/ephemeral exits and exception cleanup joins are deliberately
outside that normal-writeback measurement. Existing final-writeback diagnostics
remain unchanged. Missing timing records mean unavailable observations.

Journal write errors remain non-fatal. The fixed small number of records uses
the existing journal durability policy and does not add a background worker or
network request. Recording has some I/O overhead, which must be considered when
comparing live timings. This is instrumentation, not a claimed latency reduction
or proof of the cause of any previously observed delay.

Native regression coverage exercises actual isolated streaming and journal
readback, normal/super chat, MCP failure, governance refusal, cancellation,
journal failure, contended locking without journal I/O under the owned lock,
and separate slow construction/LRU closure. HTTPX requests are forbidden in the
new tests, including swallowed attempts. Live measurement remains separate.
