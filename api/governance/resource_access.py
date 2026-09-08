"""Resource-level checks shared by direct frontend file API sinks."""
from pathlib import Path

from . import loader
from .enforce import subject_from_identity
from .models import grant_matches
from .resolver import resolve_effective_access


def file_allowed(identity, path):
    try:
        ensure_file_access(identity, path)
        return True
    except PermissionError:
        return False


def filter_file_entries(identity, root, entries):
    return [entry for entry in entries if file_allowed(identity, Path(root) / entry["path"])]


def ensure_file_access(identity, path, *, write=False):
    from api.workspace_access import ensure_identity_workspace_access
    ensure_identity_workspace_access(identity, path)
    try:
        policy = loader.get_policy()
    except Exception:
        raise PermissionError("Governance policy unavailable") from None
    if policy.mode != "enforce":
        return
    subject = subject_from_identity(identity)
    if subject.normalized_email in policy.bootstrap_admins:
        return
    access = resolve_effective_access(policy, subject)
    target = str(Path(path).expanduser().resolve())
    dimension = "file_write_roots" if write else "file_read_roots"
    denied = (grant_matches(getattr(access.deny, dimension), target, path=True)
              or grant_matches(access.deny.file_denied_globs, target)
              or grant_matches(access.deny.file_denied_globs, Path(target).name))
    # Existing denied-glob exceptions remain compatible. Explicit per-user
    # denies above are a hard ceiling and never accept allow exceptions.
    configured_deny = (grant_matches(access.grants.file_denied_globs, target)
                      or grant_matches(access.grants.file_denied_globs, Path(target).name))
    exception = (grant_matches(access.grants.file_allow_globs, target)
                 or grant_matches(access.grants.file_allow_globs, Path(target).name))
    if denied or (configured_deny and not exception):
        raise PermissionError("File access explicitly denied by governance")
    if access.access_mode or access.access_level:
        if not access.allows(dimension, target, path=True):
            raise PermissionError("File is outside the user's governed scope")
