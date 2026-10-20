"""Text-only history must not pay for image capability discovery."""
from copy import deepcopy

import pytest
from api import streaming


@pytest.mark.parametrize('content', ['hello', [{'type':'text','text':'hello'}], None])
def test_text_history_does_not_resolve_image_capabilities(monkeypatch, content):
    def unexpected(*args, **kwargs):
        raise AssertionError('text-only history triggered image/model discovery')
    monkeypatch.setattr(streaming, '_resolve_image_input_mode', unexpected)
    history = [{'role':'user','content':content}]
    original = deepcopy(history)
    assert streaming._sanitize_messages_for_api(history, cfg={'agent':{}}) == history
    assert history == original


@pytest.mark.parametrize('mode', ['text','native'])
@pytest.mark.parametrize('typed', [True, False])
def test_real_images_still_resolve_once_and_preserve_policy(monkeypatch, mode, typed):
    calls=[]
    monkeypatch.setattr(streaming, '_resolve_image_input_mode', lambda cfg: calls.append(cfg) or mode)
    content=[{'type':'text','text':'Describe'}, {'type':'image_url','image_url':{'url':'data:image/png;base64,c3ludGhldGlj'}}]
    if not typed:
        content[1].pop('type')
    history=[{'role':'user','content':content}, {'role':'assistant','content':'A picture'}, {'role':'user','content':deepcopy(content)}]
    original=deepcopy(history)
    result=streaming._sanitize_messages_for_api(history,cfg={'agent':{}})
    assert len(calls)==1
    assert history==original
    for message in (result[0],result[2]):
        images=[p for p in message['content'] if isinstance(p,dict) and 'image_url' in p] if isinstance(message['content'],list) else []
        assert bool(images)==(mode=='native')
