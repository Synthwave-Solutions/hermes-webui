"""The interim reader at HQ (addendum 6.6.7, decision D75).

Read only (``mode=ro``, never ``immutable``), registry paths only, never
blocking the writer, bounded in time and file descriptors, off unless the
policy says HQ and no hub URL is set; every change answers 503.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "memdash"))

import memdash_harness as H  # noqa: E402
from api import memdash_backend as backends  # noqa: E402
from api import memdash_registry as registry  # noqa: E402
from api.third_party import mnemosyne_dashboard as md  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def env(monkeypatch, tmp_path):
    environment = H.Env(monkeypatch, tmp_path)
    yield environment
    environment.close()


def _digest_tree(root: Path) -> dict[str, str]:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("mnemosyne.db"))}


def test_connections_are_mode_ro_query_only_and_never_immutable(tmp_path, monkeypatch):
    bank = H.make_bank(tmp_path / "bank" / "mnemosyne.db", owner="probe")
    seen = []
    real_connect = sqlite3.connect

    def spy(database, *args, **kwargs):
        seen.append((str(database), kwargs.get("uri")))
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr(md.patches.sqlite3, "connect", spy)
    md.allow_paths([bank])
    try:
        store = md.DashboardStore(bank)
        assert store.stats()["counts"]["working_memory"] == 3
        with store.connect() as con:
            with pytest.raises(sqlite3.OperationalError):
                con.execute("DELETE FROM working_memory")
    finally:
        md.allow_paths([])
    assert seen and all(uri is True and db.endswith("?mode=ro") and "immutable" not in db for db, uri in seen)
    for path in (REPO / "api" / "third_party" / "mnemosyne_dashboard" / "patches.py", REPO / "api" / "memdash_reader.py"):
        assert "immutable=1" not in path.read_text(encoding="utf-8")


def test_connections_are_closed_after_each_view(tmp_path):
    bank = H.make_bank(tmp_path / "bank" / "mnemosyne.db", owner="probe")
    md.allow_paths([bank])
    try:
        store = md.DashboardStore(bank)
        con = store.connect()
        with con:
            con.execute("SELECT 1")
        with pytest.raises(sqlite3.ProgrammingError):
            con.execute("SELECT 1")
    finally:
        md.allow_paths([])


def test_a_store_without_a_path_or_outside_the_allowlist_is_refused(tmp_path):
    bank = H.make_bank(tmp_path / "bank" / "mnemosyne.db", owner="probe")
    other = H.make_bank(tmp_path / "other" / "mnemosyne.db", owner="other")
    with pytest.raises(PermissionError):
        md.DashboardStore()
    with pytest.raises(PermissionError):
        md.DashboardStore("")
    md.allow_paths([bank])
    try:
        with pytest.raises(PermissionError):
            md.DashboardStore(other).stats()
        link = tmp_path / "link.db"
        link.symlink_to(other)
        with pytest.raises(PermissionError):
            md.DashboardStore(link).stats()  # the symlink resolves outside the allowlist
    finally:
        md.allow_paths([])


def test_registry_paths_only_symlinks_and_paths_outside_the_roots_are_refused(env, tmp_path):
    outside = H.make_bank(tmp_path / "outside" / "mnemosyne.db", owner="outside")
    evil = env.hq.data / "banks" / "u-evil"
    evil.mkdir(parents=True)
    (evil / "mnemosyne.db").symlink_to(outside)
    inner = env.hq.data / "banks" / "u-inner"
    inner.mkdir(parents=True)
    (inner / "mnemosyne.db").symlink_to(env.hq.data / "banks" / "u-bob" / "mnemosyne.db")
    registry.clear_cache()
    stores = registry.interim_stores()
    paths = {s.backend_ref for s in stores}
    ids = {s.store_id for s in stores}
    assert "hub:u-evil" not in ids and "hub:u-inner" not in ids
    assert str(outside) not in paths
    roots = registry._roots()
    assert registry.checked_store_path(evil / "mnemosyne.db", roots) is None
    assert registry.checked_store_path(outside, roots) is None
    assert all(any(Path(p).is_relative_to(r) for r in roots) for p in paths)
    # A path the registry does not list never reaches the reader.
    backend = backends.InterimSqliteBackend.shared()
    fake = registry.Store(store_id="hub:outside", ref="b_" + "0" * 32, kind="personal", label="x",
                          backend_ref=str(outside))
    viewer = env.scope.resolve_viewer(H.identity(H.MICHAEL), env.config)
    with pytest.raises(backends.StoreNotFound):
        backend.view(fake, "stats", {}, viewer)
    # And the reader child refuses a path outside its allowlist on its own.
    reader = backend.reader
    allow = tuple(sorted(paths))
    with pytest.raises(backends.BackendUnavailable):
        reader.request(allow, str(outside), "stats", {})


def test_the_hub_config_is_read_for_its_registry_keys_only(env, monkeypatch):
    config = registry._read_hub_config(env.hq.config_path)
    assert set(config) == {"people", "service_identities", "data_dir", "shared_bank", "banks"}
    opened = []
    real_open = open

    def spy(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", spy)
    registry.clear_cache()
    registry.interim_stores()
    assert not any("tokens" in path for path in opened)


def test_views_leave_every_store_byte_identical(env):
    before = _digest_tree(env.hq.root)
    env.as_user(H.MICHAEL, "Michael")
    stores = registry.interim_stores()
    views = ("stats", "memories", "search", "graph", "timeline", "constellation", "patterns", "profile/inferred",
             "review", "lifecycle", "digest/today", "triples", "consolidations", "memoria/stats", "memoria/facts",
             "recall-debug")
    env.memdash.VIEW_RATE.limit = 10_000
    try:
        for store in stores:
            for view in views:
                response = env.view(store.ref, view, q="option")
                assert response.status in (200, 404), (store.store_id, view, response.raw[:200])
    finally:
        env.memdash.VIEW_RATE.limit = 20
    assert _digest_tree(env.hq.root) == before


def test_the_writer_lock_is_never_busy_during_a_heavy_view(env):
    big = env.hq.data / "banks" / "u-ada" / "mnemosyne.db"
    con = sqlite3.connect(big)
    con.executemany(
        "INSERT INTO working_memory(id,content,source,timestamp,session_id,importance,scope) VALUES (?,?,?,?,?,?,?)",
        [(f"bulk-{i}", ("planning notes " * 40) + str(i), "bulk", "2026-09-01T00:00:00", f"s{i % 50}", 0.4, "global")
         for i in range(6000)],
    )
    con.commit()
    con.close()
    env.as_user(H.YASER, "Yaser")
    ref = env.ref_of(lambda s: s.store_id == "hub:u-ada")
    done = threading.Event()
    busy = []
    probes = []

    def probe():
        while not done.is_set():
            writer = sqlite3.connect(big, timeout=0)
            try:
                started = time.monotonic()
                writer.execute("BEGIN IMMEDIATE")
                writer.execute("ROLLBACK")
                probes.append(time.monotonic() - started)
            except sqlite3.OperationalError as exc:
                busy.append(str(exc))
            finally:
                writer.close()
            time.sleep(0.005)

    thread = threading.Thread(target=probe)
    thread.start()
    try:
        for query in ("planning notes 17", "notes 5999", "option planning"):
            assert env.view(ref, "memories", q=query, limit="500").status == 200
            assert env.view(ref, "search", q=query).status == 200
    finally:
        done.set()
        thread.join()
    assert busy == [] and len(probes) > 3
    assert max(probes) < 0.5


def test_open_file_descriptors_stay_stable_over_200_requests(env):
    env.as_user(H.ADA, "Ada Lovelace")
    assert env.view("me", "stats").status == 200
    reader = env.backends.InterimSqliteBackend._shared.reader
    fd_dir = Path(f"/proc/{reader.pid}/fd")
    if not fd_dir.exists():
        pytest.skip("no /proc on this platform")
    before = len(os.listdir(fd_dir))
    env.memdash.VIEW_RATE.limit = 10_000
    try:
        for i in range(200):
            view = ("stats", "memories", "graph", "search")[i % 4]
            assert env.view("me", view, q="option", offset=str(i)).status == 200
    finally:
        env.memdash.VIEW_RATE.limit = 20
    assert reader.pid is not None
    after = len(os.listdir(Path(f"/proc/{reader.pid}/fd")))
    assert after <= before + 1


def test_a_reader_that_stops_answering_is_killed_and_respawned(tmp_path):
    reader = backends.ReaderProcess(command=[sys.executable, str(REPO / "tests" / "fixtures" / "memdash" / "slow_reader.py")],
                                    timeout=0.5)
    try:
        started = time.monotonic()
        with pytest.raises(backends.BackendUnavailable):
            reader.request(("/nowhere",), "/nowhere", "stats", {})
        assert time.monotonic() - started < 5
        assert reader.pid is None and reader.spawn_count == 1
        with pytest.raises(backends.BackendUnavailable):
            reader.request(("/nowhere",), "/nowhere", "stats", {})
        assert reader.spawn_count == 2
    finally:
        reader.close()


def test_the_real_reader_answers_and_caps_its_memory(env):
    env.as_user(H.ADA, "Ada Lovelace")
    assert env.view("me", "stats").status == 200
    reader = env.backends.InterimSqliteBackend._shared.reader
    limits = Path(f"/proc/{reader.pid}/limits")
    if limits.exists():
        line = next(l for l in limits.read_text().splitlines() if l.startswith("Max address space"))
        assert str(1 << 30) in line


def test_every_change_answers_503(env):
    env.as_user(H.ADA, "Ada Lovelace")
    for action in ("invalidate", "supersede", "importance", "veracity", "expiry"):
        response = env.post("/api/memdash/v1/action", {"bank": "me", "action": action, "memory_id": "ada-w0",
                                                       "content": "x", "importance": 0.5, "veracity": "stated"})
        assert response.status == 503 and response.body["message"] == "Changes are not available yet."
    env.as_user(H.YASER, "Yaser")
    ref = env.ref_of(lambda s: s.store_id == "hub:u-ada")
    response = env.post("/api/memdash/v1/action", {"bank": ref, "action": "invalidate", "memory_id": "ada-w0",
                                                   "reason_code": "support"})
    assert response.status == 503
    assert env.access_log.rows_all() == []
    auth = env.view("me", "auth/status").body
    assert auth["config"]["memory_admin_enabled"] is False


@pytest.mark.parametrize("case", ["hub_url", "no_installation", "client"])
def test_the_interim_reader_is_off_with_a_hub_url_or_outside_hq(env, monkeypatch, case):
    if case == "hub_url":
        monkeypatch.setenv("HERMES_WEBUI_MNEMO_URL", "http://127.0.0.1:9/")
    elif case == "no_installation":
        env.set_policy(H.hq_policy())
    else:
        env.set_policy(H.hq_policy(installation={"kind": "managed"}))
    env.as_user(H.ADA, "Ada Lovelace")
    banks = env.banks()
    assert banks["enabled"] and banks["available"] is False and banks["stores"] == []
    assert env.view("me", "stats").status == 503
    assert env.backends.InterimSqliteBackend._shared is None
    with pytest.raises(backends.BackendUnavailable):
        backends.select_backend(is_hq=case == "hub_url")


def test_person_assistant_and_shared_stores_follow_the_single_person_rule(env):
    stores = {s.store_id: s for s in registry.interim_stores()}
    ada, bob = env.scope.email_hash(H.ADA), env.scope.email_hash(H.BOB)
    assert stores["hub:u-ada"].kind == "personal" and stores["hub:u-ada"].owner_hash == ada
    assert stores["profile:ada:u-ada"].kind == "personal" and stores["profile:ada:u-ada"].owner_hash == ada
    # Two identities map to the pair bank: an assistant store, never Bob's.
    assert stores["profile:pair:pair-bank"].kind == "assistant" and stores["profile:pair:pair-bank"].owner_hash == ""
    # No single person behind the identity: an assistant store.
    assert stores["profile:sales-ops:sales"].kind == "assistant"
    assert stores["hub:engine-only"].kind == "assistant"
    assert stores["hub:team-shared"].kind == "shared" and not stores["hub:team-shared"].mixed
    assert stores["hub:u-info"].kind == "shared" and stores["hub:u-info"].mixed
    custom = [s for s in stores.values() if s.store_id.startswith("extra:")]
    assert len(custom) == 1 and custom[0].kind == "shared" and custom[0].mixed
    env.as_user(H.BOB, "Bob")
    banks = env.banks()
    assert [s["label"] for s in banks["stores"]] == ["Bob (legacy)"]
    assert banks["stores"][0]["own"] and banks["stores"][0]["group"] == "mine"
    pair = stores["profile:pair:pair-bank"].ref
    assert env.view(pair, "stats").status == 404
    assert bob and all(s.owner_hash != bob for s in stores.values() if s.kind != "personal")


def test_references_are_stable_hmacs_and_never_paths(env):
    first = {s.store_id: s.ref for s in registry.interim_stores()}
    registry.clear_cache()
    again = {s.store_id: s.ref for s in registry.interim_stores()}
    assert first == again
    assert all(registry.valid_ref(ref) for ref in first.values())
    key = env.state / registry.KEY_FILE
    assert (key.stat().st_mode & 0o777) == 0o600
    for ref in first.values():
        assert "/" not in ref and "u-" not in ref
