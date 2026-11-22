"""Self-service proxy. Only server-resolved identities reach the signed MSP API."""
from urllib.parse import parse_qs, quote, urlencode
import os
import re
from api import control_plane_client as control
from api.org_modules import context
from api.governance import delegation
from api.helpers import j

ROUTES=('/api/msp/invoice','/api/msp/invoices','/api/msp/order','/api/msp/job-cost','/api/msp/package','/api/msp/overview','/api/msp/tickets','/api/msp/ticket','/api/msp/comment',
        '/api/msp/app-state','/api/msp/app-request','/api/msp/app-intake','/api/msp/app-support')


def identity(handler):
    policy,subject,scope=context(handler)
    email=subject.normalized_email
    known=set(policy.users)|set(policy.bootstrap_admins)|set(delegation.organization_people(policy))
    personal = subject.provider=='synthpulse_cloud' and os.environ.get('SP_CLOUD_PERSONAL_MSP')=='1'
    if not email or subject.provider=='auth_disabled' or (email not in known and not personal):
        raise PermissionError('Sign in with an organisation account')
    if email not in known:
        # The supplier's assigned staff work in Studio; the customer's own account
        # (invoices, orders, packages, tickets) is not theirs to open.
        from api import org_structure
        if org_structure.partner_for(email) is not None:
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
    options={'timeout':60} if path.endswith('/download') else {}
    if os.environ.get('SP_CLOUD_PERSONAL_MSP')=='1':
        from api.auth import cloud_msp_proof
        proof=cloud_msp_proof(handler)
        if not proof:
            return 403,{'error':{'code':'personal_login_required','message':'Open SynthPulse vanuit je persoonlijke Cloud-account.'}}
        options['cloud_session']=proof
    status,data=control.call(method,path,body=body,acting=acting,**options)
    return status or 503,data


def overview(handler):
    return fetch(handler,'/v1/customer/overview')


# ── Payments and invoices of the organisation (organisation owners and admins) ──

LEDGER_PATH='/v1/customer/invoices'
_LEDGER_MAX=200
_INVOICE_ID=re.compile(r'br_[A-Za-z0-9_-]{1,80}')


def _words(value,limit=200):
    return ' '.join(str(value).split())[:limit] if isinstance(value,(str,int)) and not isinstance(value,bool) else ''


def _cents(value):
    return int(value) if isinstance(value,(int,float)) and not isinstance(value,bool) else None


def _ledger_lines(raw):
    return [{'kind':_words(line.get('kind'),40),'description':_words(line.get('description')),'department':_words(line.get('department'),120) or None,
             'quantity':line.get('quantity') if isinstance(line.get('quantity'),(int,float)) and not isinstance(line.get('quantity'),bool) else None,
             'amount_ex_vat_cents':_cents(line.get('amount_ex_vat_cents'))}
            for line in (raw if isinstance(raw,list) else [])[:40] if isinstance(line,dict)]


def _ledger_row(raw,invoice):
    row={'id':_words(raw.get('id'),100),'date':_words(raw.get('date'),40) or None,'period':_words(raw.get('period'),20) or None,
         'status':_words(raw.get('status'),40),'description':_words(raw.get('description')),'lines':_ledger_lines(raw.get('lines')),
         'totals':{'amount_ex_vat_cents':_cents(raw.get('amount_ex_vat_cents')),'vat_cents':_cents(raw.get('vat_cents')),
                   'total_cents':_cents(raw.get('total_cents'))},
         'payment_method':_words(raw.get('payment_method'),40) or None}
    if isinstance(raw.get('totals'),dict):          # a control plane that already groups the totals
        for key in row['totals']:
            if _cents(raw['totals'].get(key)) is not None:row['totals'][key]=_cents(raw['totals'][key])
    if invoice:
        # The document is fetched by the invoice id through the existing download route; only ids of that form get one.
        row.update(number=_words(raw.get('number'),80),reverse_charge=raw.get('reverse_charge') is True,
                   pdf_available=raw.get('pdf_available') is True and bool(_INVOICE_ID.fullmatch(row['id'])))
    else:
        row.update(kind=_words(raw.get('kind'),40),department_name=_words(raw.get('department_name'),120) or None,
                   service_from=_words(raw.get('service_from'),20) or None,service_until=_words(raw.get('service_until'),20) or None,
                   under_review=raw.get('under_review') is True)
    return row


def clean_ledger(data):
    """The bounded shape for the browser from what the control plane answered."""
    data=data if isinstance(data,dict) else {}
    rows=lambda key,invoice:[_ledger_row(r,invoice) for r in (data.get(key) if isinstance(data.get(key),list) else [])[:_LEDGER_MAX] if isinstance(r,dict)]
    return {'title':_words(data.get('title'),120),'currency':_words(data.get('currency'),3) or 'EUR',
            'invoices_complete':data.get('invoices_complete') is True,'notice':_words(data.get('notice'),600) or None,
            'invoices':rows('invoices',True),'payments':rows('payments',False)}


