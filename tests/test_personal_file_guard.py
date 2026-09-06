from types import SimpleNamespace
from unittest.mock import patch
import pytest
from api import personal_context as pc
from api.personal_file_guard import guard_request


@pytest.mark.parametrize('route', ['/api/file','/api/file/raw','/api/media','/api/file/save','/api/file/delete','/api/escape/file/read'])
def test_generic_paths_cannot_read_other_actor_or_shared_personal_data(tmp_path, route):
    alice={'email':'alice@example.test'}
    bob={'email':'bob@example.test'}
    with patch('api.config.STATE_DIR', tmp_path):
        private=pc.home(bob)/'memories'/'MEMORY.md'
        session=SimpleNamespace(workspace=str(tmp_path),owner_email=alice['email'],participants=[],project_shared=False)
        with patch('api.governance.enforce._request_identity',return_value=alice),patch('api.routes.get_session_for_file_ops',return_value=session):
            with pytest.raises(PermissionError):
                guard_request(object(),route,{'session_id':'s','path':str(private)})
            own=pc.home(alice)/'memories'/'MEMORY.md'
            guard_request(object(),route,{'session_id':'s','path':str(own)})
            session.participants=[bob['email']]
            with pytest.raises(PermissionError):
                guard_request(object(),route,{'session_id':'s','path':str(own)})


def test_folder_ancestor_move_destination_and_symlink_are_guarded(tmp_path):
    identity={'email':'alice@example.test'}
    with patch('api.config.STATE_DIR',tmp_path):
        private=pc.home({'email':'bob@example.test'})
        private.mkdir(parents=True)
        (tmp_path/'link').symlink_to(private,target_is_directory=True)
        session=SimpleNamespace(workspace=str(tmp_path),owner_email=identity['email'],participants=[],project_shared=False)
        with patch('api.governance.enforce._request_identity',return_value=identity),patch('api.routes.get_session_for_file_ops',return_value=session):
            for route,values in [('/api/folder/download',{'path':'.'}),('/api/list',{}),('/api/file',{'path':'link/MEMORY.md'}),('/api/file/move',{'path':'ordinary.txt','dest_dir':str(private)})]:
                with pytest.raises(PermissionError):
                    guard_request(object(),route,{'session_id':'s',**values})
            guard_request(object(),'/api/file',{'session_id':'s','path':'ordinary.txt'})
