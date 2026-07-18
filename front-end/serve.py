"""Tiny static server for the SHB1 front-end (demo convenience).

Serves the files in this folder so the browser origin is http(s) rather than file://
(some browsers block fetch() from file:// origins).

Usage:
    python front-end/serve.py            # http://localhost:5173
    python front-end/serve.py 8080       # custom port

The backend (FastAPI) still runs separately on http://localhost:8000. The front-end
calls it directly; CORS is already open (allow_origins=["*"]). Change the API address
on the login screen if the backend runs elsewhere.
"""
from __future__ import annotations

import http.server
import os
import socketserver
import sys

# Windows consoles default to cp1252 and choke on accents / arrows — force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> None:
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"SHB1 front-end -> http://localhost:{PORT}")
        print("Backend expected at http://localhost:8000 (changeable on the login screen).")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nĐã dừng.")


if __name__ == "__main__":
    main()
