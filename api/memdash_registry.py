"""The Memory explorer's store registry and the store-level access rule.

Plan addendum 6.6.6 and 6.6.7. Every store carries a ``kind`` (personal, org,
dept, assistant, shared), an owner (email hash and display name, or none), an
organisation and a department. References are ``b_`` plus an HMAC of the
canonical store id under a 0600 key in the WebUI state directory: stable per
installation, not guessable, and never a path.

Interim registry (HQ only, until A11): built from the hub config named by
``HERMES_WEBUI_MEMDASH_HUB_CONFIG``, reading only ``people``,
``service_identities``, ``data_dir``, ``shared_bank`` and the ``owner_private``
flag of ``banks.<name>`` (revision 6.2), never the tokens file. Paths are
realpath-checked under ``HERMES_WEBUI_MEMDASH_BANK_ROOTS``: regular files, no
symlink escape, owned by the service user. The WebUI process only stats these
files; the reader child opens them.

* person stores: a hub bank that exactly one person maps to (the root
  ``default`` bank included), and a profile copy whose ``hermes-<profile>``
  identity maps to exactly one person while no other identity or person maps
  to the same bank;
* assistant stores (admins only): profile copies without a person, every
  profile copy that fails the rule above, and hub banks only identities feed;
* shared stores (platform only): the shared bank, banks that several people
  or nobody map to (``u-info`` at HQ), and stores under extra roots (the mux
  ``custom`` bank); all but the configured shared bank are marked mixed.

Owner-private stores (revision 6.2, Michael's item 11): a person marked
``owner_private`` (their bank's flag in ``banks.<name>``; at HQ the root
``default`` bank is owner-private unless its flag says ``false``) is the only
one who can list or open any store linked to them, profile copies included.
Everyone else gets 404, exactly like a store that does not exist.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import stat
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from api.memdash_scope import MEMBER, ORG_ADMIN, PLATFORM_ADMIN, Config, Viewer, email_hash

logger = logging.getLogger(__name__)

KINDS = ("personal", "org", "dept", "assistant", "shared")
KEY_FILE = "memdash_ref.key"
_REF_RE = re.compile(r"^b_[0-9a-f]{32}$")
_BANK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_DENYLIST_RE = re.compile(r"mnemosyne|mnemo-hub|hermes|omniroute|langgraph|litellm|n8n", re.IGNORECASE)
_MAX_CONFIG_BYTES = 1024 * 1024
_CACHE_TTL = 30.0

_LOCK = threading.Lock()
_KEY_CACHE: dict[str, bytes] = {}
_REGISTRY_CACHE: dict[tuple, tuple[float, list]] = {}


class RegistryUnavailable(RuntimeError):
    """The registry cannot be built; callers answer 503."""


@dataclass(frozen=True)
class Store:
    store_id: str
    ref: str
    kind: str
    label: str
    owner_hash: str = ""
    owner_display: str = ""
    org_id: str = ""
    org_name: str = ""
    dept: str = ""
    external: bool = False
    mixed: bool = False
    private_owner_hash: str = ""
    last_write: str = ""
    backend_ref: str = ""
    primary: bool = False

    @property
    def is_person_store(self) -> bool:
        return self.kind == "personal" and bool(self.owner_hash)

    def is_own(self, viewer: Viewer) -> bool:
        return self.is_person_store and bool(viewer.email_hash) and self.owner_hash == viewer.email_hash


# ── References ───────────────────────────────────────────────────────────────

def _state_dir() -> Path:
    from api.config import STATE_DIR

    return Path(STATE_DIR)


def _ref_key() -> bytes:
    path = _state_dir() / KEY_FILE
    cache_key = str(path)
    with _LOCK:
        cached = _KEY_CACHE.get(cache_key)
        if cached:
            return cached
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                fd = None
            if fd is not None:
                try:
                    os.write(fd, os.urandom(32).hex().encode("ascii"))
                finally:
                    os.close(fd)
            info = os.lstat(path)
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise RegistryUnavailable("the reference key file must be a 0600 regular file")
            data = bytes.fromhex(path.read_text(encoding="ascii").strip())
            if len(data) < 32:
                raise RegistryUnavailable("the reference key is too short")
        except (OSError, ValueError) as exc:
            raise RegistryUnavailable("the reference key is not available") from exc
        _KEY_CACHE[cache_key] = data
        return data


def ref_for(store_id: str) -> str:
    digest = hmac.new(_ref_key(), ("memdash-store|" + store_id).encode("utf-8"), hashlib.sha256).hexdigest()
    return "b_" + digest[:32]


def valid_ref(value: str) -> bool:
    return bool(_REF_RE.match(str(value or "")))


def neutral_label(text: str, fallback: str) -> str:
    value = re.sub(r"[\x00-\x1f\x7f]", " ", str(text or "")).strip()[:80]
    if not value or _DENYLIST_RE.search(value):
        return fallback
    return value


# ── Access rule ──────────────────────────────────────────────────────────────

def authorize(viewer: Viewer, store: Store, config: Config) -> bool:
    """May ``viewer`` list and open ``store``? (addendum 6.6.6, revision 6.2)

    A member only their own person stores; an organisation admin the person
    stores of their organisation's non-external people and that
    organisation's org, dept and assistant stores (never an empty or unknown
    organisation); a platform admin every store on the installation. An
    owner-private store only its owner, whoever asks.
    """
    if store.private_owner_hash and store.private_owner_hash != viewer.email_hash:
        return False
    if store.is_own(viewer):
        return True
    if viewer.kind == PLATFORM_ADMIN:
        return config.view_platform_admins
    if viewer.kind == ORG_ADMIN:
        if not config.view_org_admins or not viewer.org_id or not store.org_id:
            return False
        if store.org_id != viewer.org_id:
            return False
        if store.kind == "personal":
            return bool(store.owner_hash) and not store.external
        return store.kind in ("org", "dept", "assistant")
    return False


def group_of(viewer: Viewer, store: Store) -> str:
    if store.is_own(viewer):
        return "mine"
    if store.kind == "personal":
        return "people"
    if store.kind == "assistant":
        return "assistants"
    return "shared"


# ── Interim registry (HQ) ────────────────────────────────────────────────────

def _roots() -> list[Path]:
    raw = os.environ.get("HERMES_WEBUI_MEMDASH_BANK_ROOTS", "")
    roots = []
    for part in raw.split(":"):
        part = part.strip()
        if not part:
            continue
        try:
            roots.append(Path(os.path.realpath(os.path.expanduser(part))))
        except (OSError, ValueError):
            continue
    return roots


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def checked_store_path(candidate: Path, roots: list[Path]) -> Path | None:
    """The real path of a store file that may be opened, or None."""
    try:
        info = os.lstat(candidate)
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        return None
    real = Path(os.path.realpath(candidate))
    if not any(_under(real, root) for root in roots):
        return None
    try:
        real_info = os.stat(real)
    except OSError:
        return None
    if not stat.S_ISREG(real_info.st_mode) or real_info.st_uid != os.getuid():
        return None
    return real


def _last_write(path: Path) -> str:
    newest = 0.0
    for suffix in ("", "-wal"):
        try:
            newest = max(newest, os.stat(str(path) + suffix).st_mtime)
        except OSError:
            continue
    if not newest:
        return ""
    return datetime.fromtimestamp(newest, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_hub_config(path: Path) -> dict:
    import yaml

    try:
        info = os.stat(path)
        if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_CONFIG_BYTES:
            raise RegistryUnavailable("the hub config is not a regular file of a sane size")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except RegistryUnavailable:
        raise
    except Exception as exc:
        raise RegistryUnavailable("the hub config cannot be read") from exc
    if not isinstance(data, dict):
        raise RegistryUnavailable("the hub config must be a mapping")
    # Only these keys are ever read (addendum 6.6.7); tokens are never touched.
    return {k: data.get(k) for k in ("people", "service_identities", "data_dir", "shared_bank", "banks")}


def _bank_file(data_dir: Path, bank: str) -> Path:
    if bank == "default":
        return data_dir / "mnemosyne.db"
    return data_dir / "banks" / bank / "mnemosyne.db"


def _flag(value) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def build_interim(config_path: Path, roots: list[Path]) -> list[Store]:
    cfg = _read_hub_config(config_path)
    if not roots:
        raise RegistryUnavailable("no store roots are configured")
    raw_dir = cfg.get("data_dir")
    if not isinstance(raw_dir, str) or not raw_dir.strip():
        raise RegistryUnavailable("the hub config has no data_dir")
    data_dir = Path(os.path.realpath(os.path.expanduser(raw_dir)))
    if not any(_under(data_dir, root) for root in roots):
        raise RegistryUnavailable("data_dir is outside the store roots")

    people: dict[str, dict] = {}
    for email, spec in (cfg.get("people") or {}).items() if isinstance(cfg.get("people"), dict) else []:
        email = str(email or "").strip().lower()
        spec = spec if isinstance(spec, dict) else {}
        bank = str(spec.get("bank") or "").strip()
        if not email or "@" not in email or not _BANK_RE.match(bank):
            continue
        display = str(spec.get("naam") or spec.get("name") or "").strip() or email.split("@")[0]
        people[email] = {
            "bank": bank,
            "display": neutral_label(display, email.split("@")[0]),
            "external": spec.get("external") is True,
        }
    identities: dict[str, dict] = {}
    raw_ids = cfg.get("service_identities")
    for name, spec in (raw_ids.items() if isinstance(raw_ids, dict) else []):
        spec = spec if isinstance(spec, dict) else {}
        bank = str(spec.get("bank") or "").strip()
        identities[str(name)] = {
            "bank": bank if _BANK_RE.match(bank) else "",
            "email": str(spec.get("email") or "").strip().lower(),
        }
    banks_cfg = cfg.get("banks") if isinstance(cfg.get("banks"), dict) else {}
    shared_bank = str(cfg.get("shared_bank") or "").strip()

    def bank_private(bank: str) -> bool:
        spec = banks_cfg.get(bank) if isinstance(banks_cfg.get(bank), dict) else {}
        flag = _flag(spec.get("owner_private"))
        if flag is not None:
            return flag
        # Revision 6.2: at HQ the root default bank (Michael's) is
        # owner-private unless the registry explicitly says otherwise.
        return bank == "default"

    bank_people: dict[str, set[str]] = {}
    for email, spec in people.items():
        bank_people.setdefault(spec["bank"], set()).add(email)
    bank_identities: dict[str, set[str]] = {}
    for name, spec in identities.items():
        if spec["bank"]:
            bank_identities.setdefault(spec["bank"], set()).add(name)
    private_people = {email for email, spec in people.items() if bank_private(spec["bank"])}

    stores: list[Store] = []
    seen_paths: set[Path] = set()

    def add(store_id: str, path: Path, **fields) -> None:
        real = checked_store_path(path, roots)
        if real is None or real in seen_paths:
            return
        seen_paths.add(real)
        stores.append(Store(store_id=store_id, ref=ref_for(store_id), backend_ref=str(real),
                            last_write=_last_write(real), **fields))

    # Hub banks: configured and discovered.
    names = set(bank_people) | set(bank_identities)
    if shared_bank and _BANK_RE.match(shared_bank):
        names.add(shared_bank)
    banks_dir = data_dir / "banks"
    try:
        for entry in sorted(os.scandir(banks_dir), key=lambda e: e.name):
            if entry.is_dir(follow_symlinks=False) and _BANK_RE.match(entry.name):
                names.add(entry.name)
    except OSError:
        pass
    if (data_dir / "mnemosyne.db").exists():
        names.add("default")
    for bank in sorted(names):
        persons = bank_people.get(bank, set())
        path = _bank_file(data_dir, bank)
        if len(persons) == 1 and bank != shared_bank:
            owner = next(iter(persons))
            add("hub:" + bank, path, kind="personal", label=people[owner]["display"],
                owner_hash=email_hash(owner), owner_display=people[owner]["display"],
                external=people[owner]["external"],
                private_owner_hash=email_hash(owner) if owner in private_people else "",
                primary=True)
        elif bank == shared_bank:
            add("hub:" + bank, path, kind="shared", label=neutral_label(bank, "Shared memories"))
        elif not persons and bank_identities.get(bank):
            add("hub:" + bank, path, kind="assistant", label=neutral_label(bank, "Assistant"))
        else:
            add("hub:" + bank, path, kind="shared", mixed=True, label=neutral_label(bank, "Shared store"))

    # Profile copies.
    profiles_root = data_dir.parent.parent / "profiles" if data_dir.parent.name == "mnemosyne" else None
    if profiles_root is not None:
        for name, spec in sorted(identities.items()):
            if not name.startswith("hermes-"):
                continue
            profile = name[len("hermes-"):]
            if not _PROFILE_RE.match(profile):
                continue
            bank = spec["bank"] or "default"
            path = _bank_file(profiles_root / profile / "mnemosyne" / "data", bank)
            person = spec["email"] if spec["email"] in people else ""
            others = (bank_identities.get(bank, set()) - {name}) | (bank_people.get(bank, set()) - {person})
            single = bool(person) and not others
            private = email_hash(person) if person in private_people else ""
            label = neutral_label(profile, "Assistant")
            if single:
                label = people[person]["display"] + " (" + label + ")"
                add("profile:" + profile + ":" + bank, path, kind="personal", label=label,
                    owner_hash=email_hash(person), owner_display=people[person]["display"],
                    external=people[person]["external"], private_owner_hash=private)
            else:
                add("profile:" + profile + ":" + bank, path, kind="assistant", label=label,
                    private_owner_hash=private)

    # Stores under extra roots (for example the mux custom bank): platform only.
    for root in roots:
        if _under(data_dir, root) or _under(root, data_dir):
            continue
        if profiles_root is not None and (_under(root, profiles_root) or _under(profiles_root, root)):
            continue
        candidates = [("main", root / "mnemosyne.db")]
        try:
            for entry in sorted(os.scandir(root / "banks"), key=lambda e: e.name):
                if entry.is_dir(follow_symlinks=False) and _BANK_RE.match(entry.name):
                    candidates.append((entry.name, root / "banks" / entry.name / "mnemosyne.db"))
        except OSError:
            pass
        root_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
        for bank, path in candidates:
            add("extra:" + root_id + ":" + bank, path, kind="shared", mixed=True,
                label=neutral_label(bank, "Shared store"))
    return stores


def interim_stores() -> list[Store]:
    """The interim registry, cached for 30 seconds per config version."""
    raw = os.environ.get("HERMES_WEBUI_MEMDASH_HUB_CONFIG", "").strip()
    if not raw:
        raise RegistryUnavailable("HERMES_WEBUI_MEMDASH_HUB_CONFIG is not set")
    path = Path(os.path.expanduser(raw))
    roots = _roots()
    try:
        info = os.stat(path)
        signature = (str(path), info.st_mtime_ns, info.st_size, tuple(str(r) for r in roots), str(_state_dir()))
    except OSError as exc:
        raise RegistryUnavailable("the hub config cannot be read") from exc
    now = time.monotonic()
    with _LOCK:
        cached = _REGISTRY_CACHE.get(signature)
        if cached and now - cached[0] < _CACHE_TTL:
            return cached[1]
    stores = build_interim(path, roots)
    with _LOCK:
        _REGISTRY_CACHE.clear()
        _REGISTRY_CACHE[signature] = (now, stores)
    return stores


def clear_cache() -> None:
    with _LOCK:
        _REGISTRY_CACHE.clear()
        _KEY_CACHE.clear()


# ── Hub registry (``GET /v1/banks``) ─────────────────────────────────────────

def from_hub_entries(entries, viewer: Viewer) -> list[Store]:
    """Map the hub's ``/v1/banks`` entries (A13h contract) to stores."""
    stores: list[Store] = []
    for raw in entries if isinstance(entries, list) else []:
        if not isinstance(raw, dict):
            continue
        hub_ref = str(raw.get("ref") or "").strip()
        kind = str(raw.get("kind") or "").strip()
        if not hub_ref or len(hub_ref) > 128 or kind not in KINDS:
            continue
        owner_hash = str(raw.get("owner_hash") or "").strip().lower()
        if not owner_hash and raw.get("owner_email"):
            owner_hash = email_hash(str(raw.get("owner_email")))
        if owner_hash and not re.match(r"^[0-9a-f]{24}$", owner_hash):
            continue
        if kind == "personal" and not owner_hash:
            continue
        owner_display = neutral_label(raw.get("owner_display") or "", "Person") if owner_hash else ""
        org_id = str(raw.get("org") or "").strip()
        store_id = "hubapi:" + hub_ref
        stores.append(Store(
            store_id=store_id, ref=ref_for(store_id), kind=kind,
            label=neutral_label(raw.get("label") or owner_display or hub_ref, "Store"),
            owner_hash=owner_hash, owner_display=owner_display, org_id=org_id,
            org_name=neutral_label(raw.get("org_name") or "", viewer.org_name or ""),
            dept=str(raw.get("dept") or "").strip()[:40], external=raw.get("external") is True,
            mixed=raw.get("mixed") is True,
            private_owner_hash=owner_hash if raw.get("owner_private") is True else "",
            last_write=str(raw.get("last_write") or "")[:40], backend_ref=hub_ref,
            primary=raw.get("primary") is True or hub_ref == "me",
        ))
    return stores


