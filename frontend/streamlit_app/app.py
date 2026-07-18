"""Canonical frontend entry (Final spec §5.2/§10) — delegates to the live UI.

The single UI implementation lives in ui/app.py during the migration window;
this wrapper exists so `streamlit run frontend/streamlit_app/app.py` is the
canonical command and drift between two copies is impossible.
"""
from ui.app import main  # noqa: F401

if __name__ == "__main__":  # streamlit run executes this file as __main__
    main()
