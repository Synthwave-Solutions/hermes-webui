"""Read-only local module catalogue. Central requests/entitlements are not connected."""
from __future__ import annotations

import os
from api import modules, module_connections
from api.governance import delegation, loader
from api.helpers import j

# Public fields copied from the pinned catalogue, checked against it in tests.
CATALOG = {'workspace': {'name': {'nl': 'Werkplek en AI-medewerkers', 'en': 'Workspace and AI assistants'},
               'summary': {'nl': 'Chat, AI-medewerkers, projecten, geplande taken, vaardigheden en geheugen '
                                 'op één plek.',
                           'en': 'Chat, AI assistants, projects, scheduled tasks, skills and memory in one '
                                 'place.'},
               'tier': 'standard',
               'lifecycle': 'available',
               'confirmed': True,
               'model_usage': {'level': 'high', 'consumers': 'every chat, task and skill'}},
 'group_chat': {'name': {'nl': 'Groepsgesprekken met AI-medewerkers', 'en': 'Group chats with AI assistants'},
                'summary': {'nl': "Collega's en meerdere AI-medewerkers in één gesprek, ook in Teams, Slack "
                                  'en WhatsApp.',
                            'en': 'Colleagues and several AI assistants in one conversation, also in Teams, '
                                  'Slack and WhatsApp.'},
                'tier': 'standard',
                'lifecycle': 'available',
                'confirmed': True,
                'model_usage': {'level': 'medium', 'consumers': 'assistant turns in group conversations'}},
 'design_studio': {'name': {'nl': 'Ontwerpstudio', 'en': 'Design studio'},
                   'summary': {'nl': 'Documenten, presentaties en afbeeldingen in je eigen huisstijl.',
                               'en': 'Documents, presentations and images in your own house style.'},
                   'tier': 'standard',
                   'lifecycle': 'available',
                   'confirmed': True,
                   'model_usage': {'level': 'medium', 'consumers': 'design generation through the router'}},
 'workflows': {'name': {'nl': 'Workflows', 'en': 'Workflows'},
               'summary': {'nl': 'Processen die automatisch tussen je systemen lopen, door ons gebouwd en '
                                 'beheerd.',
                           'en': 'Processes that run automatically between your systems, built and run by '
                                 'us.'},
               'tier': 'standard',
               'lifecycle': 'available',
               'confirmed': True,
               'model_usage': {'level': 'low', 'consumers': 'AI steps through the router'}},
 'knowledge_base': {'name': {'nl': 'Kennisbank op je eigen documenten',
                             'en': 'Knowledge base on your own documents'},
                    'summary': {'nl': 'Doorzoek de documenten van je organisatie en krijg antwoorden met '
                                      'bronnen.',
                                'en': "Search your organisation's documents and get answers with sources."},
                    'tier': 'advanced',
                    'lifecycle': 'pilot',
                    'confirmed': False,
                    'model_usage': {'level': 'high',
                                    'consumers': 'embeddings at the first ingest, retrieval plus answer per '
                                                 'question'}},
 'notebook': {'name': {'nl': 'Onderzoeksnotitieboek', 'en': 'Research notebook'},
              'summary': {'nl': 'Verzamel bronnen, maak notities en krijg samenvattingen, ook als audio.',
                          'en': 'Collect sources, take notes and get summaries, also as audio.'},
              'tier': 'advanced',
              'lifecycle': 'pilot',
              'confirmed': False,
              'model_usage': {'level': 'medium', 'consumers': 'summaries; audio summaries high'}},
 'e_signing': {'name': {'nl': 'Digitaal ondertekenen', 'en': 'Digital signing'},
               'summary': {'nl': 'Laat documenten digitaal ondertekenen met een volledig '
                                 'ondertekeningsverslag.',
                           'en': 'Have documents signed digitally with a complete signing record.'},
               'tier': 'advanced',
               'lifecycle': 'pilot',
               'confirmed': False,
               'model_usage': {'level': 'none', 'consumers': 'nothing'}},
 'dictation': {'name': {'nl': 'Dicteren in elke applicatie', 'en': 'Dictation in every application'},
               'summary': {'nl': 'Dicteer tekst op je laptop in elke applicatie; je spraak wordt in de EU '
                                 'verwerkt en niet bewaard.',
                           'en': 'Dictate text on your laptop in any application; your speech is processed '
                                 'in the EU and not stored.'},
               'tier': 'advanced',
               'lifecycle': 'pilot',
               'confirmed': False,
               'model_usage': {'level': 'low',
                               'consumers': 'speech minutes; no model spend when transcription runs on the '
                                            'installation'}},
 'meeting_notes': {'name': {'nl': 'Vergaderverslagen', 'en': 'Meeting notes'},
                   'summary': {'nl': 'Verslagen, besluiten en actiepunten van elke vergadering, opgenomen op '
                                     'je eigen laptop.',
                               'en': 'Minutes, decisions and actions from every meeting, recorded on your '
                                     'own laptop.'},
                   'tier': 'advanced',
                   'lifecycle': 'pilot',
                   'confirmed': False,
                   'model_usage': {'level': 'medium',
                                   'consumers': 'one summary per meeting through the router'}},
 'office_apps': {'name': {'nl': "Kantoorprogramma's met AI", 'en': 'Office apps with AI'},
                 'summary': {'nl': 'Documenten, spreadsheets, presentaties en pdf-bestanden op je laptop '
                                   'schrijven en bewerken met een AI-assistent die de eigen AI-dienst van je '
                                   'organisatie gebruikt.',
                             'en': 'Write and edit documents, spreadsheets, presentations and PDF files on '
                                   "your laptop with an AI assistant that uses your organisation's own AI "
                                   'service.'},
                 'tier': 'advanced',
                 'lifecycle': 'pilot',
                 'confirmed': False,
                 'model_usage': {'level': 'medium',
                                 'consumers': 'the assistant inside the apps, through the gateway'}}}


