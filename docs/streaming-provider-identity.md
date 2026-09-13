# Named provider identity during streaming

The WebUI resolves a named custom provider before constructing an agent. Its
transport may use the generic `custom` provider together with the resolved
endpoint and credentials. The original resolved name is also passed through
the engine's existing `requested_provider` parameter when supported, allowing
engine policy to distinguish a remote router from a native inference server.

The session agent cache includes this name. Repeated turns on the same route
reuse their agent; switching between named routes rebuilds it even when model,
endpoint and credentials happen to match. Existing fallback and credential
refresh behavior remains responsible for runtime replacement. Older engines
without the constructor parameter retain their existing behavior.

This changes only agent construction and in-memory cache identity. It adds no
timeout policy, model changes, authentication changes, or transcript fields.
Native stream-worker tests cover constructor capture, ephemeral turns, cache
reuse, route switches, active fallback replacement, and older constructors.
Provider inference and production response times require separate validation.
