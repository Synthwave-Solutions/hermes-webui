"""Bot selection and project membership are independent sidebar constraints."""
import copy

from api import routes
from tests.test_session_list_project_read_budget import project_store, ALICE  # noqa: F401


def test_shared_project_chats_are_scoped_to_their_bot(project_store, monkeypatch):
    source = [
        {'session_id': 'writer-chat', 'profile': 'writer', 'project_id': 'team',
         'project_shared': True, 'bot_participants': ['writer'], 'owner_email': ALICE, 'message_count': 2},
        {'session_id': 'review-chat', 'profile': 'reviewer', 'project_id': 'team',
         'project_shared': True, 'bot_participants': ['reviewer'], 'owner_email': ALICE, 'message_count': 2},
        {'session_id': 'old-writer-chat', 'profile': 'default', 'project_id': 'team',
         'project_shared': True, 'bot_participants': ['writer'], 'owner_email': ALICE, 'message_count': 2},
        {'session_id': 'private', 'profile': 'default', 'project_id': None,
         'owner_email': ALICE, 'message_count': 2},
    ]
    monkeypatch.setattr(routes, 'all_sessions', lambda **kw: copy.deepcopy(source))
    monkeypatch.setattr(routes, '_reconcile_stale_stream_state_for_session_rows', lambda rows: False)
    monkeypatch.setattr(routes, '_prune_orphaned_webui_zero_message_sessions', lambda rows, **kw: rows)
    monkeypatch.setattr(routes, '_is_isolated_profile_mode', lambda: False)
    def fetch(profile, all_profiles=False):
        return routes._build_session_list_cache_payload(profile, all_profiles, False, False, False, owner_scope=ALICE)
    result = fetch('writer')
    assert {row['session_id'] for row in result['sessions']} == {'writer-chat', 'old-writer-chat'}
    assert {row['project_id'] for row in result['sessions']} == {'team'}
    assert {row['profile'] for row in result['sessions']} == {'writer'}
    assert {row['session_id'] for row in fetch('reviewer')['sessions']} == {'review-chat'}
    assert {row['session_id'] for row in fetch('default')['sessions']} == {'private'}
    assert len(fetch('writer', True)['sessions']) == 4
    assert source[2]['profile'] == 'default'  # Listing never migrates stored history.
    monkeypatch.setattr(routes, '_is_isolated_profile_mode', lambda: True)
    assert {row['session_id'] for row in fetch('writer')['sessions']} == {'writer-chat'}
