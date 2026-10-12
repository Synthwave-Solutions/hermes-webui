"""Authenticated, explicitly granted Bot Screens; no public RFB port.

The existing engine owns desktops and the durable human lease. This adapter
owns WebUI authorization, confirmation challenges, audit and WebSocket lifetime.
A human lease hides frames from all other viewers, including after link loss.
"""
from contextlib import contextmanager
import hashlib
import secrets
import socket
import select
import threading
import time
from urllib.parse import parse_qs, urlsplit

from api import auth
from api.governance import loader
from api.governance.audit import append_audit_event
from api.helpers import j

_LOCK = threading.RLock()
_CHALLENGES = {}
_SCREEN_LOCKS = {}
_STREAMS = threading.BoundedSemaphore(8)


class ScreenError(Exception):
    def __init__(self, code, status=403):
        self.code, self.status = code, status


def _identity(handler):
    cookie = auth.parse_cookie(handler)
    identity = auth.get_session_identity(cookie or '')
    email = (identity or {}).get('email', '').strip().lower()
    if not email:
        raise ScreenError('sign_in_required', 401)
    return email, cookie


def _policy():
    try:
        config = loader.get_policy().raw.get('bot_screens', {})
        if config.get('enabled') is not True:
            raise ScreenError('screens_disabled')
        profiles = config.get('profiles', {})
        if not isinstance(profiles, dict):
            raise ScreenError('screens_disabled')
        return profiles
    except ScreenError:
        raise
    except Exception:
        raise ScreenError('policy_unavailable', 503) from None


def _rights(email, bot):
    row = _policy().get(bot, {})
    def member(key):
        values = row.get(key, []) if isinstance(row, dict) else []
        return isinstance(values, list) and email in values
    admin = member('admins')
    control = admin or member('controllers')
    return {'view': control or member('viewers'), 'control': control, 'admin': admin}


def _home(bot):
    from api.bot_builder import _home as profile_home
    try:
        if not isinstance(bot, str) or not bot:
            raise ValueError()
        home = profile_home(bot)
        if not home.is_dir():
            raise ValueError()
        return home
    except Exception:
        raise ScreenError('unknown_bot', 404) from None


def _authorize(handler, bot, permission='view'):
    if not isinstance(bot, str) or not bot or len(bot) > 64:
        raise ScreenError('invalid_bot', 422)
    email, cookie = _identity(handler)
    rights = _rights(email, bot)
    if not rights[permission]:
        _audit(email, bot, 'denied')
        raise ScreenError('screen_forbidden')
    return email, cookie, rights, _home(bot)


@contextmanager
def _runtime(home):
    from api.routes import _ensure_agent_cron_import_path
    _ensure_agent_cron_import_path()
    from hermes_constants import set_hermes_home_override, reset_hermes_home_override
    from tools.bot_desktop import runtime, lease
    token = set_hermes_home_override(home)
    try:
        yield runtime, lease
    finally:
        reset_hermes_home_override(token)


def _viewer(cookie, bot, tab):
    # An untrusted tab name cannot claim another authenticated session's lease.
    if not isinstance(tab, str) or not 16 <= len(tab) <= 80 or not all(c.isalnum() or c in '-_' for c in tab):
        raise ScreenError('invalid_tab', 422)
    return hashlib.sha256((cookie + '\0' + bot + '\0' + tab).encode()).hexdigest()


def _audit(email, bot, action):
    append_audit_event('bot_screen_' + action, subject_email=email,
                       path='/api/bot-screen', mode='enforce', extra={'bot': bot})


def _may_watch(lease, viewer):
    return lease.holder == 'agent' or lease.viewer_id == viewer


def _snapshot(home, viewer, rights):
    with _runtime(home) as (runtime, leases):
        st = runtime.status().as_dict()
        lease = leases.get(profile_key=str(home))
    return {'running': bool(st.get('running')), 'supported': bool(st.get('supported')),
            'missing': st.get('missing', st.get('missing_binaries', [])),
            'can_start': bool(st.get('installed')) and not st.get('blocker'),
            'start_blocked_reason': st.get('blocker'),
            'holder': lease.holder, 'mine': lease.holder == 'human' and lease.viewer_id == viewer,
            'private': not _may_watch(lease, viewer), 'rights': rights}


def _screen_lock(home):
    with _LOCK:
        return _SCREEN_LOCKS.setdefault(str(home), threading.RLock())


