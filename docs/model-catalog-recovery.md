# Recovering a provisional model catalog

The model picker can render a usable static or previously cached list while the
existing provider catalog worker is still running. A nonempty list does not imply
that discovery is complete. The `/api/models` producer now adds the boolean
`refresh_pending: true` to those provisional response copies. The marker is not
written into the catalog cache and is absent after completion or a failed build
at the timeout boundary. Existing per-request governance filtering still applies
to every returned catalog.

The browser schedules one continuation at a time, one second after a provisional
response, with at most three additional requests and a 20-second deadline for the
continuation cycle. These are ordinary catalog GETs: they reuse the existing
worker/cache instead of forcing a rebuild or eagerly fetching each provider.
A completed response, HTTP failure, cancellation, newer request, or changed
profile generation ends the previous recovery. This includes an A-to-B-to-A
profile switch. The active provider's existing optional live enrichment is also
prevented from applying a late result to a different profile.

Each response reconciles against the currently loaded session or current picker
choice. The fresh-boot default preference is not replayed during recovery. This
preserves a deliberate model/provider selection, reasoning setting and composer
draft while the full list appears. There is no new setting or control. If a
provider remains unavailable beyond the bounded cycle, a later session visit or
Providers > Refresh Models can make a new catalog request; the existing refresh
toast acknowledges invalidation rather than successful remote discovery.

## Verification and limits

- Native backend tests gate the real detached worker and verify provisional
  static/stale copies, one shared rebuild, final publication and current
  governance filtering. Existing budget-boundary, cache-only and session-visit
  contracts remain covered.
- Real Chromium fixtures load the complete production `ui.js` with synthetic HTTP
  responses at desktop and narrow widths. They exercise recovery, route selection,
  draft/reasoning preservation, bounded retries, timeout/cancel/error paths,
  replacement and late profile responses. Network and WebSocket traffic outside
  the in-process fixture is refused.
- These hermetic fixtures do not prove a live provider is healthy or that an
  observed production catalog was incomplete for this particular reason. Live
  acceptance must verify the same selected route and the eventual model list in
  the signed-in browser without changing provider configuration.
