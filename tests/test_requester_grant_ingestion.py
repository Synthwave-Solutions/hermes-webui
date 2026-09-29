"""A requester's pending route denials are visible before any admin queue visit."""
import pytest

from api import approvals, grant_requests
from tests.test_governance_approvals_kinds import as_user as as_user, isolated_home as isolated_home, _call


@pytest.fixture(autouse=True)
def notifications(monkeypatch):
    events = []
    monkeypatch.setattr(grant_requests, '_notify_admins_of_request', lambda entry: events.append(entry['owner_email']))
    return events


def test_requester_read_ingests_only_own_denial_without_admin_visit(as_user, notifications):
    assert grant_requests.record_route_denial('viewer@example.test', '/api/skills')
    assert grant_requests.record_route_denial('other@example.test', '/api/skills/usage')
    assert approvals.load() == {}
    as_user('viewer@example.test')
    _, response = _call('/api/governance/approvals/mine', query='owner_email=other@example.test')
    assert response.status == 200
    assert response.body['owner_email'] == 'viewer@example.test'
    assert [(row['key'], row['status']) for row in response.body['requests']] == [
        ('viewer@example.test|route|/api/skills', 'pending')]
    assert approvals.get('grant', 'other@example.test|route|/api/skills/usage') is None
    assert notifications == ['viewer@example.test']
    _, repeated = _call('/api/governance/approvals/mine')
    assert repeated.body['requests'] == response.body['requests']
    assert notifications == ['viewer@example.test']


@pytest.mark.parametrize('decision,expected', [('approve', 'approved'), ('reject', 'rejected')])
def test_requester_refresh_preserves_decided_request_without_reopening(as_user, decision, expected):
    email = 'viewer@example.test'; key = email + '|route|/api/skills'
    assert grant_requests.record_route_denial(email, '/api/skills')
    as_user(email)
    _, pending = _call('/api/governance/approvals/mine')
    assert pending.body['requests'][0]['status'] == 'pending'
    approvals.decide('grant', key, decision, 'admin@example.test')
    assert grant_requests.record_route_denial(email, '/api/skills')
    _, decided = _call('/api/governance/approvals/mine')
    assert len(decided.body['requests']) == 1
    assert decided.body['requests'][0]['status'] == expected
    assert decided.body['requests'][0]['decided_by'] == 'admin@example.test'


def test_admin_ingestion_still_collects_every_owner(notifications):
    for email in ['viewer@example.test', 'other@example.test']:
        assert grant_requests.record_route_denial(email, '/api/skills')
    assert grant_requests.ingest_spool() == 2
    assert sorted(notifications) == ['other@example.test', 'viewer@example.test']
    assert len(approvals.list_all(kinds=['grant'])) == 2