def _confirm(key, challenge, action):
    with _LOCK:
        saved = _CHALLENGES.pop(key, None)
    if not saved or saved[1] < time.monotonic() or not isinstance(challenge, str) or not secrets.compare_digest(saved[0], challenge) or saved[2] != action:
        raise ScreenError('confirmation_required', 409)


def handle_get(handler, parsed):
    try:
        query = parse_qs(parsed.query)
        if parsed.path == '/api/bot-screen/ws':
            return _stream(handler, query)
        if parsed.path != '/api/bot-screen':
            return False
        email, cookie = _identity(handler)
        bot = query.get('bot', [''])[0]
        if not bot:
            rows = []
            for name in _policy():
                rights = _rights(email, name)
                if rights['view']:
                    _home(name)
                    rows.append({'id': name, 'rights': rights})
            return j(handler, {'bots': rows, 'csrf': auth.csrf_token_for_session(cookie)}, extra_headers={'Cache-Control': 'no-store'})
        _, cookie, rights, home = _authorize(handler, bot)
        viewer = _viewer(cookie, bot, query.get('tab', [''])[0])
        return j(handler, _snapshot(home, viewer, rights), extra_headers={'Cache-Control': 'no-store'})
    except ScreenError as exc:
        return j(handler, {'error': exc.code}, status=exc.status, extra_headers={'Cache-Control': 'no-store'})


def handle_post(handler, body):
    try:
        if not isinstance(body, dict) or set(body) - {'bot', 'tab', 'action', 'challenge', 'operation'}:
            raise ScreenError('invalid_request', 422)
        bot, action = body.get('bot'), body.get('action')
        if action not in ('start', 'stop', 'confirm', 'takeover', 'release', 'recover'):
            raise ScreenError('invalid_action', 422)
        email, cookie, rights, home = _authorize(handler, bot, 'admin' if action in ('stop', 'recover') else 'control')
        viewer = _viewer(cookie, bot, body.get('tab'))
        if action == 'confirm':
            if body.get('operation') not in ('takeover', 'recover', 'stop'):
                raise ScreenError('invalid_action', 422)
            challenge = secrets.token_urlsafe(24)
            with _LOCK:
                for key, value in list(_CHALLENGES.items()):
                    if value[1] < time.monotonic():
                        _CHALLENGES.pop(key, None)
                if len(_CHALLENGES) >= 128:
                    raise ScreenError('busy', 429)
                _CHALLENGES[viewer] = (challenge, time.monotonic() + 60, body['operation'])
            return j(handler, {'challenge': challenge}, extra_headers={'Cache-Control': 'no-store'})
        if action in ('takeover', 'recover', 'stop'):
            _confirm(viewer, body.get('challenge'), action)
        with _screen_lock(home), _runtime(home) as (runtime, leases):
            _authorize(handler, bot, 'admin' if action in ('stop', 'recover') else 'control')
            lease = leases.get(profile_key=str(home))
            if action == 'start':
                _audit(email, bot, action)
                runtime.start()
            elif action == 'takeover':
                if not runtime.status().running:
                    raise ScreenError('screen_stopped', 409)
                if lease.holder == 'human' and lease.viewer_id != viewer:
                    raise ScreenError('another_controller', 409)
                _audit(email, bot, action)
                leases.acquire(viewer, profile_key=str(home), reason='SynthPulse private takeover')
            elif action == 'release':
                if lease.holder == 'human' and lease.viewer_id != viewer:
                    raise ScreenError('another_controller', 409)
                _audit(email, bot, action)
                leases.release(viewer, profile_key=str(home))
            elif action == 'recover':
                _audit(email, bot, action)
                leases.release(profile_key=str(home))
            elif action == 'stop':
                if lease.holder == 'human':
                    raise ScreenError('hand_back_first', 409)
                _audit(email, bot, action)
                runtime.stop()
        return j(handler, _snapshot(home, viewer, rights), extra_headers={'Cache-Control': 'no-store'})
    except ScreenError as exc:
        return j(handler, {'error': exc.code}, status=exc.status)
    except Exception:
        return j(handler, {'error': 'screen_unavailable'}, status=503)


def _origin_allowed(handler):
    origin = urlsplit(handler.headers.get('Origin', ''))
    # Browser sockets always send Origin; forwarded headers are not authority.
    return origin.scheme in ('https', 'http') and origin.netloc == handler.headers.get('Host') and not origin.path and not origin.query and not origin.fragment


