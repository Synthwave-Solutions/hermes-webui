"""Enroll background bots in an explicitly configured shared gateway."""
from pathlib import Path


class BackgroundRuntimeError(RuntimeError):
    pass


def ensure_background_profile(home) -> None:
    """Register a real local profile, then require the gateway to serve it.

    The root's operator setting is authoritative, never a bot/request setting.
    An unset setting preserves ordinary native gateway discovery. Registration
    is idempotent and never replaces another profile or restarts a gateway.
    """
    from api.config import get_config_for_profile_home
    from api.profiles import _DEFAULT_HERMES_HOME

    base = Path(_DEFAULT_HERMES_HOME).resolve()
    settings = get_config_for_profile_home(base).get("webui") or {}
    if not isinstance(settings, dict):
        raise BackgroundRuntimeError("The background runner settings must be a mapping.")
    configured = settings.get("background_gateway_home")
    if not configured:
        return
    try:
        from gateway.control_socket import rescan_gateway_profiles
        from hermes_cli.gateway_runtime import _endpoint
        from hermes_cli.gateway_runtime_discovery import _private_node, query_identify

        host = Path(configured).expanduser()
        if not host.is_absolute():
            raise ValueError("background_gateway_home must be absolute")
        host = host.resolve(strict=True)
        profile = Path(home).resolve(strict=True)
        if profile == base:
            return  # The default profile has its own gateway.
        if profile.parent != (base / "profiles").resolve():
            raise ValueError("profile is outside this installation")
        _private_node(profile, kind="directory", home=True)
        payload = query_identify(host, timeout=2)
        if _endpoint(payload, host).state != "ready":
            raise BackgroundRuntimeError("The background runner is not ready; Scout was not enabled.")
        directory = host / "profiles"
        _private_node(directory, kind="directory", home=True)
        link = directory / profile.name
        try:
            link.symlink_to(profile, target_is_directory=True)
        except FileExistsError:
            if link.resolve(strict=True) != profile:
                raise BackgroundRuntimeError("The background runner has a different profile with this name.") from None
        if _endpoint(payload, profile, control_home=host).state != "ready":
            rescan_gateway_profiles(host, timeout=8)
            payload = query_identify(host, timeout=2)
        if _endpoint(payload, profile, control_home=host).state != "ready":
            raise BackgroundRuntimeError(
                "The background runner could not start this bot; check its gateway status and retry. "
                "Scout was not enabled."
            )
    except BackgroundRuntimeError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError, ImportError) as exc:
        raise BackgroundRuntimeError(
            "The background runner is unavailable or its profile registration is invalid. "
            "Scout was not enabled; check the gateway configuration and retry."
        ) from exc
