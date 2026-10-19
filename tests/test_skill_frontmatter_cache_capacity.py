"""Copied skill metadata shares parsing without sharing mutable results."""
from api import profiles
import pytest


@pytest.fixture(autouse=True)
def cache():
    profiles._SKILL_FRONTMATTER_CACHE.clear()
    profiles._skill_frontmatter_by_content.cache_clear()
    yield
    profiles._SKILL_FRONTMATTER_CACHE.clear()
    profiles._skill_frontmatter_by_content.cache_clear()


def test_copied_skills_parse_once_and_mutations_are_isolated(tmp_path):
    calls = []
    def parse(text):
        calls.append(text)
        return {'name': text, 'platforms': ['linux']}, ''
    paths = [tmp_path / str(i) for i in range(5)]
    for path in paths:
        path.write_text('same')
    for path in paths:
        value = profiles._skill_frontmatter_cached(path, parse)
        value['platforms'].append('mutated')
    assert calls == ['same']
    assert profiles._skill_frontmatter_cached(paths[0], parse)['platforms'] == ['linux']
    paths[1].write_text('changed')
    assert profiles._skill_frontmatter_cached(paths[1], parse)['name'] == 'changed'
    assert profiles._skill_frontmatter_cached(paths[0], parse)['name'] == 'same'
    assert calls == ['same', 'changed']


def test_capacity_evicts_only_least_recent_path(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, '_SKILL_FRONTMATTER_CACHE_MAX', 2)
    def parse(text):
        return {'name': text}, ''
    paths = [tmp_path / str(i) for i in range(3)]
    for i, path in enumerate(paths):
        path.write_text(str(i))
    for path in paths[:2]:
        profiles._skill_frontmatter_cached(path, parse)
    profiles._skill_frontmatter_cached(paths[0], parse)
    profiles._skill_frontmatter_cached(paths[2], parse)
    keys = profiles._SKILL_FRONTMATTER_CACHE
    assert len(keys) == 2
    assert (str(paths[0]), parse) in keys
    assert (str(paths[2]), parse) in keys
    assert (str(paths[1]), parse) not in keys


def test_content_cache_respects_parser_identity(tmp_path):
    path = tmp_path / 'SKILL.md'
    path.write_text('same')
    def first(text):
        return {'name': 'first'}, ''
    def second(text):
        return {'name': 'second'}, ''
    assert profiles._skill_frontmatter_cached(path, first)['name'] == 'first'
    assert profiles._skill_frontmatter_cached(path, second)['name'] == 'second'
