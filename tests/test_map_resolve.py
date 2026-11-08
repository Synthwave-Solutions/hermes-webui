"""POST /api/map/resolve (api/map_resolve.py) with a mocked network.

No test here reaches the internet: ``map_resolve._open`` is replaced by a
fake that answers per host and records every request. One test talks to a
local HTTP server to prove that the real opener never follows a redirect.
"""

from __future__ import annotations

import io
import json
import logging
import threading
import time
import urllib.error
import urllib.parse
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from api import map_resolve as mr

PDOK_HIT = {"response": {"numFound": 1, "docs": [{"weergavenaam": "Taurusavenue 1, 2132LS Hoofddorp",
                                                  "centroide_ll": "POINT(4.68786 52.29587)", "type": "adres", "score": 14.2}]}}
NOMINATIM_HIT = [{"lat": "52.3599976", "lon": "4.8852188", "place_rank": 30, "display_name": "Rijksmuseum, Museumstraat 1, Amsterdam",
                  "extratags": {"wikipedia": "nl:Rijksmuseum"}}]
THUMB = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Rijksmuseum_2019.jpg/320px-Rijksmuseum_2019.jpg"
ORIGINAL = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Rijksmuseum_2019.jpg"
SUMMARY = {"titles": {"canonical": "Rijksmuseum"}, "coordinates": {"lat": 52.36, "lon": 4.885},
           "thumbnail": {"source": THUMB, "width": 320, "height": 213}, "originalimage": {"source": ORIGINAL}}
COMMONS = {"query": {"pages": [{"imageinfo": [{"extmetadata": {
    "LicenseShortName": {"value": "CC BY-SA 4.0"},
    "Artist": {"value": '<a href="//commons.wikimedia.org/wiki/User:Jan">Jan &amp; <b>Piet</b></a>' + " x" * 100}}}]}]}}


class FakeNet:
    def __init__(self):
        self.calls = []
        self.answers = {}
        self.lock = threading.Lock()

    def set(self, host, answer):
        self.answers[host] = answer

    def __call__(self, request, timeout):
        url = request.full_url
        host = urllib.parse.urlsplit(url).hostname
        with self.lock:
            self.calls.append({"url": url, "host": host, "agent": request.get_header("User-agent"), "t": time.monotonic(),
                               "timeout": timeout})
        answer = self.answers.get(host)
        if callable(answer):
            answer = answer(url)
        if isinstance(answer, BaseException):
            raise answer
        if answer is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", Message(), None)
        return 200, json.dumps(answer).encode("utf-8")

    def hosts(self):
        return [c["host"] for c in self.calls]


@pytest.fixture
def net(monkeypatch, tmp_path):
    fake = FakeNet()
    monkeypatch.setattr(mr, "_open", fake)
    monkeypatch.setattr(mr, "CACHE", mr._Cache(tmp_path / "map_cache.sqlite"))
    monkeypatch.setattr(mr, "_nomi", {"last": -1e9, "day": "", "count": 0})
    mr._rate_calls.clear()
    mr._rate_places.clear()
    for env in ("HERMES_WEBUI_MAP_GEOCODER", "HERMES_WEBUI_MAP_CONTACT", "HERMES_WEBUI_MAP_TILES"):
        monkeypatch.delenv(env, raising=False)
    return fake


def request(*places, photos=False, region=("nl",), lang="nl"):
    return mr.parse_request({"v": 1, "lang": lang, "region": list(region), "photos": photos,
                             "places": [dict({"k": str(i)}, **p) for i, p in enumerate(places)]})


ON = {"webui_map_contact": "ops@example.test"}


# ── Lookups ─────────────────────────────────────────────────────────────────

def test_pdok_answers_dutch_addresses_and_its_point_is_parsed(net):
    net.set("api.pdok.nl", PDOK_HIT)
    out, counts = mr.resolve(request({"name": "Kantoor", "q": "Taurusavenue 1, Hoofddorp"}), ON)
    place = out["places"][0]
    assert place == {"k": "0", "status": "ok", "lat": 52.29587, "lng": 4.68786, "precision": "address", "source": "pdok",
                     "label": "Taurusavenue 1, 2132LS Hoofddorp"}
    assert net.hosts() == ["api.pdok.nl"]
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(net.calls[0]["url"]).query)
    assert query["q"] == ["Taurusavenue 1, Hoofddorp"] and query["rows"] == ["1"]
    assert out["attribution"] == ["Kadaster / PDOK"]
    assert counts["looked_up"] == 1


