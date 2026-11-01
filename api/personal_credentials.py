"""One personal credential boundary for WebUI turns and delegated workers."""
from contextlib import contextmanager


def bind(identity):
    from api import personal_context
    from api.hosted_connectors import personal_token, authorize_connection
    from agent.vault_scope import bind_personal_vault, reset_personal_vault
    from tools.connectors.identity import bind_connector_identity
    captured = dict(identity) if isinstance(identity, dict) else {"email": identity}
    root = personal_context.ensure_home(captured)
    vault = bind_personal_vault(root)
    try:
        connectors = bind_connector_identity(
            lambda: personal_token(captured),
            authorize_connection=lambda slugs: authorize_connection(captured, slugs),
        )
    except BaseException:
        reset_personal_vault(vault)
        raise
    return vault, connectors


def reset(tokens):
    from agent.vault_scope import reset_personal_vault
    from tools.connectors.identity import reset_connector_identity
    vault, connectors = tokens
    try:
        reset_connector_identity(connectors)
    finally:
        reset_personal_vault(vault)


@contextmanager
def scope(identity):
    tokens = bind(identity)
    try:
        yield
    finally:
        reset(tokens)
