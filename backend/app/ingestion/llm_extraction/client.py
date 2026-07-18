"""LLM client abstraction: Anthropic | OpenAI | Mock.

Auto-falls back to MockClient when the provider key is missing or demo_mode is on,
so the whole app (and its tests) runs offline. Mock generation is grounded: it echoes
the first cited evidence line, so deterministic output checks still pass in a demo.

Tool use is intentionally NOT exposed here — generation is tool-free by contract.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from packages.common.config import get_settings

_client = None
_BRACKET = re.compile(r"\[([^\]\s]+)\]\s*(?:\([^)]*\)\s*)?(.*)")


class MockClient:
    provider = "mock"
    model = "mock"

    def complete(self, system: str, user: str, temperature: float = 0.0) -> str:
        # Produce a grounded answer from the first cited evidence line.
        for line in user.splitlines():
            line = line.strip()
            m = _BRACKET.match(line)
            if m and m.group(2).strip():
                sid, content = m.group(1), m.group(2).strip()
                return f"{content} [{sid}]"
        return "INSUFFICIENT_EVIDENCE"

    def complete_json(self, system: str, user: str, schema: Optional[dict] = None) -> Dict[str, Any]:
        return {}


class GoogleClient:
    """Google AI Studio (Gemini) via the google-genai SDK."""
    provider = "google"

    def __init__(self, api_key: str, model: str, temperature: float):
        from google import genai
        self._genai = genai
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def complete(self, system: str, user: str, temperature: Optional[float] = None) -> str:
        from google.genai import types
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.temperature if temperature is None else temperature,
        )
        resp = self._client.models.generate_content(model=self.model, contents=user, config=cfg)
        return resp.text or ""

    def complete_json(self, system: str, user: str, schema: Optional[dict] = None) -> Dict[str, Any]:
        from google.genai import types
        cfg = types.GenerateContentConfig(
            system_instruction=system + "\nTrả về DUY NHẤT JSON hợp lệ.",
            temperature=0.0,
            response_mime_type="application/json",
        )
        resp = self._client.models.generate_content(model=self.model, contents=user, config=cfg)
        return _extract_json(resp.text or "{}")


class AnthropicClient:
    provider = "anthropic"

    def __init__(self, api_key: str, model: str, temperature: float):
        import anthropic
        self._c = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def complete(self, system: str, user: str, temperature: Optional[float] = None) -> str:
        resp = self._c.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=self.temperature if temperature is None else temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    def complete_json(self, system: str, user: str, schema: Optional[dict] = None) -> Dict[str, Any]:
        txt = self.complete(system + "\nTrả về DUY NHẤT JSON hợp lệ.", user, temperature=0.0)
        return _extract_json(txt)


class OpenAIClient:
    provider = "openai"

    def __init__(self, api_key: str, model: str, temperature: float):
        import openai
        self._c = openai.OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def complete(self, system: str, user: str, temperature: Optional[float] = None) -> str:
        resp = self._c.chat.completions.create(
            model=self.model,
            temperature=self.temperature if temperature is None else temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""

    def complete_json(self, system: str, user: str, schema: Optional[dict] = None) -> Dict[str, Any]:
        resp = self._c.chat.completions.create(
            model=self.model,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return _extract_json(resp.choices[0].message.content or "{}")


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[-1] if "\n" in text else text
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
        return {}


def get_client():
    global _client
    if _client is not None:
        return _client
    s = get_settings()
    try:
        if s.demo_mode:
            _client = MockClient()
        elif s.llm_provider == "google" and s.google_api_key:
            _client = GoogleClient(s.google_api_key, s.llm_model, s.llm_temperature)
        elif s.llm_provider == "anthropic" and s.anthropic_api_key:
            _client = AnthropicClient(s.anthropic_api_key, s.llm_model, s.llm_temperature)
        elif s.llm_provider == "openai" and s.openai_api_key:
            _client = OpenAIClient(s.openai_api_key, s.llm_model, s.llm_temperature)
        else:
            _client = MockClient()
    except Exception:
        _client = MockClient()
    return _client


def reset_client_for_tests(client=None):
    global _client
    _client = client or MockClient()
    return _client