@pytest.mark.parametrize("payload,expected", [
    ({"response": {"docs": [{"centroide_ll": "POINT(5.1 52.09)", "type": "woonplaats", "weergavenaam": "Utrecht"}]}}, (52.09, 5.1, "city")),
    ({"response": {"docs": [{"centroide_ll": "POINT(4.9 52.37)", "type": "weg"}]}}, (52.37, 4.9, "street")),
    ({"response": {"docs": [{"centroide_ll": "POINT(999 52)", "type": "adres"}]}}, None),
    ({"response": {"docs": [{"centroide_ll": "POLYGON((1 2))"}]}}, None),
    ({"response": {"docs": []}}, None),
    ([], None),
])
def test_pdok_parsing(payload, expected):
    got = mr.parse_pdok(payload)
    assert (got and (got["lat"], got["lng"], got["precision"])) == expected or (got is None and expected is None)


def test_a_bare_name_skips_pdok_and_uses_nominatim_with_an_identifying_agent(net):
    net.set("nominatim.openstreetmap.org", NOMINATIM_HIT)
    out, _ = mr.resolve(request({"name": "Rijksmuseum", "q": "Rijksmuseum"}), ON)
    assert net.hosts() == ["nominatim.openstreetmap.org"]
    call = net.calls[0]
    assert call["agent"] == "SynthwaveSuperAgent/1.0 (+https://synthwave.solutions; ops@example.test)"
    assert "python-urllib" not in call["agent"].lower()
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(call["url"]).query)
    assert query["format"] == ["jsonv2"] and query["countrycodes"] == ["nl"] and query["email"] == ["ops@example.test"]
    assert query["extratags"] == ["1"] and query["limit"] == ["1"]
    assert out["places"][0]["status"] == "ok" and out["places"][0]["precision"] == "address"
    assert out["attribution"] == ["© OpenStreetMap-bijdragers"]
    assert call["timeout"] <= mr.CALL_TIMEOUT


def test_every_outgoing_call_identifies_itself(net):
    net.set("api.pdok.nl", {"response": {"docs": []}})
    net.set("nominatim.openstreetmap.org", [])
    net.set("nl.wikipedia.org", SUMMARY)
    net.set("commons.wikimedia.org", COMMONS)
    mr.resolve(request({"name": "Kantoor", "q": "Dorpsstraat 1, Ergens", "wiki": "nl:Rijksmuseum"}, photos=True), {})
    assert set(net.hosts()) == {"api.pdok.nl", "nominatim.openstreetmap.org", "nl.wikipedia.org", "commons.wikimedia.org"}
    assert all(c["agent"] == mr.USER_AGENT for c in net.calls)


def test_given_coordinates_need_no_lookup(net):
    out, counts = mr.resolve(request({"name": "Dam", "q": "Dam", "lat": 52.3731, "lng": 4.8926}), ON)
    assert out["places"][0]["precision"] == "given" and net.calls == []
    assert counts["given"] == 1


def test_nominatim_is_spaced_for_the_whole_process(net):
    net.set("nominatim.openstreetmap.org", NOMINATIM_HIT)
    errors = []

    def one(i):
        try:
            mr.resolve(request({"name": f"Plek {i}", "q": f"Plek {i}"}), ON)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=one, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(20)
    assert not errors
    times = sorted(c["t"] for c in net.calls if c["host"] == "nominatim.openstreetmap.org")
    assert len(times) == 3
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert all(g >= mr.NOMINATIM_SPACING - 0.01 for g in gaps), gaps


def test_at_most_eight_uncached_nominatim_lookups_per_call(net, monkeypatch):
    monkeypatch.setattr(mr, "NOMINATIM_SPACING", 0.0)
    net.set("nominatim.openstreetmap.org", NOMINATIM_HIT)
    out, counts = mr.resolve(request(*({"name": f"Plek {i}", "q": f"Plek {i}"} for i in range(11))), ON)
    statuses = [p["status"] for p in out["places"]]
    assert statuses == ["ok"] * 8 + ["later"] * 3
    assert counts["later"] == 3


