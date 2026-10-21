"""Exercise the actual browser parser on partial tags in large replies."""
import json
import subprocess
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'static/messages.js').read_text()
PARSER = SOURCE[SOURCE.index('const _thinkPairs='):SOURCE.index("if(typeof window!=='undefined'){", SOURCE.index('function _extractInlineThinkingFromContent'))]


def test_partial_tail_scans_once_and_preserves_code_and_reasoning():
    script = PARSER + r'''
    const originalNext = _nextThinkingOpener;
    let searches = 0;
    _nextThinkingOpener = (...args) => {searches++; return originalNext(...args);};
    const prefix = 'Ordinary answer text. '.repeat(3000);
    const cases = [
      [prefix + '<thi', prefix, '', true],
      [prefix + '`<thi', prefix + '`<thi', '', false],
      [prefix + '\n```html\n<thi', prefix + '\n```html\n<thi', '', false],
      [prefix + '\n    <thi', prefix + '\n    <thi', '', false],
      ['<think>first</think>' + prefix + '<think>second</think><thi', prefix, 'first\n\nsecond', true]
    ];
    const result = cases.map(([text, content, reasoning, inThinking]) => {
      searches = 0;
      const actual = _extractInlineThinkingFromContent(text, '', {streaming:true});
      return {correct:actual.content === content && actual.reasoning === reasoning && actual.inThinking === inThinking, searches};
    });
    console.log(JSON.stringify(result));
    '''
    output = subprocess.run(['node', '-e', script], text=True, capture_output=True, check=True)
    results = json.loads(output.stdout)
    assert all(item['correct'] for item in results), results
    assert all(item['searches'] <= 3 for item in results), results


def test_server_partial_tail_preserves_semantics_without_repeated_suffix_search(monkeypatch):
    from api import streaming

    original = streaming._next_inline_thinking_opener
    searches = []

    def counted(text, start):
        searches.append(start)
        return original(text, start)

    monkeypatch.setattr(streaming, '_next_inline_thinking_opener', counted)
    prefix = 'Ordinary answer text. ' * 3000
    for raw, expected, reasoning in [
        (prefix + '<thi', prefix, ''),
        (prefix + '`<thi', prefix + '`<thi', ''),
        (prefix + '\n```html\n<thi', prefix + '\n```html\n<thi', ''),
        (prefix + '\n    <thi', prefix + '\n    <thi', ''),
        ('<think>first</think>' + prefix + '<think>second</think><thi', prefix, 'first\n\nsecond'),
    ]:
        searches.clear()
        assert streaming._extract_inline_thinking_from_content(raw, '', streaming=True) == (expected, reasoning)
        assert len(searches) <= 3


def test_mixed_reasoning_code_and_settled_partial_tags_keep_all_content():
    from api.streaming import _extract_inline_thinking_from_content

    cases = [
        ('<think>plan</think>answer <thi', True, 'answer ', 'plan'),
        ('<think>plan</think>answer <thi', False, 'answer <thi', 'plan'),
        ('`<think>literal</think>`<think>real</think>end <thi', True, '`<think>literal</think>`end ', 'real'),
        ('```html\n<think>literal</think>\n```\n<think>real</think>end <thi', True, '```html\n<think>literal</think>\n```\nend ', 'real'),
        ('    <think>literal</think>\n<think>real</think>end <thi', True, '    <think>literal</think>\nend ', 'real'),
        ('<|channel>thought\nplan<channel|>answer <|cha', True, 'answer ', 'plan'),
        ('<|turn|>thinking\nplan<turn|>answer <|tur', True, 'answer ', 'plan'),
        ('<think>plan</think>answer `<thi', True, 'answer `<thi', 'plan'),
        ('<think>plan</think>answer\n    <thi', True, 'answer\n    <thi', 'plan'),
    ]
    script = PARSER + '\nconst cases=' + json.dumps(cases) + ';' + '''
    console.log(JSON.stringify(cases.map(([text, streaming]) => {
      const r=_extractInlineThinkingFromContent(text, '', {streaming});
      return [r.content,r.reasoning];
    })));
    '''
    output = subprocess.run(['node', '-e', script], text=True, capture_output=True, check=True)
    browser_results = json.loads(output.stdout)
    for case, browser in zip(cases, browser_results, strict=True):
        raw, streaming, content, reasoning = case
        assert browser == [content, reasoning]
        assert _extract_inline_thinking_from_content(raw, streaming=streaming) == (content, reasoning)
