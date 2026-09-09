"""Request-scoped resource bounds for model, settings and skill HTTP surfaces.

Coarse route permissions remain mandatory. Legacy policies with an omitted
dimension retain their old route-level behavior; configured dimensions and
explicit denials are enforced, including wildcard grants. Managed users also
retain their role ceiling. Cached catalogs are copied before filtering.
"""
from copy import deepcopy
from urllib.parse import parse_qs

from .models import grant_matches


def access_for(handler):
    from .enforce import _request_identity, subject_from_identity
    from .loader import get_policy
    from .resolver import resolve_effective_access

    policy = get_policy()
    if not policy.enabled or policy.mode == "report_only":
        return None
    return resolve_effective_access(policy, subject_from_identity(_request_identity(handler)))


def allowed(access, dimension, value, aliases=()):
    if access is None:
        return True
    values = tuple(dict.fromkeys(str(v).strip() for v in (value, *aliases) if str(v).strip()))
    if not values:
        return False
    if any(grant_matches(getattr(access.deny, dimension), v) for v in values):
        return False
    configured = getattr(access.grants, dimension)
    if not configured and access.role_ceiling is None:
        return True
    return any(access.allows(dimension, v) for v in values)


def _setting_group(key):
    from api.settings_scope import APPEARANCE_SETTINGS_KEYS
    if key in APPEARANCE_SETTINGS_KEYS:
        return "appearance"
    if key in {"password", "current_password", "auth_disabled", "api_redact", "check_updates", "update_channel"}:
        return "system"
    return "preferences"


def setting_allowed(access, key, write=False):
    return allowed(access, "settings_write" if write else "settings_read", key, (_setting_group(key),))


def model_allowed(access, model, provider=""):
    if access is None:
        return True
    from api.config import resolve_model_provider, _resolve_provider_alias, get_config
    raw_model = str(model or "").strip()
    if not raw_model:
        current = get_config().get("model", {})
        raw_model = str(current.get("default") or current.get("name") or "").strip()
    resolved_model, resolved_provider, _ = resolve_model_provider(raw_model)
    provider = str(provider or "").strip()
    if provider in {"", "auto", "default"}:
        provider = str(resolved_provider or "")
    provider = _resolve_provider_alias(provider)
    # An explicit picker hint is also a routing target and cannot hide behind
    # a different provider field supplied in the same request.
    if raw_model.startswith("@") and resolved_provider and not allowed(access, "model_providers", _resolve_provider_alias(resolved_provider)):
        return False
    return allowed(access, "model_providers", provider) and allowed(access, "models", raw_model, (resolved_model,))


def _reject(handler, resource, reason="resource_not_allowed"):
    from api.helpers import j
    from .audit import append_audit_event
    from .enforce import _request_identity
    try:
        identity = _request_identity(handler) or {}
        append_audit_event("deny", subject_email=identity.get("email", ""),
                           path=getattr(handler, "path", ""), method=getattr(handler, "command", ""),
                           reason=reason, mode="enforce", extra={"resource": resource})
    except Exception:
        pass
    j(handler, {"error": "forbidden", "reason": reason, "resource": resource}, status=403)
    return False


def guard_request(handler, parsed, method, body=None):
    """Return False after a response when a concrete requested target is denied."""
    path = parsed.path
    relevant = path in {"/api/settings", "/api/default-model", "/api/model/set", "/api/models/live", "/api/models/refresh",
                        "/api/skills/content", "/api/skills/save", "/api/skills/delete", "/api/skills/toggle"}
    if not relevant:
        return True
    try:
        access = access_for(handler)
        if access is None:
            return True
        data = body if isinstance(body, dict) else {}
        query = parse_qs(parsed.query or "")
        if path == "/api/settings" and method == "POST":
            for key in data:
                if not setting_allowed(access, key, write=True):
                    return _reject(handler, "settings:" + str(key))
        elif path in {"/api/default-model", "/api/model/set"} and method == "POST":
            if not model_allowed(access, data.get("model"), data.get("provider")):
                return _reject(handler, "model")
        elif path in {"/api/models/live", "/api/models/refresh"}:
            from api.config import _resolve_provider_alias, resolve_model_provider
            provider = data.get("provider") if method == "POST" else query.get("provider", [""])[0]
            provider = _resolve_provider_alias(str(provider or resolve_model_provider("")[1] or ""))
            if not allowed(access, "model_providers", provider):
                return _reject(handler, "model_provider")
        elif path.startswith("/api/skills/"):
            name = data.get("name", "") if method == "POST" else query.get("name", [""])[0]
            normalized = str(name).strip().lower().replace(" ", "-")
            dimension = "skills_manage" if method == "POST" else "skills_view"
            if name and not allowed(access, dimension, normalized, (str(name), normalized.rsplit("/", 1)[-1])):
                return _reject(handler, "skill:" + normalized)
        return True
    except Exception:
        return _reject(handler, "resource", "policy_error")


def filter_settings(handler, payload):
    access = access_for(handler)
    return {key: deepcopy(value) for key, value in payload.items() if setting_allowed(access, key)}


def filter_skills(handler, skills):
    access = access_for(handler)
    return [deepcopy(skill) for skill in skills if allowed(access, "skills_view", skill.get("name", ""))]


def filter_skill_usage(handler, payload):
    access = access_for(handler)
    result = deepcopy(payload)
    result["usage"] = {key: val for key, val in result.get("usage", {}).items() if allowed(access, "skills_view", key)}
    result["skill_names"] = [name for name in result.get("skill_names", []) if allowed(access, "skills_view", name)]
    counts = [sum(int(row.get(key, 0) or 0) for key in ("use_count", "view_count", "patch_count")) for row in result["usage"].values()]
    result["total_invocations"] = sum(counts)
    result["unique_skills_used"] = sum(n > 0 for n in counts)
    return result


def filter_models(handler, payload):
    access = access_for(handler)
    if access is None:
        return payload
    result = deepcopy(payload)
    def entries(models, provider):
        return [m for m in models if model_allowed(access, m.get("id", "") if isinstance(m, dict) else m, provider)]
    if "groups" in result:
        result["groups"] = [{**group, "models": entries(group.get("models", []), group.get("provider_id", ""))}
                            for group in result["groups"] if allowed(access, "model_providers", group.get("provider_id", ""))]
        result["groups"] = [group for group in result["groups"] if group["models"]]
    if "models" in result:
        result["models"] = entries(result["models"], result.get("provider", ""))
        result["count"] = len(result["models"])
    if not model_allowed(access, result.get("default_model", ""), result.get("active_provider", "")):
        result.pop("default_model", None)
    if "active_provider" in result and not allowed(access, "model_providers", result["active_provider"]):
        result.pop("active_provider", None)
    if "aliases" in result:
        result["aliases"] = {key: val for key, val in result["aliases"].items() if model_allowed(access, val)}
    # Badge metadata can reveal models removed from the visible groups.
    if "configured_model_badges" in result:
        visible = {m["id"] for group in result.get("groups", []) for m in group.get("models", [])}
        result["configured_model_badges"] = {key: val for key, val in result["configured_model_badges"].items() if key in visible}
    return result


def filter_auxiliary_models(handler, payload):
    access = access_for(handler)
    result = deepcopy(payload)
    for key, value in list(result.items()):
        if isinstance(value, dict) and "model" in value and not model_allowed(access, value.get("model"), value.get("provider")):
            result.pop(key)
    if "tasks" in result:
        result["tasks"] = [task for task in result["tasks"] if model_allowed(access, task.get("model"), task.get("provider"))]
    return result
