"""One personal credential boundary for WebUI turns and delegated workers."""
from contextlib import contextmanager


def bind(identity, session_id=None):
    from api import personal_context, chat_connectors
    from api.hosted_connectors import personal_token, authorize_connection
    from agent.vault_scope import bind_personal_vault, reset_personal_vault
    from tools.connectors.identity import bind_connector_identity, reset_connector_identity
    captured = dict(identity) if isinstance(identity, dict) else {"email": identity}
    choices = chat_connectors.disabled(captured, session_id)
    hosted = {key.removeprefix("hosted:") for key in choices if key.startswith("hosted:")}
    nango = {key.removeprefix("nango:") for key in choices if key.startswith("nango:")}
    root = personal_context.ensure_home(captured)
    vault = bind_personal_vault(root)
    try:
        connectors = bind_connector_identity(
            lambda: personal_token(captured),
            **({"disabled_connectors": hosted} if hosted else {}),
            authorize_connection=lambda slugs: authorize_connection(captured, slugs),
        )
    except BaseException:
        reset_personal_vault(vault)
        raise
    try:
        from api import app_connections
        apps = app_connections.bind(captured, disabled=nango)
    except BaseException:
        reset_connector_identity(connectors)
        reset_personal_vault(vault)
        raise
    return vault, connectors, apps


def reset(tokens):
    from agent.vault_scope import reset_personal_vault
    from tools.connectors.identity import reset_connector_identity
    vault, connectors, *rest = tokens
    try:
        if rest:
            from api import app_connections
            app_connections.reset(rest[0])
    finally:
        try:
            reset_connector_identity(connectors)
        finally:
            reset_personal_vault(vault)


@contextmanager
def scope(identity, session_id=None):
    tokens = bind(identity, session_id)
    try:
        yield
    finally:
        reset(tokens)
