"""Gateway extraction must tolerate wrappers but reject incomplete fact objects."""

from types import SimpleNamespace as NS

import pytest

from api.memory_extraction import extract


@pytest.mark.parametrize(
    "body,finish,valid",
    [
        ('{"facts":[]}', "stop", True),
        ('Here is the JSON:\n```json\n{"facts":[]}\n```', "stop", True),
        ('{"facts":[{"content":"unfinished', "stop", False),
        ('{"facts":[]}', "length", False),
        ('{"facts":"invented"}', "stop", False),
        ('{"facts":[]}\nExplanation with {braces}.', "stop", True),
        ('{"facts":[]} {"facts":[]}', "stop", True),
        ('{"facts":[]} Correction: {"facts":[', "stop", False),
    ],
)
def test_extraction_wire_validation(monkeypatch, body, finish, valid):
    import api.config
    import sys

    monkeypatch.setattr(
        api.config,
        "get_config",
        lambda: {
            "memory": {"consolidation": {"provider": "custom:test", "model": "test"}}
        },
    )
    monkeypatch.setattr(
        api.config,
        "resolve_custom_provider_connection",
        lambda _: ("test", "http://localhost/v1"),
    )

    class Client:
        def __init__(self, **kwargs):
            self.chat = NS(
                completions=NS(
                    create=lambda **kwargs: NS(
                        choices=[NS(finish_reason=finish, message=NS(content=body))]
                    )
                )
            )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setitem(sys.modules, "openai", NS(OpenAI=Client))
    if valid:
        assert extract("Return JSON.", [], []) == []
    else:
        with pytest.raises(ValueError):
            extract("Return JSON.", [], [])
