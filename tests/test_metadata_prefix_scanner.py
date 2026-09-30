"""Metadata scanning must skip large strings without confusing nested chat keys."""
import json

import pytest

from api.models import _find_top_level_json_key, _read_metadata_json_prefix


@pytest.mark.parametrize('summary', ['plain' * 40000, 'é \\" { [ messages' * 12000], ids=['plain', 'escaped-unicode'])
def test_large_prefix_preserves_metadata_and_excludes_transcript(tmp_path, summary):
    meta = {'nested': {'messages': [1]}, 'compression_anchor_summary': summary}
    path = tmp_path / 'chat.json'
    path.write_text(json.dumps({**meta, 'messages': [{'content': 'transcript'}]}))
    assert json.loads(_read_metadata_json_prefix(path)) == meta


def test_scanner_decodes_json_key_escapes():
    text = r'{"nested": {"messages": []}, "mess\u0061ges": []}'
    assert _find_top_level_json_key(text, 'messages') == text.index('"mess\\u0061ges"')


@pytest.mark.parametrize('text', ['{"summary":"unfinished', '{"nested":{"messages":[]}}', '{"summary":"escaped\\"'])
def test_absent_or_incomplete_key_returns_none(text):
    assert _find_top_level_json_key(text, 'messages') is None
