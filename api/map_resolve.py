"""Map blocks: coordinates and photos for the places in a ```map block.

``POST /api/map/resolve`` (routed early in ``api.routes.handle_post``, after
the CSRF check; ``check_auth`` already ran in ``server.py``). The chat sends
the places of one finished map block; the answer says for each place where it
is and how precise that is. The kit frame cannot reach this server, so the
chat passes the answer on to it.

Lookup per place, first hit wins:

1. coordinates given in the block (from the user or a tool);
2. the cache (``STATE_DIR/map_cache.sqlite`` plus an in-process LRU);
3. PDOK Locatieserver (Kadaster, Dutch addresses) when the region holds
   ``nl`` and the place has an address;
4. Nominatim (OpenStreetMap) within its usage policy: one request per
   1.05 s for the whole process, an identifying User-Agent, results cached,
   at most 8 uncached lookups per call and about 500 a day; beyond that the
   place is ``later``;
5. the coordinates of the Wikipedia article named in ``wiki``.

Photos (only with ``photos: true``, at most 8 per map) come from the
Wikipedia summary of the article and are only used when Wikimedia Commons
lists a CC or public-domain license and a named creator. The checks are
ported from Open Intelligent UI's ``trip_images.py`` (MIT, CopilotKit).

Safety: every base URL is a constant; user text only goes into urlencoded
query strings or a ``quote(safe='')`` path segment; redirects are not
followed (one same-host hop for a renamed Wikipedia article); 6 s per call,
12 s per request, 512 KB per response. Per user: 20 calls a minute and 300
places an hour (429 with Retry-After). Logs hold counts only, never
addresses: client addresses can be personal data.

Config: ``webui_map_geocoder`` (``pdok,nominatim`` by default, ``off`` for
no outside lookups at all), ``webui_map_contact`` (added to the
User-Agent), ``webui_map_tiles`` (tile URL template, or a dict with ``url``,
``attribution`` and ``maxZoom``). ``HERMES_WEBUI_MAP_GEOCODER``,
``HERMES_WEBUI_MAP_CONTACT`` and ``HERMES_WEBUI_MAP_TILES`` override them.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import math
import os
import re
import sqlite3
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger(__name__)

PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
WIKI_HOSTS = {lang: f"{lang}.wikipedia.org" for lang in ("nl", "en", "de", "fr")}
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
ALLOWED_HOSTS = frozenset({"api.pdok.nl", "nominatim.openstreetmap.org", "commons.wikimedia.org", *WIKI_HOSTS.values()})
PHOTO_PREFIX = "https://upload.wikimedia.org/wikipedia/commons/"
DEFAULT_TILES = {"url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png", "attribution": "© OpenStreetMap", "maxZoom": 19}
USER_AGENT = "SynthwaveSuperAgent/1.0 (+https://synthwave.solutions)"

MAX_BODY = 16 * 1024
MAX_PLACES = 25
MAX_QUERY = 200
MAX_NAME = 80
MAX_PHOTOS = 8
CALL_TIMEOUT = 6.0
REQUEST_DEADLINE = 12.0
MAX_RESPONSE = 512 * 1024
NOMINATIM_SPACING = 1.05
NOMINATIM_PER_REQUEST = 8
NOMINATIM_PER_DAY = 500
RATE_WINDOW = 60.0
RATE_REQUESTS = 20
PLACES_WINDOW = 3600.0
RATE_PLACES = 300
GEO_TTL_HIT = 180 * 86400
GEO_TTL_MISS = 86400
PHOTO_TTL = 30 * 86400
PHOTO_TTL_MISS = 86400
LRU_SIZE = 2000
_RATE_MAX_KEYS = 2000
CHAIN = ("pdok", "nominatim")

_warned = {"geocoder": False}
_clock = time.monotonic
_now = time.time
_sleep = time.sleep


# ── Config ──────────────────────────────────────────────────────────────────

def _config():
    try:
        from api.config import get_config
        data = get_config()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _setting(config_data, key, env):
    value = os.environ.get(env)
    if value is not None and value.strip() != "":
        return value
    if isinstance(config_data, dict):
        return config_data.get(key)
    return None


def geocoders(config_data=None) -> tuple[str, ...]:
    """The lookup chain. Absent means the default; an unknown value means off."""
    raw = _setting(config_data, "webui_map_geocoder", "HERMES_WEBUI_MAP_GEOCODER")
    if raw is None:
        return CHAIN
    if raw is False:
        return ()
    if isinstance(raw, str):
        words = [w.strip().lower() for w in re.split(r"[\s,]+", raw) if w.strip()]
    elif isinstance(raw, (list, tuple)):
        words = [str(w).strip().lower() for w in raw]
    else:
        return ()
    if not words or any(w in ("off", "none", "false", "0", "no") for w in words):
        return ()
    chain = tuple(dict.fromkeys(w for w in words if w in CHAIN))
    if len(chain) != len(set(words)):
        # A typo must not quietly send addresses somewhere: fail closed.
        if not _warned["geocoder"]:
            _warned["geocoder"] = True
            logger.warning("map resolve: unknown value in webui_map_geocoder, outside lookups are off")
        return ()
    return chain


def user_agent(config_data=None) -> str:
    contact = _setting(config_data, "webui_map_contact", "HERMES_WEBUI_MAP_CONTACT")
    contact = re.sub(r"[^A-Za-z0-9@.+:/_-]", "", str(contact or ""))[:120]
    return USER_AGENT[:-1] + "; " + contact + ")" if contact else USER_AGENT


_TILE_RE = re.compile(r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+(?::\d{2,5})?/[^\s\"'<>\\{}]*(?:\{[zxyr]\}[^\s\"'<>\\{}]*)+$")


def tiles(config_data=None) -> dict:
    """The tile layer for maps (also read for the kit frame's img-src)."""
    if config_data is None:
        config_data = _config()
    raw = _setting(config_data, "webui_map_tiles", "HERMES_WEBUI_MAP_TILES")
    out = dict(DEFAULT_TILES)
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = None
    if isinstance(raw, str):
        raw = {"url": raw}
    if not isinstance(raw, dict):
        return out
    url = str(raw.get("url") or "").strip()
    if not (_TILE_RE.match(url) and all(t in url for t in ("{z}", "{x}", "{y}"))):
        return out
    out["url"] = url
    attribution = re.sub(r"[\x00-\x1f<>]", "", str(raw.get("attribution") or "")).strip()[:160]
    out["attribution"] = attribution or ("© OpenStreetMap" if "openstreetmap" in url else "")
    try:
        out["maxZoom"] = max(1, min(20, int(raw.get("maxZoom", 19))))
    except (TypeError, ValueError):
        out["maxZoom"] = 19
    return out


# ── Network ─────────────────────────────────────────────────────────────────

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Copied from api/auth_oidc.py: a redirect is an error, never followed."""

    def redirect_request(self, *args, **kwargs):
        return None


class _Deadline(Exception):
    pass


def _build_opener():
    return urllib.request.build_opener(_NoRedirect)


_OPENER = _build_opener()


def _open(request, timeout):
    """One HTTP call; returns (status, bytes). Replaced in tests."""
    with _OPENER.open(request, timeout=timeout) as response:
        return response.status, response.read(MAX_RESPONSE + 1)


def _check_url(url: str) -> None:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS or parts.username or parts.password or parts.port:
        raise ValueError("host not allowed")


def _fetch_json(url, deadline, agent, *, follow_same_host=False):
    _check_url(url)
    for hop in range(2):
        remaining = deadline - _clock()
        if remaining < 0.5:
            raise _Deadline()
        request = urllib.request.Request(url, headers={
            "User-Agent": agent, "Accept": "application/json", "Accept-Language": "nl,en;q=0.8"})
        try:
            status, data = _open(request, min(CALL_TIMEOUT, remaining))
        except urllib.error.HTTPError as exc:
            location = exc.headers.get("Location") if exc.headers else None
            if follow_same_host and hop == 0 and exc.code in (301, 302, 303, 307, 308) and location:
                target = urllib.parse.urljoin(url, location)
                if urllib.parse.urlsplit(target).hostname == urllib.parse.urlsplit(url).hostname:
                    _check_url(target)
                    url = target
                    continue
            raise
        if status != 200:
            raise ValueError(f"status {status}")
        if len(data) > MAX_RESPONSE:
            raise ValueError("response too large")
        return json.loads(data.decode("utf-8"))
    raise ValueError("too many redirects")


# ── Nominatim pacing (one request per 1.05 s for the whole process) ─────────

_NOMI_LOCK = threading.Lock()
_nomi = {"last": -1e9, "day": "", "count": 0}


def _nominatim_slot(deadline) -> bool:
    """Wait for the next free Nominatim slot; False when there is no time or budget left."""
    remaining = deadline - _clock()
    if remaining <= 1.0 or not _NOMI_LOCK.acquire(timeout=remaining - 1.0):
        return False
    try:
        today = time.strftime("%Y-%m-%d", time.gmtime(_now()))
        if _nomi["day"] != today:
            _nomi["day"], _nomi["count"] = today, 0
        if _nomi["count"] >= NOMINATIM_PER_DAY:
            return False
        wait = _nomi["last"] + NOMINATIM_SPACING - _clock()
        if wait > 0:
            if _clock() + wait > deadline - 1.0:
                return False
            _sleep(wait)
        _nomi["last"] = _clock()
        _nomi["count"] += 1
        return True
    finally:
        _NOMI_LOCK.release()


# ── Cache ───────────────────────────────────────────────────────────────────

class _Cache:
    def __init__(self, path=None):
        self._path = path
        self._db = None
        self._lock = threading.Lock()
        self._lru: OrderedDict = OrderedDict()
        self._broken = False

    def _conn(self):
        if self._db is not None or self._broken:
            return self._db
        try:
            path = Path(self._path) if self._path else _default_cache_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(str(path), timeout=2.0, check_same_thread=False, isolation_level=None)
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
            db.execute("CREATE TABLE IF NOT EXISTS geo(key TEXT PRIMARY KEY, lat REAL, lng REAL, precision TEXT,"
                       " label TEXT, source TEXT, wiki TEXT, ts INTEGER)")
            db.execute("CREATE TABLE IF NOT EXISTS photo(key TEXT PRIMARY KEY, json TEXT, ts INTEGER)")
            self._db = db
        except Exception:
            logger.debug("map cache unavailable", exc_info=True)
            self._broken = True
        return self._db

    def _remember(self, key, value):
        self._lru[key] = value
        self._lru.move_to_end(key)
        while len(self._lru) > LRU_SIZE:
            self._lru.popitem(last=False)

    def get_geo(self, key):
        now = _now()
        with self._lock:
            hit = self._lru.get("g:" + key)
            if hit is None:
                db = self._conn()
                row = None
                if db is not None:
                    try:
                        row = db.execute("SELECT lat, lng, precision, label, source, wiki, ts FROM geo WHERE key=?", (key,)).fetchone()
                    except Exception:
                        logger.debug("map cache read failed", exc_info=True)
                if row is None:
                    return None
                hit = {"lat": row[0], "lng": row[1], "precision": row[2] or "", "label": row[3] or "",
                       "source": row[4] or "", "wiki": row[5] or "", "ts": row[6] or 0}
                self._remember("g:" + key, hit)
            ttl = GEO_TTL_HIT if hit["lat"] is not None else GEO_TTL_MISS
            if now - hit["ts"] > ttl:
                self._lru.pop("g:" + key, None)
                return None
            return hit

    def put_geo(self, key, value):
        value = dict(value, ts=int(_now()))
        with self._lock:
            self._remember("g:" + key, value)
            db = self._conn()
            if db is None:
                return
            try:
                db.execute("INSERT OR REPLACE INTO geo(key, lat, lng, precision, label, source, wiki, ts) VALUES (?,?,?,?,?,?,?,?)",
                           (key, value.get("lat"), value.get("lng"), value.get("precision", ""), value.get("label", ""),
                            value.get("source", ""), value.get("wiki", ""), value["ts"]))
            except Exception:
                logger.debug("map cache write failed", exc_info=True)

    def get_photo(self, key):
        now = _now()
        with self._lock:
            hit = self._lru.get("p:" + key)
            if hit is None:
                db = self._conn()
                row = None
                if db is not None:
                    try:
                        row = db.execute("SELECT json, ts FROM photo WHERE key=?", (key,)).fetchone()
                    except Exception:
                        logger.debug("map cache read failed", exc_info=True)
                if row is None:
                    return None
                try:
                    hit = {"value": json.loads(row[0]), "ts": row[1] or 0}
                except ValueError:
                    return None
                self._remember("p:" + key, hit)
            ttl = PHOTO_TTL if hit["value"].get("found") else PHOTO_TTL_MISS
            if now - hit["ts"] > ttl:
                self._lru.pop("p:" + key, None)
                return None
            return hit["value"]

    def put_photo(self, key, value):
        hit = {"value": value, "ts": int(_now())}
        with self._lock:
            self._remember("p:" + key, hit)
            db = self._conn()
            if db is None:
                return
            try:
                db.execute("INSERT OR REPLACE INTO photo(key, json, ts) VALUES (?,?,?)",
                           (key, json.dumps(value, ensure_ascii=False), hit["ts"]))
            except Exception:
                logger.debug("map cache write failed", exc_info=True)


def _default_cache_path():
    from api.config import STATE_DIR
    return Path(STATE_DIR) / "map_cache.sqlite"


CACHE = _Cache()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(text or "")).lower()).strip()


def _geo_key(chain, lang, region, query) -> str:
    raw = "v1|" + ",".join(chain) + "|" + lang + "|" + ",".join(region) + "|" + _norm(query)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── Providers ───────────────────────────────────────────────────────────────

def _coords_ok(lat, lng) -> bool:
    return (isinstance(lat, (int, float)) and isinstance(lng, (int, float)) and not isinstance(lat, bool)
            and not isinstance(lng, bool) and math.isfinite(lat) and math.isfinite(lng)
            and -90 <= lat <= 90 and -180 <= lng <= 180)


def _label(text) -> str:
    return re.sub(r"[\x00-\x1f\x7f<>]", "", str(text or "")).strip()[:200]


_PDOK_PRECISION = {"adres": "address", "appartementsrecht": "address", "perceel": "place", "postcode": "street",
                   "weg": "street", "hectometerpaal": "place", "woonplaats": "city", "gemeente": "city",
                   "provincie": "city"}
_POINT_RE = re.compile(r"^\s*POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)\s*$", re.I)


def parse_pdok(payload):
    docs = (((payload or {}).get("response") or {}).get("docs") or []) if isinstance(payload, dict) else []
    if not docs or not isinstance(docs[0], dict):
        return None
    doc = docs[0]
    match = _POINT_RE.match(str(doc.get("centroide_ll") or ""))
    if not match:
        return None
    lng, lat = float(match.group(1)), float(match.group(2))
    if not _coords_ok(lat, lng):
        return None
    return {"lat": lat, "lng": lng, "precision": _PDOK_PRECISION.get(str(doc.get("type") or ""), "place"),
            "label": _label(doc.get("weergavenaam")), "source": "pdok", "wiki": ""}


def _pdok(query, deadline, agent):
    params = {"q": query, "rows": 1, "fl": "weergavenaam,centroide_ll,type,score"}
    if re.search(r"\d", query):
        # With a house number, ask for the address itself first: the free
        # search otherwise ranks the street above "Museumstraat 1".
        found = parse_pdok(_fetch_json(PDOK_URL + "?" + urllib.parse.urlencode(dict(params, fq="type:adres")), deadline, agent))
        if found:
            return found
    return parse_pdok(_fetch_json(PDOK_URL + "?" + urllib.parse.urlencode(params), deadline, agent))


def parse_nominatim(payload):
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        return None
    item = payload[0]
    try:
        lat, lng = float(item.get("lat")), float(item.get("lon"))
    except (TypeError, ValueError):
        return None
    if not _coords_ok(lat, lng):
        return None
    try:
        rank = int(item.get("place_rank") or 0)
    except (TypeError, ValueError):
        rank = 0
    precision = "address" if rank >= 28 else "street" if rank >= 26 else "place" if rank >= 17 else "city"
    wiki = ""
    extratags = item.get("extratags") if isinstance(item.get("extratags"), dict) else {}
    raw_wiki = str(extratags.get("wikipedia") or "")
    match = re.match(r"^([a-z]{2}):(.{1,160})$", raw_wiki)
    if match and match.group(1) in WIKI_HOSTS:
        wiki = match.group(1) + ":" + match.group(2)
    return {"lat": lat, "lng": lng, "precision": precision, "label": _label(item.get("display_name")),
            "source": "nominatim", "wiki": wiki}


def _nominatim(query, lang, region, deadline, agent, contact):
    params = {"q": query, "format": "jsonv2", "limit": 1, "accept-language": lang, "extratags": 1, "addressdetails": 0}
    if region:
        params["countrycodes"] = ",".join(region)
    if contact and "@" in contact:
        params["email"] = contact
    url = NOMINATIM_URL + "?" + urllib.parse.urlencode(params)
    return parse_nominatim(_fetch_json(url, deadline, agent))


_COMMONS_FILE_RE = re.compile(r"/wikipedia/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/]+)(?:/[^/]+)?")


_IMAGE_HOSTS = ("upload.wikimedia.org", "thumb.wikimedia.org")


def commons_image(url: str):
    """(url on upload.wikimedia.org without a query, Commons file name) or None.

    Wikipedia now hands out thumbnails on thumb.wikimedia.org with tracking
    parameters; the same path is served by upload.wikimedia.org, the only
    photo host the kit frame allows."""
    parts = urllib.parse.urlsplit(str(url or ""))
    if parts.scheme != "https" or parts.hostname not in _IMAGE_HOSTS or parts.port or parts.username:
        return None
    match = _COMMONS_FILE_RE.fullmatch(parts.path)
    if not match:
        return None
    return "https://upload.wikimedia.org" + parts.path, urllib.parse.unquote(match.group(1)).replace(" ", "_")


def commons_filename(url: str):
    image = commons_image(url)
    return image[1] if image else None


def _plain(value, limit):
    text = html.unescape(re.sub(r"<[^>]*>", "", str(value or "")))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def license_ok(name: str) -> bool:
    name = str(name or "").strip()
    return name.startswith("CC") or name.lower() in ("public domain", "pd")


def _wiki_summary(lang, title, deadline, agent, want_photo):
    """Coordinates and (optionally) a licensed photo for one article, cached."""
    key = lang + ":" + title
    cached = CACHE.get_photo(key)
    if cached is not None and (cached.get("photo_checked") or not want_photo):
        return cached
    host = WIKI_HOSTS[lang]
    url = f"https://{host}/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"), safe="")
    out = {"found": False, "lat": None, "lng": None, "photo": None, "photo_checked": want_photo}
    data = _fetch_json(url, deadline, agent, follow_same_host=True)
    if not isinstance(data, dict):
        CACHE.put_photo(key, out)
        return out
    coords = data.get("coordinates") if isinstance(data.get("coordinates"), dict) else {}
    lat, lng = coords.get("lat"), coords.get("lon")
    if _coords_ok(lat, lng):
        out.update(found=True, lat=float(lat), lng=float(lng))
    canonical = str(((data.get("titles") or {}) if isinstance(data.get("titles"), dict) else {}).get("canonical") or title.replace(" ", "_"))
    if want_photo:
        out["photo"] = _commons_photo(data, lang, canonical, deadline, agent)
        if out["photo"]:
            out["found"] = True
    CACHE.put_photo(key, out)
    return out


def _commons_photo(summary, lang, canonical, deadline, agent):
    thumb = (summary.get("thumbnail") or {}) if isinstance(summary.get("thumbnail"), dict) else {}
    original = (summary.get("originalimage") or {}) if isinstance(summary.get("originalimage"), dict) else {}
    image, full = commons_image(thumb.get("source")), commons_image(original.get("source"))
    if not image or not full or image[1] != full[1]:
        return None  # thumbnail and original must be the same Commons file
    image, filename = image
    if not image.startswith(PHOTO_PREFIX) or re.search(r"[\s\"'<>\\]", image):
        return None
    url = COMMONS_API_URL + "?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": 2, "prop": "imageinfo", "iiprop": "extmetadata",
        "iiextmetadatafilter": "Artist|LicenseShortName", "titles": "File:" + filename})
    meta = _fetch_json(url, deadline, agent)
    pages = ((meta or {}).get("query") or {}).get("pages") or []
    if isinstance(pages, dict):
        pages = list(pages.values())
    info = {}
    if pages and isinstance(pages[0], dict):
        infos = pages[0].get("imageinfo") or [{}]
        info = (infos[0] or {}).get("extmetadata") or {}
    license_name = _plain((info.get("LicenseShortName") or {}).get("value"), 60)
    artist = _plain((info.get("Artist") or {}).get("value"), 120)
    if not artist or not license_ok(license_name):
        return None
    try:
        width, height = int(thumb.get("width") or 0), int(thumb.get("height") or 0)
    except (TypeError, ValueError):
        width = height = 0
    return {"url": image, "w": width, "h": height, "artist": artist, "license": license_name,
            "credit_url": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(filename, safe=""),
            "article_url": f"https://{WIKI_HOSTS[lang]}/wiki/" + urllib.parse.quote(canonical, safe="")}


# ── Request ─────────────────────────────────────────────────────────────────

class BadRequest(ValueError):
    pass


_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,8}$")
_WIKI_RE = re.compile(r"^(nl|en|de|fr):([^\x00-\x1f<>\[\]{}|#]{1,160})$")


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_request(body) -> dict:
    if not isinstance(body, dict) or body.get("v") != 1:
        raise BadRequest("version")
    places = body.get("places")
    if not isinstance(places, list) or not 1 <= len(places) <= MAX_PLACES:
        raise BadRequest("places")
    region = body.get("region", ["nl"])
    if isinstance(region, str):
        region = [region]
    if not isinstance(region, list) or len(region) > 5 or not all(isinstance(r, str) and re.fullmatch(r"[a-z]{2}", r) for r in region):
        raise BadRequest("region")
    lang = body.get("lang", "nl")
    if lang not in ("nl", "en"):
        raise BadRequest("lang")
    photos = body.get("photos", False)
    if not isinstance(photos, bool):
        raise BadRequest("photos")
    out, seen = [], set()
    for item in places:
        if not isinstance(item, dict):
            raise BadRequest("place")
        key, name = item.get("k"), item.get("name")
        if not isinstance(key, str) or not _KEY_RE.match(key) or key in seen:
            raise BadRequest("key")
        seen.add(key)
        if not isinstance(name, str) or not name.strip() or len(name) > MAX_NAME:
            raise BadRequest("name")
        query = item.get("q", name)
        if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY:
            raise BadRequest("query")
        place = {"k": key, "name": name.strip(), "q": query.strip(), "lat": None, "lng": None, "wiki": ""}
        has_lat, has_lng = "lat" in item, "lng" in item
        if has_lat or has_lng:
            if not (has_lat and has_lng and _finite(item["lat"]) and _finite(item["lng"]) and _coords_ok(item["lat"], item["lng"])):
                raise BadRequest("coordinates")
            place["lat"], place["lng"] = float(item["lat"]), float(item["lng"])
        wiki = item.get("wiki")
        if wiki is not None:
            match = _WIKI_RE.match(wiki) if isinstance(wiki, str) else None
            if not match:
                raise BadRequest("wiki")
            place["wiki"] = wiki
        out.append(place)
    return {"places": out, "region": region or ["nl"], "lang": lang, "photos": photos}


def _transient(exc) -> bool:
    """Whether a failed lookup is worth trying again later (never cached)."""
    if isinstance(exc, _Deadline):
        return True
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code not in (400, 404, 410)
    return isinstance(exc, (urllib.error.URLError, OSError, ValueError))


def _lookup(place, chain, lang, region, deadline, agent, contact, budget):
    """(found, later) for one place without given coordinates."""
    later = False
    if "pdok" in chain and "nl" in region and _norm(place["q"]) != _norm(place["name"]):
        # PDOK knows addresses; a bare name ("Rijksmuseum") goes to Nominatim.
        try:
            found = _pdok(place["q"], deadline, agent)
            if found:
                return found, False
        except Exception as exc:  # noqa: BLE001 - a provider failure must not end the request
            later = later or _transient(exc)
    if "nominatim" in chain:
        if budget["nominatim"] > 0 and _nominatim_slot(deadline):
            budget["nominatim"] -= 1
            try:
                found = _nominatim(place["q"], lang, region, deadline, agent, contact)
                if found:
                    return found, False
            except Exception as exc:  # noqa: BLE001
                later = later or _transient(exc)
        else:
            later = True
    if place["wiki"]:
        try:
            wl, wt = place["wiki"].split(":", 1)
            summary = _wiki_summary(wl, wt, deadline, agent, False)
            if summary.get("lat") is not None:
                return {"lat": summary["lat"], "lng": summary["lng"], "precision": "place", "label": "",
                        "source": "wikipedia", "wiki": place["wiki"]}, False
        except Exception as exc:  # noqa: BLE001
            later = later or _transient(exc)
    return None, later


def resolve(request: dict, config_data=None) -> tuple[dict, dict]:
    """Resolve one validated request; returns (response, counts)."""
    if config_data is None:
        config_data = _config()
    chain = geocoders(config_data)
    agent = user_agent(config_data)
    contact = str(_setting(config_data, "webui_map_contact", "HERMES_WEBUI_MAP_CONTACT") or "").strip()
    deadline = _clock() + REQUEST_DEADLINE
    lang, region = request["lang"], request["region"]
    counts = {"places": len(request["places"]), "given": 0, "cached": 0, "looked_up": 0, "not_found": 0, "later": 0, "photos": 0}
    used = set()
    budget = {"nominatim": NOMINATIM_PER_REQUEST}
    # With outside lookups off nothing leaves this server, photos included.
    photos_left = MAX_PHOTOS if request["photos"] and chain else 0
    results = []
    for place in request["places"]:
        result = {"k": place["k"], "status": "not_found"}
        found = None
        if place["lat"] is not None:
            found = {"lat": place["lat"], "lng": place["lng"], "precision": "given", "label": "", "source": "given", "wiki": ""}
            counts["given"] += 1
        elif chain:
            key = _geo_key(chain, lang, region, place["q"] + "|" + place["wiki"])
            cached = CACHE.get_geo(key)
            if cached is not None:
                counts["cached"] += 1
                found = cached if cached.get("lat") is not None else None
            else:
                found, later = _lookup(place, chain, lang, region, deadline, agent, contact, budget)
                if found is not None:
                    counts["looked_up"] += 1
                    CACHE.put_geo(key, found)
                elif later:
                    result["status"] = "later"
                else:
                    CACHE.put_geo(key, {"lat": None, "lng": None, "precision": "", "label": "", "source": "", "wiki": ""})
        if found is not None:
            used.add(found.get("source") or "")
            result.update(status="ok", lat=found["lat"], lng=found["lng"], precision=found.get("precision") or "place",
                          source=found.get("source") or "", label=found.get("label") or "")
        wiki = place["wiki"] or (found or {}).get("wiki") or ""
        if photos_left > 0 and wiki and result["status"] == "ok":
            photos_left -= 1
            try:
                wl, wt = wiki.split(":", 1)
                summary = _wiki_summary(wl, wt, deadline, agent, True)
                if summary.get("photo"):
                    result["photo"] = summary["photo"]
                    counts["photos"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.debug("map photo failed: %s", type(exc).__name__)
        if result["status"] == "not_found":
            counts["not_found"] += 1
        elif result["status"] == "later":
            counts["later"] += 1
        results.append(result)
    attribution = []
    if "pdok" in used:
        attribution.append("Kadaster / PDOK")
    if "nominatim" in used:
        attribution.append("\u00a9 OpenStreetMap" + ("-bijdragers" if lang == "nl" else " contributors"))
    if "wikipedia" in used:
        attribution.append("Wikipedia")
    if counts["photos"]:
        attribution.append("Wikimedia Commons")
    return {"places": results, "tiles": tiles(config_data), "attribution": attribution}, counts


# ── Rate limits ─────────────────────────────────────────────────────────────

_RATE_LOCK = threading.Lock()
_rate_calls: dict = {}
_rate_places: dict = {}


def _rate_key(handler) -> str:
    """Copied from api/ops_reporter.py: the signed-in user, else the client address."""
    try:
        from api.ownership import request_owner_email

        email = request_owner_email(handler)
        if email:
            return "user:" + str(email).strip().lower()
    except Exception:
        pass
    try:
        address = getattr(handler, "client_address", None)
        if address:
            return "ip:" + str(address[0])
    except Exception:
        pass
    return "anonymous"


def rate_limited(key: str, places: int, now: float | None = None) -> int:
    """Seconds to wait, or 0 when this call may go ahead (and is counted)."""
    now = _now() if now is None else now
    with _RATE_LOCK:
        calls = [t for t in _rate_calls.get(key, ()) if t > now - RATE_WINDOW]
        spent = [(t, n) for t, n in _rate_places.get(key, ()) if t > now - PLACES_WINDOW]
        if len(calls) >= RATE_REQUESTS:
            _rate_calls[key] = calls
            return max(1, int(math.ceil(calls[0] + RATE_WINDOW - now)))
        if sum(n for _, n in spent) + places > RATE_PLACES:
            _rate_places[key] = spent
            return max(1, int(math.ceil(spent[0][0] + PLACES_WINDOW - now))) if spent else int(PLACES_WINDOW)
        calls.append(now)
        spent.append((now, places))
        _rate_calls[key], _rate_places[key] = calls, spent
        for table in (_rate_calls, _rate_places):
            while len(table) > _RATE_MAX_KEYS:
                del table[next(iter(table))]
    return 0


# ── Handler ─────────────────────────────────────────────────────────────────

def _send(handler, payload, status=200, headers=None):
    from api.helpers import j
    j(handler, payload, status=status, extra_headers=headers)
    return True


def handle(handler) -> bool:
    """``POST /api/map/resolve``. Never raises; never logs place names or addresses."""
    try:
        raw_length = handler.headers.get("Content-Length") if getattr(handler, "headers", None) is not None else None
        try:
            length = int(raw_length) if raw_length not in (None, "") else 0
        except (TypeError, ValueError):
            length = -1
        if length < 0:
            handler.close_connection = True
            return _send(handler, {"error": "invalid_content_length"}, 400)
        if length > MAX_BODY:
            handler.close_connection = True
            return _send(handler, {"error": "too_large"}, 413)
        raw = handler.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
            request = parse_request(body)
        except (UnicodeDecodeError, ValueError):
            return _send(handler, {"error": "invalid_request"}, 400)
        wait = rate_limited(_rate_key(handler), len(request["places"]))
        if wait:
            return _send(handler, {"error": "rate_limited"}, 429, {"Retry-After": str(wait)})
        response, counts = resolve(request)
        logger.info("map resolve: %(places)d places, %(given)d given, %(cached)d cached, %(looked_up)d looked up, "
                    "%(not_found)d not found, %(later)d later, %(photos)d photos", counts)
        return _send(handler, response)
    except Exception:
        logger.warning("map resolve failed", exc_info=False)
        try:
            return _send(handler, {"error": "unavailable"}, 500)
        except Exception:
            return True