def test_the_daily_budget_turns_lookups_into_later(net, monkeypatch):
    net.set("nominatim.openstreetmap.org", NOMINATIM_HIT)
    monkeypatch.setattr(mr, "_nomi", {"last": -1e9, "day": time.strftime("%Y-%m-%d", time.gmtime()), "count": mr.NOMINATIM_PER_DAY})
    out, _ = mr.resolve(request({"name": "Plek", "q": "Plek"}), ON)
    assert out["places"][0]["status"] == "later" and net.calls == []


def test_failures_are_later_and_not_cached_but_misses_are(net):
    net.set("nominatim.openstreetmap.org", urllib.error.URLError("timed out"))
    out, _ = mr.resolve(request({"name": "Plek", "q": "Plek"}), ON)
    assert out["places"][0]["status"] == "later"
    net.set("nominatim.openstreetmap.org", [])
    out, _ = mr.resolve(request({"name": "Plek", "q": "Plek"}), ON)
    assert out["places"][0]["status"] == "not_found"
    before = len(net.calls)
    out, counts = mr.resolve(request({"name": "Plek", "q": "Plek"}), ON)
    assert out["places"][0]["status"] == "not_found" and len(net.calls) == before and counts["cached"] == 1


def test_cache_ttls(net, monkeypatch):
    net.set("nominatim.openstreetmap.org", NOMINATIM_HIT)
    clock = {"now": 1_800_000_000.0}
    monkeypatch.setattr(mr, "_now", lambda: clock["now"])
    req = request({"name": "Rijksmuseum", "q": "Rijksmuseum"})
    mr.resolve(req, ON)
    assert len(net.calls) == 1
    clock["now"] += 179 * 86400
    mr.CACHE._lru.clear()  # read back from SQLite
    mr.resolve(req, ON)
    assert len(net.calls) == 1, "a hit is kept for 180 days"
    clock["now"] += 2 * 86400
    mr.resolve(req, ON)
    assert len(net.calls) == 2, "and looked up again after that"
    # A miss is kept for one day.
    net.set("nominatim.openstreetmap.org", [])
    miss = request({"name": "Nergens", "q": "Nergens"})
    mr.resolve(miss, ON)
    clock["now"] += 23 * 3600
    mr.resolve(miss, ON)
    assert len(net.calls) == 3
    clock["now"] += 2 * 3600
    mr.resolve(miss, ON)
    assert len(net.calls) == 4


def test_the_lru_stays_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "LRU_SIZE", 5)
    cache = mr._Cache(tmp_path / "c.sqlite")
    for i in range(12):
        cache.put_geo(f"k{i}", {"lat": 1.0, "lng": 2.0})
    assert len(cache._lru) == 5
    assert cache.get_geo("k0")["lat"] == 1.0, "older entries still come from SQLite"


# ── Geocoder switch ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    (None, ("pdok", "nominatim")), ("off", ()), (False, ()), ("none", ()), ("pdok", ("pdok",)),
    ("nominatim, pdok", ("nominatim", "pdok")), (["pdok"], ("pdok",)), ("pdok,photon", ()), ("of", ()), (42, ()),
])
def test_geocoder_setting_fails_closed(value, expected, monkeypatch):
    monkeypatch.delenv("HERMES_WEBUI_MAP_GEOCODER", raising=False)
    config = {} if value is None else {"webui_map_geocoder": value}
    assert mr.geocoders(config) == expected


def test_geocoder_off_sends_nothing_out(net):
    net.set("nominatim.openstreetmap.org", NOMINATIM_HIT)
    req = request({"name": "Dam", "q": "Dam", "lat": 52.37, "lng": 4.89}, {"name": "Kantoor", "q": "Dorpsstraat 1",
                  "wiki": "nl:Rijksmuseum"}, photos=True)
    out, counts = mr.resolve(req, {"webui_map_geocoder": "off"})
    assert net.calls == []
    assert [p["status"] for p in out["places"]] == ["ok", "not_found"]
    assert "photo" not in out["places"][0] and out["attribution"] == []


