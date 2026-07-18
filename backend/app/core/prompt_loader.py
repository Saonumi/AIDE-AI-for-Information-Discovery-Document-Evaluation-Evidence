"""Versioned prompt/schema loader (Mode spec §10.1).

Evaluator, explainer and assistant each get their OWN system prompt file —
never one shared prompt. Every prompt carries a version in its first line
(`<!-- version: name-X.Y -->`) which is stamped into Review Run audit metadata.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = _APP_DIR / "prompts"
SCHEMAS_DIR = _APP_DIR / "schemas"
_VER = re.compile(r"version:\s*([\w.\-]+)")


@lru_cache(maxsize=None)
def load_prompt(name: str) -> dict:
    """name = file stem, e.g. 'review_evaluator.system' -> {name, version, text}."""
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    first = text.splitlines()[0] if text else ""
    m = _VER.search(first)
    return {"name": name, "version": m.group(1) if m else "unversioned", "text": text}


@lru_cache(maxsize=None)
def system_prompt(name: str) -> str:
    """Mode prompt + shared safety rules appended (safety always wins)."""
    return load_prompt(name)["text"] + "\n\n" + load_prompt("shared_safety_rules")["text"]


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    """name = file stem, e.g. 'claim_assessment' -> parsed JSON Schema."""
    return json.loads((SCHEMAS_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def schema_version(name: str) -> str:
    return load_schema(name).get("version", "unversioned")
