"""Dependency-free local API for the V5 web client and integrations."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cumcm_lens.training import coach_review, diagnose_profile, recommend_models

ROOT = Path(__file__).resolve().parents[2]


class Handler(BaseHTTPRequestHandler):
    server_version = "CUMCMLens/5.0"

    def _headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def _json(self, payload: Any, status: int = 200) -> None:
        self._headers(status)
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("request body too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._headers(204)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/v1/health":
            self._json({"status": "ok", "version": "5.0.0", "mode": "local-first"})
        elif path == "/api/v1/problems":
            catalog = ROOT / "knowledge" / "problem_catalog.csv"
            self._json({"path": str(catalog.relative_to(ROOT)), "available": catalog.exists()})
        else:
            self._json({"error": "not_found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/v1/diagnose":
                self._json(diagnose_profile(body.get("scores", body)))
            elif path == "/api/v1/recommend-models":
                self._json(recommend_models(
                    str(body.get("task", "regression")),
                    time_ordered=bool(body.get("time_ordered")),
                    nonlinear=bool(body.get("nonlinear")),
                ))
            elif path == "/api/v1/coach":
                self._json(coach_review(str(body.get("text", "")), body.get("context")))
            else:
                self._json({"error": "not_found"}, 404)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json({"error": "invalid_request", "detail": str(exc)}, 400)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"CUMCM Lens API: http://{args.host}:{args.port}/api/v1/health")
    server.serve_forever()


if __name__ == "__main__":
    main()
