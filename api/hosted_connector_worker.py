"""Short-lived connector account worker with an isolated personal auth store.

Invoked by hosted_connectors, never as an HTTP handler. No ambient host tokens,
profile configuration or connector identities are inherited by this process.
"""
import contextlib
import io
import json
import sys


def execute(request):
    from tools.managed_tool_gateway import read_nous_access_token
    from tools.connectors.portal.client import PortalConnectorClient
    action = request['action']
    if action == 'token':
        return {'token': read_nous_access_token()}
    if action == 'accounts':
        return {'accounts': PortalConnectorClient().list_accounts() if read_nous_access_token() else []}
    if action == 'catalog':
        client = PortalConnectorClient()
        listing = client.catalog() if read_nous_access_token() else client.public_catalog()
        return listing.model_dump()
    if action == 'connect':
        from tools.connectors.managed import managed_client, DESKTOP_PAGE
        return managed_client(creates_guest=True, initiator=DESKTOP_PAGE).connections([request['slug']])
    if action == 'disconnect':
        return PortalConnectorClient().delete_account(request['connection_id'])
    raise ValueError('Unsupported connector action')


def main():
    request = json.loads(sys.stdin.read(8192))
    try:
        # Native auth helpers can print sign-in notices. Only the typed result
        # crosses this pipe; stderr and credential values never enter HTTP logs.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = execute(request)
        print(json.dumps({'ok': True, 'result': result}))
    except Exception:
        print(json.dumps({'ok': False, 'error': 'The connector service could not complete this request. Please retry.'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
