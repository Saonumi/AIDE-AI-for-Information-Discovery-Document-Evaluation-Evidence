"""Helper to call a track service facade lazily and surface a clean 503 if the
track hasn't implemented it yet. Keeps route files identical in shape.
"""
from __future__ import annotations

from importlib import import_module

from fastapi import HTTPException


def call(module: str, func: str, *args, **kwargs):
    try:
        mod = import_module(module)
        fn = getattr(mod, func)
    except (ImportError, AttributeError) as e:
        raise HTTPException(status_code=503, detail=f"{module}.{func} not implemented yet ({e})")
    return fn(*args, **kwargs)
