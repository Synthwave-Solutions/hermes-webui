"""Synthetic Realtime protocol over actual HTTP/WebSocket connections.

This fixture does not synthesize audio or establish a real WebRTC peer. It lets
the browser lifecycle, server sideband, engine work and governance run together
without a live provider or credentials. Event injection is fixture-only.
"""
from __future__ import annotations

from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from urllib.parse import parse_qs, urlparse
import uuid

from websockets.sync.server import serve

LOCK = threading.RLock()
CALLS: dict[str, dict] = {}


def broadcast(call_id: str, event: dict) -> None:
    with LOCK:
        call = CALLS[call_id]
        call['provider_events'].append(event)
        if event.get('type') == 'response.created':
            call['response_active'] = True
        elif event.get('type') == 'response.done':
            call['response_active'] = False
        clients = list(call['clients'])
    for client in clients:
        try:
            client.send(json.dumps(event))
        except Exception:
            pass


def reply(call_id: str) -> None:
    response_id, item_id = 'resp_' + uuid.uuid4().hex, 'item_' + uuid.uuid4().hex
    with LOCK:
        text = CALLS[call_id].get('next_reply', 'QA_REALTIME_REPLY: We can keep talking while work runs.')
    for event in [
        {'type': 'response.created', 'response': {'id': response_id}},
        {'type': 'output_audio_buffer.started', 'response_id': response_id},
        {'type': 'response.output_audio_transcript.done', 'response_id': response_id, 'item_id': item_id, 'transcript': text},
        {'type': 'response.done', 'response': {'id': response_id, 'status': 'completed', 'output': [
            {'type': 'message', 'id': item_id, 'role': 'assistant', 'status': 'completed',
             'content': [{'type': 'audio', 'transcript': text}]}]}},
        {'type': 'output_audio_buffer.stopped', 'response_id': response_id},
    ]:
        broadcast(call_id, event)


def socket_handler(socket) -> None:
    call_id = parse_qs(urlparse(socket.request.path).query).get('call_id', [''])[0]
    with LOCK:
        call = CALLS.get(call_id)
        if not call:
            socket.close(1008, 'Unknown synthetic call')
            return
        call['clients'].add(socket)
        config = call['config']
    try:
        socket.send(json.dumps({'type': 'session.created', 'session': config}))
        for raw in socket:
            event = json.loads(raw)
            with LOCK:
                call['client_events'].append(event)
            if event.get('type') == 'response.create':
                reply(call_id)
            elif event.get('type') == 'conversation.item.create':
                broadcast(call_id, {'type': 'conversation.item.added', 'item': event.get('item', {})})
            elif event.get('type') == 'output_audio_buffer.clear':
                broadcast(call_id, {'type': 'output_audio_buffer.cleared'})
            elif event.get('type') == 'response.cancel':
                if not call.get('response_active'):
                    broadcast(call_id, {'type': 'error', 'error': {'code': 'response_cancel_not_active'}})
                else:
                    broadcast(call_id, {'type': 'response.done', 'response': {'status': 'cancelled', 'output': []}})
    finally:
        with LOCK:
            call['clients'].discard(socket)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status: int, body, *, content_type='application/json', headers=None):
        data = (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/health':
            return self.respond(200, {'ok': True})
        if self.path == '/qa/realtime/calls':
            with LOCK:
                calls = [{key: value for key, value in call.items() if key != 'clients'} for call in CALLS.values()]
            return self.respond(200, {'calls': calls})
        return self.respond(404, {'error': 'Unknown fixture route'})

    def do_POST(self):
        raw = self.rfile.read(min(int(self.headers.get('Content-Length', '0')), 1000000))
        if self.path == '/v1/realtime/calls':
            message = BytesParser(policy=default).parsebytes(
                ('Content-Type: ' + self.headers.get('Content-Type', '') + '\r\n\r\n').encode() + raw)
            parts = {part.get_param('name', header='content-disposition'): part.get_content() for part in message.iter_parts()}
            config = json.loads(parts['session'])
            call_id = 'rtc_qa_' + uuid.uuid4().hex
            with LOCK:
                CALLS[call_id] = {'call_id': call_id, 'config': config, 'clients': set(), 'client_events': [], 'provider_events': [], 'ended': False}
            return self.respond(201, 'v=0\na=qa-call-id:' + call_id + '\n', content_type='application/sdp',
                                headers={'Location': '/v1/realtime/calls/' + call_id})
        if self.path.startswith('/v1/realtime/calls/') and self.path.endswith('/hangup'):
            call_id = self.path.split('/')[-2]
            with LOCK:
                call = CALLS.get(call_id)
                if call:
                    call['ended'] = True
                    clients = list(call['clients'])
                else:
                    clients = []
            for client in clients:
                client.close()
            return self.respond(200, {'ok': True})
        parts = self.path.split('/')
        if len(parts) == 5 and parts[1:3] == ['qa', 'realtime'] and parts[4] == 'events':
            call_id = parts[3]
            if call_id not in CALLS:
                return self.respond(404, {'error': 'Unknown synthetic call'})
            data = json.loads(raw)
            if 'next_reply' in data:
                with LOCK:
                    CALLS[call_id]['next_reply'] = str(data['next_reply'])
            for event in data.get('events', []):
                broadcast(call_id, event)
            return self.respond(200, {'ok': True})
        return self.respond(404, {'error': 'Unknown fixture route'})


def main():
    import sys
    http_port, ws_port = map(int, sys.argv[1:3])
    with serve(socket_handler, '127.0.0.1', ws_port) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        ThreadingHTTPServer(('127.0.0.1', http_port), Handler).serve_forever()


if __name__ == '__main__':
    main()
