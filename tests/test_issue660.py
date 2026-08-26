"""
Tests for session queue persistence across page refresh and tab restore.

#660 introduced sessionStorage persistence. #3108 hardens it by mirroring queue
state to localStorage and restoring from the durable copy when sessionStorage is
missing after browser tab/process restore.
"""
import pathlib

UI_JS = pathlib.Path(__file__).parent.parent / 'static' / 'ui.js'
SESSIONS_JS = pathlib.Path(__file__).parent.parent / 'static' / 'sessions.js'

ui_src = UI_JS.read_text(encoding='utf-8')
sess_src = SESSIONS_JS.read_text(encoding='utf-8')


class TestQueuePersistence:
    """queueSessionMessage persists through the shared dual-storage helper."""

    def test_queue_storage_helpers_exist(self):
        """Queue persistence must be centralized so write/delete paths stay symmetric."""
        assert "function _queueStorageKey(sid)" in ui_src
        assert "function _persistSessionQueueStorage(sid, queue)" in ui_src
        assert "function _readPersistedSessionQueue(sid)" in ui_src
        assert "function _clearPersistedSessionQueue(sid)" in ui_src

    def test_queue_writes_to_session_and_local_storage(self):
        """queueSessionMessage must mirror queue state to sessionStorage and localStorage."""
        helper_start = ui_src.find("function _persistSessionQueueStorage(sid, queue)")
        helper_end = ui_src.find("function _readPersistedSessionQueue(sid)", helper_start)
        assert helper_start != -1 and helper_end != -1, "_persistSessionQueueStorage helper not found"
        helper = ui_src[helper_start:helper_end]
        assert "sessionStorage.setItem(key,payload)" in helper
        assert "localStorage.setItem(key,payload)" in helper

    def test_queue_stamps_queued_at_timestamp(self):
        """Each queue entry must have a _queued_at timestamp for stale-entry detection."""
        assert '_queued_at' in ui_src

    def test_shift_uses_shared_persist_and_clear_helpers(self):
        """shiftQueuedSessionMessage must update both storage layers through the
        merge-aware persist helper, and tombstone the removed entry so the
        cross-tab merge cannot resurrect it from an older stored copy (D3).
        (A blind _clearPersistedSessionQueue here would wipe entries other tabs
        queued; the persist helper clears the key itself when nothing is left.)"""
        start = ui_src.find("function shiftQueuedSessionMessage(sid)")
        end = ui_src.find("function getQueuedSessionCount(sid)", start)
        assert start != -1 and end != -1, "shiftQueuedSessionMessage block not found"
        body = ui_src[start:end]
        assert "_tombstoneQueueEntry(sid,next._qid)" in body
        assert "_persistSessionQueueStorage(sid,q)" in body
        assert "_clearPersistedSessionQueue(sid)" not in body, (
            "blind key clear would drop entries another tab queued (D3)"
        )

    def test_queue_card_edit_paths_use_shared_helpers(self):
        """Queue edit/combine/delete paths must not leave localStorage stale."""
        assert "_saveAndRefresh()" in ui_src
        assert "_persistSessionQueueStorage(sid,liveQ)" in ui_src
        assert "_clearPersistedSessionQueue(sid)" in ui_src