def _accept_websocket(handler):
    from websockets.server import ServerProtocol
    from websockets.sync.connection import Connection
    protocol = ServerProtocol(max_size=256 * 1024)
    raw = (handler.requestline + '\r\n' + str(handler.headers).replace('\n', '\r\n')).encode('latin1')
    protocol.receive_data(raw)
    events = protocol.events_received()
    if not events:
        raise ScreenError('invalid_websocket', 400)
    response = protocol.accept(events[0])
    if response.status_code != 101:
        raise ScreenError('invalid_websocket', 400)
    protocol.send_response(response)
    handler.wfile.flush()
    for data in protocol.data_to_send():
        handler.connection.sendall(data)
    handler.close_connection = True
    ws = Connection(handler.connection, protocol, close_timeout=1, ping_interval=2, ping_timeout=2, max_queue=8)
    handler.connection.settimeout(5)
    ws.start_keepalive()
    return ws


def _stream(handler, query):
    if not _origin_allowed(handler):
        raise ScreenError('origin_forbidden')
    bot = query.get('bot', [''])[0]
    email, cookie, rights, home = _authorize(handler, bot)
    viewer = _viewer(cookie, bot, query.get('tab', [''])[0])
    with _runtime(home) as (runtime, leases):
        if not _may_watch(leases.get(profile_key=str(home)), viewer):
            raise ScreenError('screen_private')
        if not runtime.status().running:
            raise ScreenError('screen_stopped', 409)
    if not _STREAMS.acquire(blocking=False):
        raise ScreenError('busy', 429)
    lock = _screen_lock(home)
    ws = endpoint = relay = None
    stop = threading.Event()
    pump = None
    try:
        with _runtime(home) as (runtime, leases):
            path = runtime.rfb_socket_path()
            if path:
                endpoint = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                endpoint.settimeout(3)
                endpoint.connect(str(path))
                reader = writer = endpoint
            else:
                relay = runtime.open_rfb_stream()
                reader, writer = relay.stdout, relay.stdin
        _audit(email, bot, 'open')
        ws = _accept_websocket(handler)
        from tools.bot_desktop.rfb_filter import RfbClientFilter
        def valid():
            # Checked at each frame/input: revocation/logout affects open sockets too.
            if not auth.verify_session(cookie) or not _rights(email, bot)['view']:
                return False
            return _may_watch(leases.get(profile_key=str(home)), viewer)
        def can_input():
            return _rights(email, bot)['control'] and leases.viewer_may_send_input(viewer, profile_key=str(home))
        rfb_filter = RfbClientFilter(can_input)
        def upstream():
            try:
                while not stop.is_set():
                    if not select.select([reader], [], [], 0.25)[0]:
                        continue
                    data = endpoint.recv(65536) if endpoint else __import__('os').read(reader.fileno(), 65536)
                    if not data:
                        break
                    with lock:
                        if not valid():
                            break
                        ws.send(data)
            except Exception:
                pass
            finally:
                stop.set()
                ws.close(4003, 'screen access changed')
        pump = threading.Thread(target=upstream, daemon=True)
        pump.start()
        stamp = 0
        while not stop.is_set():
            with lock:
                if not valid():
                    break
            if time.monotonic() - stamp > 30:
                (home / 'bot-desktop' / 'activity').touch()
                stamp = time.monotonic()
            try:
                data = ws.recv(timeout=0.5)
            except TimeoutError:
                continue
            if not isinstance(data, bytes):
                break
            with lock:
                if not valid():
                    break
                permitted = rfb_filter.feed(data)
                if permitted:
                    if endpoint:
                        endpoint.sendall(permitted)
                    else:
                        writer.write(permitted)
                        writer.flush()
    except ScreenError:
        raise
    except Exception:
        if ws is None:
            return j(handler, {'error': 'screen_unavailable'}, status=503)
    finally:
        stop.set()
        if ws:
            ws.close()
        if endpoint:
            endpoint.close()
        if relay:
            try:
                relay.kill()
                relay.wait(timeout=3)
            except (OSError, __import__('subprocess').TimeoutExpired):
                pass
            finally:
                for pipe in (relay.stdin, relay.stdout):
                    if pipe:
                        pipe.close()
        if pump:
            pump.join(timeout=3)
        _STREAMS.release()
        _audit(email, bot, 'close')
        # Link loss or tab refresh retains human control; only explicit Hand back releases it.
    return True
