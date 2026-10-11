"""Self-service proxy. Only server-resolved identities reach the signed MSP API."""
from urllib.parse import parse_qs, quote, urlencode
import re
from api import control_plane_client as control
from api.org_modules import context
from api.governance import delegation
from api.helpers import j

ROUTES=('/api/msp/overview','/api/msp/tickets','/api/msp/ticket','/api/msp/comment',
        '/api/msp/app-state','/api/msp/app-request','/api/msp/app-support')


def identity(handler):
    policy,subject,scope=context(handler)
    email=subject.normalized_email
    known=set(policy.users)|set(policy.bootstrap_admins)|set(delegation.organization_people(policy))
    if not email or subject.provider=='auth_disabled' or email not in known:
        raise PermissionError('Sign in with an organisation account')
    return {'user':email,'member_of':delegation.member_departments(policy,email),
            'admin_of':delegation.admin_departments(policy,email)}


def visible(handler):
    try:return bool(identity(handler))
    except Exception:return False


def fetch(handler,path,method='GET',body=None):
    try:acting=identity(handler)
    except PermissionError:return 403,{'error':{'code':'forbidden','message':'Organisation sign-in required'}}
    except Exception:return 503,{'error':{'code':'policy_unavailable','message':'Account permissions unavailable'}}
    status,data=control.call(method,path,body=body,acting=acting)
    return status or 503,data


def overview(handler):
    return fetch(handler,'/v1/customer/overview')


def respond(handler,result):
    status,data=result;j(handler,data,status=status,extra_headers={'Cache-Control':'no-store'});return True


def handle_get(handler,parsed):
    query=parse_qs(parsed.query)
    if parsed.path=='/api/msp/overview':return respond(handler,overview(handler))
    if parsed.path=='/api/msp/tickets':
        scope=query.get('scope',['mine'])[0]
        if scope not in ('mine','org','department'):return respond(handler,(422,{'error':'Invalid ticket scope'}))
        return respond(handler,fetch(handler,'/v1/tickets?'+urlencode({'scope':scope})))
    if parsed.path=='/api/msp/ticket':
        tid=query.get('id',[''])[0]
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',tid):return respond(handler,(422,{'error':'Invalid ticket ID'}))
        return respond(handler,fetch(handler,'/v1/tickets/'+quote(tid,safe='')))
    return False


def handle_post(handler,path,body):
    # Validate even self-service payloads before forwarding. Organisation and
    # acting headers can never be supplied by the browser.
    if not isinstance(body,dict):return respond(handler,(422,{'error':'Invalid request'}))
    if path=='/api/msp/tickets':
        allowed={'need','impact','title','body','service','private','department'};target='/v1/tickets'
    elif path=='/api/msp/comment':
        allowed={'ticket_id','body'};tid=body.get('ticket_id','')
        if not isinstance(tid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',tid):return respond(handler,(422,{'error':'Invalid ticket ID'}))
        target='/v1/tickets/'+tid+'/comments'
    elif path in ('/api/msp/app-state','/api/msp/app-request','/api/msp/app-support'):
        action={'/api/msp/app-state':'state','/api/msp/app-request':'request','/api/msp/app-support':'support'}[path]
        allowed={'app_id',{'state':'enabled','request':'note','support':'level'}[action]}
        app_id=body.get('app_id','')
        if not isinstance(app_id,str) or not re.fullmatch(r'[a-z][a-z0-9_]{1,60}',app_id):return respond(handler,(422,{'error':'Invalid app ID'}))
        target='/v1/customer/apps/'+app_id+'/'+action
    else:return False
    if set(body)-allowed:return respond(handler,(422,{'error':'Unknown request fields'}))
    payload={k:v for k,v in body.items() if k not in ('app_id','ticket_id')}
    return respond(handler,fetch(handler,target,'POST',payload))
