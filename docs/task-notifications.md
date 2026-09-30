# Notifications per scheduled task

Open **Scheduled tasks**, select a task, and click **Notifications → Enabled / Disabled**
in its details. The change saves immediately. The same setting is available when
creating or editing a task.

This controls completion pop-ups in the WebUI for that task. Turning notifications
off does not pause the task, change its schedule, suppress its output delivery,
or clear unread badges. Open the task's results to inspect completed runs.
The setting belongs to the task, so it applies to everyone receiving that task's
completion pop-ups. Existing tasks default to enabled. Normal task edit
permissions still apply; tasks shown as read-only have a disabled control.

While saving, the button is disabled. A failed save shows an error and retains
the last confirmed state. A late response cannot change another selected task
or profile. Refresh the task after a connection failure if the server may have
received the update.

Verification:

- `./scripts/test.sh tests/test_cron_toast_notifications.py tests/test_scheduled_jobs_scope.py tests/test_cron_editor_validation.py`
- `node tests/cron_notifications_browser.cjs`
- `npm run lint:runtime`

The browser fixture uses the actual detail renderer, toggle handler, and
completion poller with an isolated API stub. It exercises task isolation,
keyboard use, save errors, pending writes, late responses, read-only tasks,
muted pop-ups, and retained unread markers at desktop and mobile widths.
It does not send real task notifications or run scheduled jobs.