def test_the_environment_overrides_the_setting(net, monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_MAP_GEOCODER", "off")
    assert mr.geocoders({"webui_map_geocoder": "pdok"}) == ()


# ── Photos (license gate ported from Open Intelligent UI) ───────────────────

def test_a_licensed_commons_photo_comes_with_its_credit(net):
    net.set("nominatim.openstreetmap.org", NOMINATIM_HIT)
    net.set("nl.wikipedia.org", SUMMARY)
    net.set("commons.wikimedia.org", COMMONS)
    out, counts = mr.resolve(request({"name": "Rijksmuseum", "q": "Rijksmuseum"}, photos=True), ON)
    photo = out["places"][0]["photo"]
    assert photo["url"] == THUMB and photo["license"] == "CC BY-SA 4.0"
    assert photo["artist"].startswith("Jan & Piet") and len(photo["artist"]) <= 120 and "<" not in photo["artist"]
    assert photo["credit_url"] == "https://commons.wikimedia.org/wiki/File:Rijksmuseum_2019.jpg"
    assert photo["article_url"] == "https://nl.wikipedia.org/wiki/Rijksmuseum"
    assert "Wikimedia Commons" in out["attribution"] and counts["photos"] == 1
    commons = next(c for c in net.calls if c["host"] == "commons.wikimedia.org")
    assert urllib.parse.parse_qs(urllib.parse.urlsplit(commons["url"]).query)["titles"] == ["File:Rijksmuseum_2019.jpg"]


@pytest.mark.parametrize("change", [
    {"meta": {"LicenseShortName": {"value": "Copyrighted"}, "Artist": {"value": "Jan"}}},
    {"meta": {"LicenseShortName": {"value": "CC BY 4.0"}, "Artist": {"value": "  "}}},
    {"summary": {"originalimage": {"source": "https://upload.wikimedia.org/wikipedia/commons/b/bc/Other.jpg"}}},
    {"summary": {"thumbnail": {"source": "https://upload.wikimedia.org/wikipedia/nl/a/ab/Local.jpg"},
                 "originalimage": {"source": "https://upload.wikimedia.org/wikipedia/nl/a/ab/Local.jpg"}}},
    {"summary": {"thumbnail": {"source": "https://evil.example/wikipedia/commons/a/ab/X.jpg"}}},
])
def test_no_photo_without_a_free_license_and_a_matching_commons_file(net, change):
    summary = json.loads(json.dumps(SUMMARY))
    summary.update(change.get("summary", {}))
    commons = {"query": {"pages": [{"imageinfo": [{"extmetadata": change["meta"]}]}]}} if "meta" in change else COMMONS
    net.set("nominatim.openstreetmap.org", NOMINATIM_HIT)
    net.set("nl.wikipedia.org", summary)
    net.set("commons.wikimedia.org", commons)
    out, _ = mr.resolve(request({"name": "Rijksmuseum", "q": "Rijksmuseum"}, photos=True), ON)
    assert out["places"][0]["status"] == "ok" and "photo" not in out["places"][0]


def test_photos_are_capped_per_map(net, monkeypatch):
    monkeypatch.setattr(mr, "NOMINATIM_SPACING", 0.0)
    net.set("nl.wikipedia.org", SUMMARY)
    net.set("commons.wikimedia.org", COMMONS)
    places = [{"name": f"P{i}", "q": f"P{i}", "lat": 52.0, "lng": 4.0 + i / 100, "wiki": f"nl:P{i}"} for i in range(10)]
    out, counts = mr.resolve(request(*places, photos=True), ON)
    assert counts["photos"] == mr.MAX_PHOTOS == 8
    assert sum("photo" in p for p in out["places"]) == 8


def test_wikipedia_coordinates_are_the_last_resort(net):
    net.set("nominatim.openstreetmap.org", [])
    net.set("nl.wikipedia.org", SUMMARY)
    out, _ = mr.resolve(request({"name": "Rijks", "q": "Rijks", "wiki": "nl:Rijksmuseum"}), ON)
    assert out["places"][0]["source"] == "wikipedia" and out["places"][0]["precision"] == "place"
    assert out["attribution"] == ["Wikipedia"]


def test_a_renamed_article_is_followed_only_on_the_same_host(net):
    target = "https://nl.wikipedia.org/api/rest_v1/page/summary/Rijksmuseum_Amsterdam"

    def wiki(url):
        if url.endswith("/Rijks"):
            headers = Message()
            headers["Location"] = "Rijksmuseum_Amsterdam"
            return urllib.error.HTTPError(url, 302, "Found", headers, None)
        return SUMMARY if url == target else None
    net.set("nl.wikipedia.org", wiki)
    net.set("nominatim.openstreetmap.org", [])
    out, _ = mr.resolve(request({"name": "R", "q": "R", "wiki": "nl:Rijks"}), ON)
    assert out["places"][0]["status"] == "ok" and net.calls[-1]["url"] == target

    def elsewhere(url):
        headers = Message()
        headers["Location"] = "https://evil.example/x"
        return urllib.error.HTTPError(url, 302, "Found", headers, None)
    net.set("nl.wikipedia.org", elsewhere)
    out, _ = mr.resolve(request({"name": "S", "q": "S", "wiki": "nl:Sneek"}), ON)
    assert out["places"][0]["status"] != "ok"
    assert "evil.example" not in net.hosts()


# ── Network safety ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "http://api.pdok.nl/x", "https://evil.example/x", "https://user:pw@api.pdok.nl/x", "https://api.pdok.nl:8443/x",
    "https://api.pdok.nl.evil.example/x", "file:///etc/passwd",
])
def test_only_fixed_https_hosts_are_called(url, net):
    with pytest.raises(ValueError):
        mr._fetch_json(url, time.monotonic() + 5, mr.USER_AGENT)
    assert net.calls == []


