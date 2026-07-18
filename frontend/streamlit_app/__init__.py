"""Streamlit UI (Track C). Talks to the FastAPI backend over HTTP only.

`api_client.py` is a thin, dependency-light HTTP wrapper (uses `requests`) that
never raises on network errors — it returns a typed ApiResult so `app.py` can show
a friendly message instead of crashing when the API is down.
`app.py` is the Streamlit application (login, chat, compare, review, dashboard,
KG viz, audit).
"""