def ledger(handler):
    """Payments and invoices, for organisation owners and admins only.

    Checked here as well as centrally: a partner never passes ``identity`` and
    a normal user is no organisation admin in the team structure. The control
    plane then decides once more on the person's role in the Cloud.
    """
    try:identity(handler)
    except PermissionError:return 403,{'error':{'code':'forbidden','message':'Organisation sign-in required'}}
    except Exception:return 503,{'error':{'code':'policy_unavailable','message':'Account permissions unavailable'}}
    from api import org_structure
    view=org_structure.request_scope(handler)
    if view.scope!=org_structure.SCOPE_ALL or view.is_partner:
        return 403,{'error':{'code':'forbidden','message':'Only organisation owners and admins see payments and invoices'}}
    status,data=fetch(handler,LEDGER_PATH)
    return (200,clean_ledger(data)) if status==200 else (status,data)


def respond(handler,result):
    status,data=result;j(handler,data,status=status,extra_headers={'Cache-Control':'no-store'});return True


def handle_get(handler,parsed):
    query=parse_qs(parsed.query)
    if parsed.path=='/api/msp/overview':return respond(handler,overview(handler))
    if parsed.path=='/api/msp/invoices':return respond(handler,ledger(handler))
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
    if path=='/api/msp/invoice':
        allowed={'request_id'};ident=body.get('request_id','')
        if not isinstance(ident,str) or not re.fullmatch(r'br_[A-Za-z0-9_-]{1,80}',ident):return respond(handler,(422,{'error':'Invalid invoice request'}))
        target='/v1/customer/invoices/'+ident+'/download'
    elif path=='/api/msp/order':
        allowed={'order_id','action'};ident=body.get('order_id','');action=body.get('action')
        if not isinstance(ident,str) or not re.fullmatch(r'so_[A-Za-z0-9_-]{1,80}',ident) or action not in ('checkout','sync','submit'):
            return respond(handler,(422,{'error':'Invalid service order'}))
        target='/v1/customer/orders/'+ident+'/'+action
    elif path=='/api/msp/job-cost':
        allowed={'job_id','profile','title','hours_hundredths','hourly_cents','expected_revision','support_minutes','support_enabled'};target='/v1/customer/job-cost'
    elif path=='/api/msp/package':
        allowed={'kind','days_per_week','action'};target='/v1/customer/package'
    elif path=='/api/msp/tickets':
        allowed={'need','impact','title','body','service','private','department'};target='/v1/tickets'
    elif path=='/api/msp/comment':
        allowed={'ticket_id','body'};tid=body.get('ticket_id','')
        if not isinstance(tid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',tid):return respond(handler,(422,{'error':'Invalid ticket ID'}))
        target='/v1/tickets/'+tid+'/comments'
    elif path in ('/api/msp/app-state','/api/msp/app-request','/api/msp/app-intake','/api/msp/app-support'):
        action={'/api/msp/app-state':'state','/api/msp/app-request':'request','/api/msp/app-intake':'intake','/api/msp/app-support':'support'}[path]
        allowed={'app_id','note','scope','departments','request_key'} if action=='intake' else {'app_id',{'state':'enabled','request':'note','support':'level'}[action]}
        app_id=body.get('app_id','')
        if not isinstance(app_id,str) or not re.fullmatch(r'[a-z][a-z0-9_]{1,60}',app_id):return respond(handler,(422,{'error':'Invalid app ID'}))
        target='/v1/customer/apps/'+app_id+'/'+action
    else:return False
    if set(body)-allowed:return respond(handler,(422,{'error':'Unknown request fields'}))
    if path=='/api/msp/app-intake':
        try:
            identity(handler)
            policy, _, _ = context(handler)
            # This is a request for a proposal. Central org roles still decide
            # whether it may be created; local policy owns department names.
            departments = body.get('departments', [])
            if (not isinstance(departments, list) or len(departments)>64 or
                    any(not isinstance(key,str) or key not in policy.departments for key in departments)):
                return respond(handler,(422,{'error':'Choose departments from this organisation'}))
            scope=body.get('scope')
            if scope not in ('organisation','departments','environment') or (scope=='departments') != bool(departments):
                return respond(handler,(422,{'error':'Choose the request scope and its departments'}))
            body={**body,'departments':sorted(set(departments))}
        except PermissionError:
            return respond(handler,(403,{'error':'Organisation sign-in required'}))
        except Exception:
            return respond(handler,(503,{'error':'Account permissions unavailable'}))
    if path=='/api/msp/job-cost':
        if not isinstance(body.get('job_id'),str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}',body['job_id']):return respond(handler,(422,{'error':'Invalid job ID'}))
        from api.profiles import get_active_profile_name, cron_profile_context
        from api.cron_scope import caller_sees_cron_profile
        profile=get_active_profile_name() or 'default'
        if body.get('profile')!=profile:return respond(handler,(422,{'error':'Open the job in its owning profile'}))
        from api.routes import _ensure_agent_cron_import_path
        _ensure_agent_cron_import_path()
        from cron.jobs import get_job
        with cron_profile_context():
            job=get_job(body.get('job_id',''))
            if not job or not caller_sees_cron_profile(handler,profile,job_id=body.get('job_id'),job=job):
                return respond(handler,(404,{'error':'Job not found'}))
            body={**body,'title':str(job.get('name') or job['id'])[:200]}
    payload={k:v for k,v in body.items() if k not in ('app_id','ticket_id','order_id','request_id') and not (path=='/api/msp/order' and k=='action')}
    return respond(handler,fetch(handler,target,'POST',payload))