def test_the_real_opener_never_follows_a_redirect():
    class Redirect(BaseHTTPRequestHandler):
        def log_message(self, *_a):
            return

        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/elsewhere")
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as err:
            mr._OPENER.open(f"http://127.0.0.1:{server.server_address[1]}/start", timeout=5)
        assert err.value.code == 302
    finally:
        server.shutdown()
        server.server_close()


def test_large_answers_are_refused(net, monkeypatch):
    monkeypatch.setattr(mr, "_open", lambda request, timeout: (200, b"[" + b"1," * (mr.MAX_RESPONSE // 2) + b"1]"))
    with pytest.raises(ValueError):
        mr._fetch_json("https://api.pdok.nl/x", time.monotonic() + 5, mr.USER_AGENT)


def test_the_request_deadline_stops_lookups(net, monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(mr, "_clock", lambda: clock["t"])

    def slow(url):
        clock["t"] += 11.8
        return {"response": {"docs": []}}
    net.set("api.pdok.nl", slow)
    net.set("nominatim.openstreetmap.org", NOMINATIM_HIT)
    out, _ = mr.resolve(request({"name": "A", "q": "Straat 1, A"}, {"name": "B", "q": "Straat 2, B"}), {"webui_map_geocoder": "pdok"})
    assert [p["status"] for p in out["places"]] == ["not_found", "later"]


# ── Request checks ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("body", [
    None, [], {"v": 2, "places": [{"k": "0", "name": "A"}]}, {"v": 1, "places": []},
    {"v": 1, "places": [{"k": str(i), "name": "A"} for i in range(26)]},
    {"v": 1, "places": [{"k": "0", "name": "A", "lat": 52}]},
    {"v": 1, "places": [{"k": "0", "name": "A", "lat": 95, "lng": 4}]},
    {"v": 1, "places": [{"k": "0", "name": "A", "lat": float("nan"), "lng": 4}]},
    {"v": 1, "places": [{"k": "0", "name": "A", "lat": True, "lng": 4}]},
    {"v": 1, "places": [{"k": "0", "name": "A", "wiki": "xx:Foo"}]},
    {"v": 1, "places": [{"k": "0", "name": "A", "q": "x" * 201}]},
    {"v": 1, "places": [{"k": "0", "name": "x" * 81}]},
    {"v": 1, "places": [{"k": "0", "name": "A"}, {"k": "0", "name": "B"}]},
    {"v": 1, "places": [{"k": "../x", "name": "A"}]},
    {"v": 1, "region": ["nl", "NLD"], "places": [{"k": "0", "name": "A"}]},
    {"v": 1, "photos": "yes", "places": [{"k": "0", "name": "A"}]},
])
def test_bad_requests_are_refused(body):
    with pytest.raises(mr.BadRequest):
        mr.parse_request(body)


def test_tile_setting_is_checked():
    assert mr.tiles({})["url"] == mr.DEFAULT_TILES["url"]
    assert mr.tiles({"webui_map_tiles": "https://t.example.nl/{z}/{x}/{y}.png"})["url"] == "https://t.example.nl/{z}/{x}/{y}.png"
    custom = mr.tiles({"webui_map_tiles": {"url": "https://t.example.nl/{z}/{x}/{y}.png", "attribution": "<b>Eigen</b>", "maxZoom": 99}})
    assert custom["attribution"] == "bEigen/b" and custom["maxZoom"] == 20
    for bad in ("http://t.example/{z}/{x}/{y}.png", "https://t.example/{z}/{x}.png", "https://t.example/{z}/{x}/{y}.png?key={k}", 5):
        assert mr.tiles({"webui_map_tiles": bad})["url"] == mr.DEFAULT_TILES["url"], bad


# ── The endpoint ────────────────────────────────────────────────────────────

class Handler:
    def __init__(self, body: bytes, address=("10.0.0.7", 5000)):
        self.headers = {"Content-Length": str(len(body))}
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.client_address = address
        self.status = None
        self.sent = {}
        self.close_connection = False

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.sent[name] = value

    def end_headers(self):
        pass

    def json(self):
        return json.loads(self.wfile.getvalue())


def call(body, address=("10.0.0.7", 5000)):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    handler = Handler(raw, address)
    assert mr.handle(handler) is True
    return handler


def test_the_endpoint_answers_and_logs_counts_only(net, monkeypatch, caplog):
    monkeypatch.setattr(mr, "_config", lambda: {"webui_map_geocoder": "pdok"})
    net.set("api.pdok.nl", PDOK_HIT)
    secret = "Geheimstraat 13, Hoofddorp"
    with caplog.at_level(logging.DEBUG, logger="api.map_resolve"):
        handler = call({"v": 1, "lang": "nl", "places": [{"k": "0", "name": "Familie de Boer", "q": secret}]})
    assert handler.status == 200
    data = handler.json()
    assert data["places"][0]["status"] == "ok" and data["tiles"]["url"] == mr.DEFAULT_TILES["url"]
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "1 places" in logged and "1 looked up" in logged
    assert secret not in logged and "Geheimstraat" not in logged and "Boer" not in logged


def test_the_endpoint_rate_limits_per_user(net, monkeypatch):
    monkeypatch.setattr(mr, "_config", lambda: {"webui_map_geocoder": "off"})
    body = {"v": 1, "places": [{"k": "0", "name": "A", "lat": 52.0, "lng": 4.0}]}
    for _ in range(mr.RATE_REQUESTS):
        assert call(body).status == 200
    limited = call(body)
    assert limited.status == 429 and int(limited.sent["Retry-After"]) >= 1
    assert call(body, ("10.0.0.8", 5000)).status == 200, "another user is not affected"


def test_places_per_hour_are_limited():
    now = 1000.0
    for i in range(12):
        assert mr.rate_limited("user:a", 25, now + i * 61) == 0
    wait = mr.rate_limited("user:a", 25, now + 12 * 61)
    assert wait > 0, "300 places an hour"
    assert mr.rate_limited("user:b", 25, now) == 0


@pytest.mark.parametrize("raw,status", [
    (b"{not json", 400), (json.dumps({"v": 1, "places": [{"k": str(i), "name": "A"} for i in range(26)]}).encode(), 400),
    (b"x" * (mr.MAX_BODY + 1), 413),
])
def test_the_endpoint_refuses_bad_bodies(raw, status, net):
    handler = call(raw)
    assert handler.status == status
    if status == 413:
        assert handler.close_connection is True
