"""Exchange a single-use account handoff directly with this installation's signed gateway."""
import os
import re
from urllib.parse import urlsplit
from api import auth, control_plane_client
from api.helpers import j


def _partner(email):
    """{'role','org'} when this address is a partner the central Cloud assigned here, else None. Never raises."""
    try:
        from api import org_structure, studio_report
        from api.governance import loader
        address=org_structure.norm_email(email)
        try:
            known=address in loader.get_policy().users
        except Exception:
            known=True
        if not address or known:
            return None
        if org_structure.cloud_partner_for(address) is None:
            # Assigned a moment ago: ask the control plane before deciding.
            studio_report.pull_assignments()
        row=org_structure.cloud_partner_for(address)
        return {'role':row['role'],'org':row['org']} if row else None
    except Exception:
        return None


def redeem(handler, body):
    origin=urlsplit(handler.headers.get('Origin',''))
    if (os.getenv('SP_CLOUD_PERSONAL_MSP')!='1' or handler.headers.get('X-SynthPulse-Login')!='1'
            or origin.scheme!='https' or origin.netloc!=handler.headers.get('Host')
            or not isinstance(body,dict) or set(body)!={'code'} or not isinstance(body['code'],str)
            or not re.fullmatch('[a-f0-9]{64}',body['code'])):
        j(handler,{'ok':False},403);return True
    status,data=control_plane_client.call('POST','/v1/cloud-session',body={'code':body['code']})
    if status!=200 or not isinstance(data,dict) or not re.fullmatch('[a-f0-9]{64}',str(data.get('proof',''))) or not data.get('email'):
        j(handler,{'ok':False},403);return True
    identity={'email':data['email'],'method':'synthpulse_cloud','groups':[],
              'claims_subset':{},'_cloud_msp_proof':data['proof']}
    partner=_partner(data['email'])
    if partner:
        # A label only: what the session may do is decided on every request from the
        # current assignment (api/governance/resolver.py), never from this field.
        identity['partner']=partner
    cookie=auth.create_session(identity)
    handler.send_response(200)
    auth.set_auth_cookie(handler,cookie)
    handler.send_header('Content-Type','application/json')
    handler.send_header('Cache-Control','no-store')
    handler.send_header('Content-Length','11')
    handler.end_headers()
    handler.wfile.write(b'{"ok":true}')
    return True
