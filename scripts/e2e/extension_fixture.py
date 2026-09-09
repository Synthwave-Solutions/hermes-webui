"""Opt-in local extension transport fixture; never loaded by production.

Only an explicit per-run marker enables the two deterministic registry/archive
URLs. TLS/DNS/vendor delivery is outside this scenario. Real WebUI checksum,
ZIP validation/extraction, permissions, state and sidecar proxy remain unchanged.
"""
from __future__ import annotations

import hashlib
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import threading
from urllib.request import build_opener, ProxyHandler
import zipfile


def setup(qa: Path) -> dict:
    from api import extensions

    enabled = qa / 'extension-fixture.enabled'
    artifacts = qa / 'extension-fixture'
    artifacts.mkdir(mode=0o700, exist_ok=True)
    sidecar_calls: list[dict] = []
    payloads: dict[str, bytes] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            if self.path in payloads:
                status, body = 200, payloads[self.path]
            elif self.path == '/health':
                status, body = 200, b'{"status":"ok"}'
            elif self.path == '/probe':
                token_file = qa / 'state/sidecar-auth/qa-local-extension.token'
                expected = token_file.read_text().strip() if token_file.exists() else ''
                valid = bool(expected) and secrets.compare_digest(
                    self.headers.get('X-Hermes-Sidecar-Token', ''), expected)
                evidence = {'token_valid': valid, 'cookie_forwarded': bool(self.headers.get('Cookie')),
                            'authorization_forwarded': bool(self.headers.get('Authorization'))}
                sidecar_calls.append(evidence)
                (artifacts / 'sidecar-calls.json').write_text(json.dumps(sidecar_calls))
                status, body = (200 if valid else 403), json.dumps(evidence).encode()
            else:
                status, body = 404, b'{"error":"not_found"}'
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True, name='qa-extension-fixture').start()
    origin = f'http://127.0.0.1:{server.server_port}'
    entries = []
    schemas = [
        {'key': 'enabled', 'type': 'boolean', 'label': 'QA flag', 'default': False},
        {'key': 'label', 'type': 'string', 'label': 'QA label', 'default': 'initial'},
        {'key': 'ratio', 'type': 'number', 'label': 'QA ratio', 'default': 1.5},
        {'key': 'count', 'type': 'integer', 'label': 'QA count', 'default': 2},
        {'key': 'mode', 'type': 'enum', 'label': 'QA mode', 'default': 'compact', 'options': ['compact', 'full']},
    ]
    for ext_id in ['qa-local-extension', 'qa-peer-extension']:
        manifest = {'id': ext_id, 'name': ext_id, 'version': '1.0.0', 'scripts': ['app.js'],
                    'permissions': {'storage': {'owned': True}}, 'settings_schema': schemas}
        if ext_id == 'qa-local-extension':
            manifest['sidecar'] = {'type': 'loopback', 'origin': origin,
                                   'health_path': '/health', 'proxy_auth': 'token-v1'}
        # A real extension-owned component, loaded by the application's official
        # extension asset loader. Tests do not inject DOM or runtime globals.
        script = """(() => {
const id=EXTENSION_ID;
const panel=document.createElement('section');panel.id=id+'-runtime';
panel.style.cssText='padding:14px;margin:10px;border:1px solid currentColor';
const label=document.createElement('h3');label.textContent=id+' local runtime';panel.append(label);
const output=document.createElement('output');output.id=id+'-result';
const storage=window.hermesExt.storage.forExtension(id);
const settings=window.hermesExt.settings.forExtension(id);
function button(caption,action){const b=document.createElement('button');b.type='button';b.textContent=caption;b.addEventListener('click',action);panel.append(b);}
button('Store QA data',()=>{storage.set('record','QA_OWNED_'+id);output.textContent='stored';});
button('Read QA data',()=>{output.textContent=JSON.stringify(storage.getAll());});
button('Read QA settings',()=>{output.textContent=JSON.stringify(settings.values);});
button('Call QA sidecar',async()=>{try{const r=await fetch('/api/extensions/'+id+'/sidecar/probe',{headers:{'x-HERMES-sidecar-token':'QA_FORGED_BROWSER_TOKEN'}});output.textContent=JSON.stringify({status:r.status,body:await r.json()});}catch(e){output.textContent='network error';}});
panel.append(document.createElement('br'),output);
document.getElementById('settingsPaneExtensions').append(panel);
})();
""".replace('EXTENSION_ID', json.dumps(ext_id))
        packed = io.BytesIO()
        with zipfile.ZipFile(packed, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(ext_id + '/manifest.json', json.dumps(manifest))
            archive.writestr(ext_id + '/app.js', script)
        raw = packed.getvalue()
        archive_path = f'/qa/{ext_id}.zip'
        payloads[archive_path] = raw
        (artifacts / (ext_id + '.zip')).write_bytes(raw)
        entries.append({'id': ext_id, 'name': ext_id, 'version': '1.0.0',
                        'description': 'Synthetic local extension lifecycle fixture.',
                        'download_url': 'https://hermes-webui.github.io' + archive_path,
                        'sha256': hashlib.sha256(raw).hexdigest(), 'permissions': manifest['permissions']})
    entries.append({**entries[0], 'id': 'qa-bad-checksum', 'name': 'qa-bad-checksum', 'sha256': '0' * 64})
    payloads['/registry.json'] = json.dumps({'extensions': entries}).encode()
    (artifacts / 'sidecar-calls.json').write_text('[]')
    original_opener = extensions._build_gallery_opener
    original_registry = extensions.get_extension_registry
    active_before = False
    local_opener = build_opener(ProxyHandler({}))
    mappings = {extensions._REGISTRY_URL: '/registry.json'}
    mappings.update({entry['download_url']: '/qa/' + entry['download_url'].rsplit('/', 1)[1] for entry in entries})

    class FixtureOpener:
        def open(self, url, **kwargs):
            if enabled.exists() and url in mappings:
                return local_opener.open(origin + mappings[url], **kwargs)
            return original_opener().open(url, **kwargs)

    def registry():
        nonlocal active_before
        active = enabled.exists()
        if active != active_before:
            # Only fixture activation/deactivation invalidates the transport
            # cache, so this optional catalog cannot pollute other scenarios.
            with extensions._REGISTRY_LOCK:
                extensions._REGISTRY_CACHE.clear()
            active_before = active
        return original_registry()

    extensions._build_gallery_opener = FixtureOpener
    extensions.get_extension_registry = registry
    return {'activation_file': str(enabled), 'artifacts': str(artifacts), 'origin': origin,
            'registry_transport': 'loopback fixture; vendor TLS/DNS not tested'}
