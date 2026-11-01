"""Curated engine plugins in the Integrations hub; shared engine installers."""
import re


def payload(handler):
    from api.ownership import request_is_admin
    from api.profiles import get_active_profile_name, profile_env_for_active_request_readonly
    from hermes_cli import plugins_cmd
    from hermes_cli.plugin_catalog import load_catalog_live, match_removed, resolved_removed_entries
    with profile_env_for_active_request_readonly('plugin catalog'):
        enabled = plugins_cmd._get_enabled_set()
        disabled = plugins_cmd._get_disabled_set()
        active = plugins_cmd._category_active_names()
        installed = []
        for name, version, description, source, directory, key in plugins_cmd._discover_all_plugins():
            status = plugins_cmd._plugin_status(name, enabled, disabled, key, source=source, dir_path=directory, active=active)
            installed.append({'name': name, 'key': key, 'version': version, 'description': description,
                              'source': source, 'enabled': status == 'enabled', 'status': status})
        removed = resolved_removed_entries()
        entries = [e.to_dict() for e in load_catalog_live()
                   if not match_removed(e.name, removed) and not match_removed(e.repo, removed)]
    return {'catalog': entries, 'installed': installed, 'profile': get_active_profile_name(),
            'can_manage': request_is_admin(handler)}


def handle(handler, action, body=None):
    from api.routes import j
    from api.ownership import request_is_admin
    from api.profiles import profile_env_for_active_request
    try:
        if action == 'catalog':
            return j(handler, payload(handler))
        if not request_is_admin(handler):
            return j(handler, {'error': 'Only administrators can change bot plugins.'}, status=403)
        name = (body or {}).get('name')
        if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_/-]{0,127}', name) or '..' in name:
            raise ValueError('Invalid plugin name')
        from hermes_cli.plugins_cmd import dashboard_install_plugin, dashboard_set_agent_plugin_enabled
        with profile_env_for_active_request('plugin management'):
            if action == 'install':
                result = dashboard_install_plugin('', catalog_name=name, enable=True, force=False)
            elif action == 'toggle' and isinstance((body or {}).get('enabled'), bool):
                result = dashboard_set_agent_plugin_enabled(name, enabled=body['enabled'])
            else:
                raise ValueError('Invalid plugin action')
        if result.get('error') or result.get('ok') is False or result.get('success') is False:
            return j(handler, {'error': 'The plugin could not be changed. Check its requirements and retry.'}, status=409)
        return j(handler, {'ok': True, 'restart_required': True})
    except ValueError as exc:
        return j(handler, {'error': str(exc)}, status=400)
    except Exception:
        # Install errors may contain credential/config paths; do not echo them.
        return j(handler, {'error': 'Plugin management is unavailable. Please retry.'}, status=502)
