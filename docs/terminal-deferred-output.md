# Completed output in deferred tool cards

A reconciled chat row can keep its DOM identity while a newer tool snapshot
replaces its HTML. The deferred detail snapshot must move with the ordinary
tool data before restoring an expanded card. Otherwise a pending snapshot can
materialize a command-only body even though the completed result is available.

The shared row rehydration now transfers or clears that deferred snapshot.
Completed results still pass through the existing `buildToolCard` escaping,
preview limits and error rendering. Output selection and expanded state remain
preserved. No tool result, session, model transcript or permission is changed.

The regression exercises replacement, clearing and null deferred state before
opening. `tests/terminal_deferred_output_fixture.py` additionally serves a local
synthetic DOM fixture using the actual renderer, row refresh and materialization
functions. Check collapsed completion then opening; Output selected before
completion; repeated completion; an escaped failed result; and replacement by
a detail-less result. No provider call is needed for that fixture.
