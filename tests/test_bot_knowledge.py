# ruff: noqa: F811
import base64
from dataclasses import replace
import pytest
from api import bot_builder as builder, bot_knowledge as knowledge
from tests.test_bot_builder import setup, ADMIN, BOB, OUT, payload  # noqa: F401


def upload(name='research-bot', filename='Guide.md', text=b'# Shared guide'):
    return {'profile': name, 'action': 'upload', 'filename': filename,
            'data': base64.b64encode(text).decode()}


def test_upload_select_reload_and_other_bot_isolation(setup):
    builder.save(ADMIN, payload())
    result = knowledge.mutate(ADMIN, upload())
    identifier = result['uploaded']
    assert result['selected'] == []
    assert knowledge.prompt('research-bot', ADMIN['email']) == ''
    saved = knowledge.mutate(ADMIN, {'profile':'research-bot', 'action':'select', 'selected':[identifier], 'revision':result['revision']})
    assert saved['selected'] == [identifier]
    assert knowledge.catalog(ADMIN, 'research-bot')['selected'] == [identifier]
    reference = str(setup / 'profiles/research-bot/knowledge' / identifier)
    assert reference in knowledge.prompt('research-bot', ADMIN['email'])
    assert knowledge.prompt('research-bot', OUT['email']) == ''
    builder.save(ADMIN, {**payload(), 'name':'second-bot'})
    assert knowledge.catalog(ADMIN, 'second-bot')['files'] == []
    with pytest.raises(ValueError):
        knowledge.mutate(ADMIN, {'profile':'second-bot', 'action':'select', 'selected':[identifier], 'revision':0})
    # Builder saves preserve independently saved documents and selection.
    builder.save(ADMIN, {**payload(), 'revision':1})
    assert reference in knowledge.prompt('research-bot', ADMIN['email'])


def test_owner_only_catalog_mutation_and_revoked_prompt(setup):
    builder.save(ADMIN, {**payload(), 'allowed_users':[BOB['email']]})
    for actor in (BOB, OUT):
        with pytest.raises(PermissionError):
            knowledge.catalog(actor, 'research-bot')
        with pytest.raises(PermissionError):
            knowledge.mutate(actor, upload())
    result=knowledge.mutate(ADMIN, upload())
    knowledge.mutate(ADMIN, {'profile':'research-bot', 'action':'select', 'selected':[result['uploaded']], 'revision':result['revision']})
    assert result['uploaded'] in knowledge.prompt('research-bot', BOB['email'])
    builder.save(ADMIN, {**payload(), 'revision':1})
    assert knowledge.prompt('research-bot', BOB['email']) == ''
    assert knowledge.prompt('research-bot', None) == ''


@pytest.mark.parametrize('filename', ['../secret.md', '/tmp/secret.md', '.env', 'bad.exe', 'a/b.md'])
def test_bad_upload_names(setup, filename):
    builder.save(ADMIN, payload())
    with pytest.raises(ValueError):
        knowledge.mutate(ADMIN, upload(filename=filename))


def test_revision_payload_and_symlink_guards(setup, tmp_path):
    builder.save(ADMIN, payload())
    for body in ({}, {'profile':None}, {'profile':[]}, {'profile':123}):
        with pytest.raises(ValueError):
            knowledge.mutate(ADMIN, body)
    with pytest.raises(RuntimeError):
        knowledge.mutate(ADMIN, {'profile':'research-bot', 'action':'select', 'selected':[], 'revision':False})
    result=knowledge.mutate(ADMIN, upload())
    path=setup/'profiles/research-bot/knowledge'/result['uploaded']
    path.unlink();path.symlink_to(setup/'config.yaml')
    assert knowledge.catalog(ADMIN, 'research-bot')['files'] == []
    with pytest.raises(ValueError):
        knowledge.mutate(ADMIN, {'profile':'research-bot', 'action':'select', 'selected':[result['uploaded']], 'revision':0})
    path.unlink();path.parent.rmdir();path.parent.symlink_to(setup/'skills')
    with pytest.raises(OSError):
        knowledge.mutate(ADMIN, upload())


def test_actual_engine_read_policy_retains_allow_and_deny(setup):
    from hermes_cli.dashboard_governance.tool_policy import decide_tool_argument_access
    builder.save(ADMIN, {**payload(), 'allowed_users':[BOB['email']]})
    result=knowledge.mutate(ADMIN, upload())
    path=str(setup/'profiles/research-bot/knowledge'/result['uploaded'])
    _, rights=builder.access(BOB)
    scoped=builder.constrain_access(BOB, 'research-bot', rights)
    allowed=replace(scoped, grants=replace(scoped.grants, file_read_roots=frozenset({str(setup/'profiles/research-bot/knowledge')})))
    denied=replace(scoped, grants=replace(scoped.grants, file_read_roots=frozenset({str(setup/'unrelated')})))
    assert decide_tool_argument_access(allowed, 'read_file', {'path':path}).allowed
    assert not decide_tool_argument_access(denied, 'read_file', {'path':path}).allowed
