"""Shared bounded JSON extraction via the configured custom gateway."""

import json


def extract(system, batch, catalog, *, provider=None, model=None):
    from api.config import get_config, resolve_custom_provider_connection
    from openai import OpenAI

    cfg = get_config()
    route = (cfg.get("memory") or {}).get("consolidation") or {}
    provider = (
        provider
        or route.get("provider")
        or (cfg.get("model") or {}).get("provider", "")
    )
    if not provider.startswith("custom:"):
        raise ValueError("Consolidation requires a configured custom gateway")
    key, url = resolve_custom_provider_connection(provider)
    if not url:
        raise ValueError("Consolidation gateway unavailable")
    model = model or route.get("model") or (cfg.get("model") or {}).get("default")
    with OpenAI(
        api_key=key or "no-key-required", base_url=url, timeout=90, max_retries=0
    ) as client:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"existing_topics": catalog, "source_messages": batch},
                        ensure_ascii=False,
                    ),
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=5000,
            # Avoid the deployed gateway's <=0.1 dedup for Responses-format bodies.
            temperature=0.2,
            extra_body={"reasoning": {"effort": "low"}},
            extra_headers={"x-omniroute-no-memory": "true"},
        )
    if result.choices[0].finish_reason not in ("stop", None):
        raise ValueError("Incomplete consolidation response")
    raw = (result.choices[0].message.content or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        # Subscription bridges may ignore JSON mode and append a correction.
        # Use the final complete object; never repair malformed fact content.
        decoder = json.JSONDecoder()
        start = raw.find("{")
        if start < 0:
            raise
        value, consumed = decoder.raw_decode(raw[start:])
        trailing = raw[start + consumed :]
        while '"facts"' in trailing:
            start = trailing.find("{")
            if start < 0:
                raise ValueError("Incomplete consolidation correction") from None
            value, consumed = decoder.raw_decode(trailing[start:])
            trailing = trailing[start + consumed :]
    if not isinstance(value, dict) or not isinstance(value.get("facts"), list):
        raise ValueError("Invalid consolidation JSON")
    return value["facts"]
