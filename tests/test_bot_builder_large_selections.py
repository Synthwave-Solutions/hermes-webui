# ruff: noqa: F811
from dataclasses import replace
import pytest
import yaml
from api import bot_builder as builder
from tests.test_bot_builder import setup, ADMIN, payload  # noqa: F401


def large_catalog(root):
    from api.governance.loader import get_policy
    policy=get_policy()
    role=policy.roles['worker']
    commands=frozenset({'git', *('qa-command-'+str(i) for i in range(153))})
    policy.roles['worker']=replace(role, grants=replace(role.grants, cli_commands=commands))
    for i in range(553):
        skill=root/'skills'/('qa-skill-'+str(i));skill.mkdir()
        (skill/'SKILL.md').write_text('# Synthetic skill')
    path=root/'config.yaml';config=yaml.safe_load(path.read_text())
    config['platform_toolsets']={'cli':['terminal']};path.write_text(yaml.safe_dump(config))
    (root/'SOUL.md').write_text('Synthetic shared default bot')
    body=builder.get(ADMIN,'default')['config'];body.pop('avatar_url')
    assert len(body['skills'])==554 and len(body['cli_tools'])==154
    return body


def test_real_catalog_counts_save_narrow_and_restore(setup):
    body=large_catalog(setup)
    result=builder.save(ADMIN,body)
    assert len(result['config']['cli_tools'])==154
    body['revision']=1;body['cli_tools']=body['cli_tools'][:-1]
    result=builder.save(ADMIN,body)
    assert len(result['config']['cli_tools'])==153
    body['revision']=2
    body['cli_tools']=[row['name'] for row in builder.catalog(ADMIN)['cli_tools']]
    result=builder.save(ADMIN,body)
    assert len(result['config']['cli_tools'])==154
    assert len(result['config']['skills'])==554


def test_large_selection_still_enforces_catalog_and_absolute_bound(setup):
    body=large_catalog(setup)
    body['cli_tools'][-1]='unavailable-command'
    with pytest.raises(PermissionError):
        builder.save(ADMIN,body)
    body['cli_tools']=['git']*10001
    with pytest.raises(ValueError):
        builder.save(ADMIN,body)
    assert builder.managed('default') is None


def test_new_bot_can_select_actual_available_large_catalog(setup):
    large_catalog(setup)
    body=payload();body['cli_tools']=[row['name'] for row in builder.catalog(ADMIN)['cli_tools']]
    result=builder.save(ADMIN,body)
    assert len(result['config']['cli_tools'])==154



def test_existing_unchanged_model_survives_unavailable_provider_catalog(setup, monkeypatch):
    builder.save(ADMIN, payload())
    def unavailable(*args):
        raise ValueError('Model catalog unavailable')
    monkeypatch.setattr('api.profiles._validate_profile_model_selection', unavailable)
    result=builder.save(ADMIN, {**payload(), 'revision':1, 'description':'Updated description'})
    assert result['config']['description']=='Updated description'
    with pytest.raises(ValueError, match='Model catalog unavailable'):
        builder.save(ADMIN, {**payload(), 'revision':2, 'default_model':'different-model'})
    with pytest.raises(ValueError, match='Model catalog unavailable'):
        builder.save(ADMIN, {**payload(), 'revision':2, 'model_provider':'different-provider'})
    with pytest.raises(ValueError, match='Model catalog unavailable'):
        builder.save(ADMIN, {**payload(), 'name':'new-bot'})



@pytest.mark.parametrize('field', ['models','model_providers'])
def test_unchanged_model_still_obeys_current_grants(setup, monkeypatch, field):
    builder.save(ADMIN, payload())
    original=builder.access
    def revoked(identity):
        policy,rights=original(identity)
        return policy,replace(rights,grants=replace(rights.grants,**{field:frozenset({'unrelated'})}))
    monkeypatch.setattr(builder,'access',revoked)
    with pytest.raises(PermissionError,match='Model selection is not allowed'):
        builder.save(ADMIN,{**payload(),'revision':1})