class TestQueueRestore:
    """Queue is restored from the shared storage helper on idle session load."""

    def test_restore_reads_shared_helper(self):
        """sessions.js must restore through the lifecycle-aware helper, which itself
        reads the dual-storage layer so the localStorage fallback stays reachable
        (behavior superseded by the queued-messages-disappear P1 fix)."""
        assert "restoreSessionQueueFromStorage(sid,S.messages,S.session)" in sess_src
        helper_start = ui_src.find("function restoreSessionQueueFromStorage(sid, messages, session)")
        assert helper_start != -1, "restoreSessionQueueFromStorage helper not found in ui.js"
        helper_end = ui_src.find("function _compressionSessionLock", helper_start)
        helper = ui_src[helper_start:helper_end]
        assert "_readPersistedSessionQueue(sid)" in helper

    def test_read_helper_falls_back_to_local_storage(self):
        """The dual-storage read must keep both layers reachable, with the
        SHARED localStorage copy as the cross-tab source of truth and the
        per-tab sessionStorage mirror only as a fallback when localStorage is
        unusable. (The old session-first preference let a stale tab-local
        mirror shadow removals made by another tab and resurrect sent
        entries; double-send D3.)"""
        start = ui_src.find("function _readPersistedSessionQueue(sid)")
        end = ui_src.find("function queueSessionMessage(sid", start)
        assert start != -1 and end != -1, "_readPersistedSessionQueue block not found"
        body = ui_src[start:end]
        local = body.find("localStorage.getItem(key)")
        session = body.find("sessionStorage.getItem(key)")
        assert local != -1 and session != -1, "both storage layers must stay reachable"
        assert local < session, "localStorage (shared) must be consulted before the per-tab mirror"
        assert "if(localOk) return parse(raw);" in body, (
            "a readable-but-empty localStorage means the queue IS empty; the "
            "tab-local mirror must not shadow another tab's removals"
        )

    def test_restore_uses_positive_evidence_reconciliation(self):
        """Entries may only be dropped with positive evidence the turn was sent.

        The old guard dropped every entry queued before the LAST assistant reply
        (_lastAsst), which silently lost messages queued while the agent was
        answering a previous turn (queued-messages-disappear P1). The lossy
        filter must stay gone and the transcript-match reconciliation must be
        what the restore path uses instead.
        """
        assert '_lastAsst' not in sess_src, "the lossy last-assistant-timestamp filter must not come back"
        assert "function _queueEntryMatchesTranscript(entry, messages, session)" in ui_src
        restore_start = ui_src.find("function restoreSessionQueueFromStorage(sid, messages, session)")
        restore_body = ui_src[restore_start:ui_src.find("function _compressionSessionLock", restore_start)]
        assert "_queueEntryMatchesTranscript(e,messages,session)" in restore_body

    def test_restore_shows_toast(self):
        """User must see a toast notification when a queue is restored."""
        restore_start = ui_src.find("function restoreSessionQueueFromStorage(sid, messages, session)")
        restore_body = ui_src[restore_start:ui_src.find("function _compressionSessionLock", restore_start)]
        assert 'queued message' in restore_body.lower() and 'restored' in restore_body.lower()

    def test_restore_repopulates_full_queue_not_composer(self):
        """ALL surviving entries go back into SESSION_QUEUES in order; the old
        first-entry-as-composer-draft restore lost every other entry."""
        restore_start = ui_src.find("function restoreSessionQueueFromStorage(sid, messages, session)")
        restore_body = ui_src[restore_start:ui_src.find("function _compressionSessionLock", restore_start)]
        assert "SESSION_QUEUES[sid]=restored;" in restore_body
        assert "_persistSessionQueueStorage(sid,restored);" in restore_body
        assert "_msg.value=_first.text" not in sess_src, "restore must not degrade the queue to a single composer draft"

    def test_restore_clears_storage_only_when_all_entries_processed(self):
        """The persisted copy is emptied only when every entry reconciled as
        already-sent; a populated queue must never be wiped on load. The empty
        write goes through the merge-aware persist helper (not a blind key
        clear) so entries another tab queued meanwhile survive (D3)."""
        restore_start = ui_src.find("function restoreSessionQueueFromStorage(sid, messages, session)")
        restore_body = ui_src[restore_start:ui_src.find("function _compressionSessionLock", restore_start)]
        clear_pos = restore_body.find("_persistSessionQueueStorage(sid,[]);")
        guard_pos = restore_body.find("if(!restored.length){")
        assert guard_pos != -1 and clear_pos != -1 and guard_pos < clear_pos
        assert "_clearPersistedSessionQueue(sid);" not in restore_body, (
            "restore must never blind-clear the shared queue key (D3)"
        )

    def test_restore_wrapped_in_try_catch(self):
        """Storage access must be wrapped in try/catch (private browsing may block
        it), and the catch must NOT clear the queue (the old handler wiped the
        persisted entries on any transient exception)."""
        assert "catch(_){/* storage may be blocked (private browsing); keep the queue untouched */}" in sess_src
        assert "catch(_){if(typeof _clearPersistedSessionQueue==='function') _clearPersistedSessionQueue(sid);}" not in sess_src

    def test_delete_session_clears_persisted_queue_after_success(self):
        """Deleting a session must clear localStorage-backed queue state after the API succeeds."""
        start = sess_src.find("async function deleteSession(sid, beforeDelete=null)")
        end = sess_src.find("// ── Project helpers", start)
        assert start != -1 and end != -1, "deleteSession block not found"
        body = sess_src[start:end]
        clear_pos = body.find("if(typeof _clearPersistedSessionQueue==='function') _clearPersistedSessionQueue(sid);")
        error_pos = body.find("if(deleteResult&&deleteResult.error){")
        success_pos = body.find("const response=deleteResult&&deleteResult.response;")
        assert error_pos != -1 and success_pos != -1 and clear_pos != -1
        assert success_pos < clear_pos, "queue cleanup should run only after delete success"

    def test_busy_session_restores_queue_but_only_idle_kicks_drain(self):
        """Both loadSession branches restore the queue (a refresh during a live
        stream must not lose it), but only the idle branch kicks an immediate
        drain; the busy branch waits for setBusy(false) at stream completion."""
        assert sess_src.count("restoreSessionQueueFromStorage(sid,S.messages,S.session)") == 2, \
            "queue restore must run in BOTH the INFLIGHT (busy) and idle loadSession branches"
        # The drain kick is exclusive to the idle branch.
        assert sess_src.count("drainQueuedSessionMessage(sid)") == 1
        drain_pos = sess_src.find("drainQueuedSessionMessage(sid)")
        set_busy_true_pos = sess_src.find("setBusy(true);setComposerStatus('');")
        assert drain_pos > set_busy_true_pos, \
            "the drain kick must live in the idle branch, after the busy branch"