def primary_for(viewer: Viewer, stores: list[Store]) -> Store | None:
    own = [s for s in stores if s.is_own(viewer)]
    for store in own:
        if store.primary:
            return store
    return own[0] if own else None


def with_org_name(store: Store, name: str) -> Store:
    return store if store.org_name else replace(store, org_name=name)


def viewer_kinds() -> tuple[str, ...]:
    return (MEMBER, ORG_ADMIN, PLATFORM_ADMIN)


def personal_stores(viewer: Viewer) -> list[Store]:
    """Current person-owned banks, resolved only from the authenticated viewer.

    Bot identity and administrative role never select another person's directory.
    Conversation banks remain private copies owned by that same person.
    """
    from api import personal_context

    identity = {"email": viewer.email}
    try:
        directory = personal_context.home(identity) / "mnemosyne"
        if not directory.is_dir():
            return []
        stores = []
        for candidate in sorted(directory.glob("*.db")):
            bank = candidate.stem
            if bank != "private" and not re.fullmatch(r"[0-9a-f]{64}", bank):
                continue
            personal_context._safe(candidate)
            path = checked_store_path(candidate, [directory])
            if path is None:
                continue
            store_id = "person:" + viewer.email_hash + ":" + bank
            stores.append(Store(
                store_id=store_id, ref=ref_for(store_id), kind="personal",
                label="Personal memories" if bank == "private" else "Conversation memories " + bank[:8],
                owner_hash=viewer.email_hash, owner_display=viewer.display_name,
                private_owner_hash=viewer.email_hash, primary=bank == "private",
                backend_ref=str(path), last_write=_last_write(path),
            ))
        return stores
    except (OSError, PermissionError, ValueError) as exc:
        raise RegistryUnavailable("personal stores unavailable") from exc
