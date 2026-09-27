import threading
from api import approvals, config, grant_requests


def test_admin_delivery_does_not_hold_registry_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'STATE_DIR', tmp_path)
    monkeypatch.setattr(grant_requests, '_load_spool', lambda: {
        'u|skill|example': {'email': 'u@example.test', 'gkind': 'skill', 'value': 'example'}
    })
    observed = []
    completed_during_delivery = []
    def deliver(entry):
        def reader():
            with approvals._REGISTRY_LOCK:
                observed.append(approvals.load()['grant:u|skill|example']['status'])
        worker = threading.Thread(target=reader)
        worker.start()
        worker.join(timeout=1)
        completed_during_delivery.append(not worker.is_alive())
        return True
    monkeypatch.setattr(grant_requests, '_notify_admins_of_request', deliver)
    assert grant_requests.ingest_spool() == 1
    # Since 09f09e2d (14 Sep 2026) the administrators are notified from the
    # automatic-review thread, after the reviewer leaves the row to them, so
    # wait for that thread instead of expecting a synchronous call.
    import time
    deadline = time.monotonic() + 5
    while not completed_during_delivery and time.monotonic() < deadline:
        time.sleep(0.02)
    assert completed_during_delivery == [True]
    assert observed == ['pending'], 'External delivery must not block registry readers/decisions'