def context(handler):
    from api.governance.enforce import _request_identity, subject_from_identity
    policy = loader.get_policy()
    identity = _request_identity(handler)
    subject = subject_from_identity(identity, policy)
    return policy, subject, delegation.delegated_scope(policy, subject)


def visible(policy, scope):
    return bool(delegation.organization_id(policy) and not delegation.installation_is_hq(policy)
                and scope.scope in {'platform', 'org', 'billing'})


def _authorized(handler):
    try:
        policy, subject, scope = context(handler)
    except Exception:
        j(handler, {'error': 'policy_unavailable'}, status=503)
        return None
    if delegation.installation_is_hq(policy) or not delegation.organization_id(policy):
        j(handler, {'error': 'not found'}, status=404)
        return None
    if not visible(policy, scope):
        j(handler, {'error': 'forbidden', 'reason': 'delegated_scope'}, status=403)
        return None
    return policy


def handle_get(handler, parsed):
    policy = _authorized(handler)
    if policy is None:
        return True
    state = modules.current_state()
    connections = module_connections.resolve(state, os.environ, policy.raw)
    rows = []
    for mid, spec in modules.REGISTRY.items():
        data = CATALOG[mid]
        links = module_connections.works_with(mid, state, connections)
        for link in links:
            connection = module_connections.REGISTRY[link['connection']]
            link['name'] = dict(connection.name)
            link['summary'] = dict(connection.summary)
        rows.append({'id': mid, 'tier': spec.tier,
                     'status': 'included' if spec.tier == 'standard' else
                               'active' if mid in state.active else 'available',
                     'name': data['name'], 'summary': data['summary'],
                     'model_usage': data['model_usage']['level'],
                     'lifecycle': data['lifecycle'], 'confirmed': data['confirmed'],
                     'works_with': links})
    j(handler, {'modules': rows, 'source': state.source, 'read_only': True,
                'requests_connected': False})
    return True


def handle_request(handler, body):
    if _authorized(handler) is not None:
        j(handler, {'error': 'requests_not_connected'}, status=503)
    return True


def settings_view(handler):
    state = modules.current_state()
    nav = modules.nav_view(state)
    nav['modules_visible'] = False
    nav['apps_visible'] = False
    nav['msp_visible'] = False
    try:
        policy, subject, scope = context(handler)
        nav['modules_visible'] = visible(policy, scope)
        nav['apps_visible'] = bool(subject.normalized_email and subject.provider != 'auth_disabled')
        from api import msp_service
        nav['msp_visible'] = msp_service.visible(handler)
    except Exception:
        pass
    return {'enabled_modules': list(state.active), 'modules_source': state.source,
            'module_nav': nav, 'enabled_connections': list(module_connections.current_state().active)}
