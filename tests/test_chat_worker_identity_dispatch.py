import ast
import inspect
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('gateway,group', [(True,False),(True,True),(False,False)])
def test_actual_worker_dispatch_keywords_match_original_sender(gateway,group):
    from api import routes, gateway_chat, streaming
    tree=ast.parse(inspect.getsource(routes._start_chat_stream_for_session))
    body=tree.body[0].body
    start=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='backend_is_gateway' for t in n.targets))
    end=next(i for i,n in enumerate(body[start:],start) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='thr' for t in n.targets))
    captured={}
    def thread(**kwargs):
        inspect.signature(kwargs['target']).bind(*kwargs['args'],**kwargs['kwargs'])
        captured.update(kwargs)
    identity={'email':'sender@example.test','groups':['original-sso-group']}
    namespace=dict(s=SimpleNamespace(session_id='sid',owner_email='owner@example.test',participants=['sender@example.test'] if group else [],bot_participants=['writer'] if group else []),webui_gateway_chat_enabled=lambda config:gateway,get_config=lambda:{},_run_gateway_chat_streaming=gateway_chat._run_gateway_chat_streaming,_run_agent_streaming=streaming._run_agent_streaming,model_provider=None,goal_related=False,sender_identity=identity,sender_email=identity['email'],execution_profile='writer' if group else None,moa_config=None,threading=SimpleNamespace(Thread=thread),msg='hello',model='test',workspace='/tmp',stream_id='run',attachments=[])
    exec(compile(ast.Module(body=body[start:end+1],type_ignores=[]),'<actual worker dispatch>','exec'),namespace)
    assert captured['kwargs']['sender_email']==identity['email']
    if gateway and not group:
        assert captured['target'] is gateway_chat._run_gateway_chat_streaming
        assert 'sender_identity' not in captured['kwargs']
    else:
        assert captured['target'] is streaming._run_agent_streaming
        assert captured['kwargs']['sender_identity'] is identity
