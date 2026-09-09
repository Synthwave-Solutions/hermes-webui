# Separately reviewed Linux replay operator

`run_vps_failed21_reviewed.py` is a task-specific operator for an explicitly invoked disposable Linux diagnostic replay. It is not imported or executed by the application or the225-case browser suite. It must run in its own verified user unit, requires frozen7b/b0 QA checkouts, and selects exactly21 historical failures with unchanged assertions and deadlines. Its result cannot replace the failed224 full run or establish all Linux coverage.

Operator SHA256: `b538d359ae149276445e7181a86e5bab410d79f376aa783f0d500bba0da08d25`. Independent source/selection checks are separate from browser acceptance. No credentials, raw traces or production task data are included. See the delivered QA evidence for actual outcomes and process-cleanup scope.
