from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .config import load_settings
from .io_utils import read_json
from .llm import SumoPodChatModel
from .mock_llm import MockChatModel
from .orchestrator import run_workflow


class WebApp:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.static_dir = root / "web"

    def make_handler(self) -> type[BaseHTTPRequestHandler]:
        app = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/":
                    self._send_file(app.static_dir / "index.html", "text/html; charset=utf-8")
                    return
                if parsed.path == "/api/tickets":
                    self._send_json(read_json(app.root / "data/sample_tickets.json"))
                    return
                if parsed.path.startswith("/static/"):
                    requested = parsed.path.removeprefix("/static/")
                    path = app.static_dir / requested
                    content_type = "text/css; charset=utf-8" if path.suffix == ".css" else "application/javascript; charset=utf-8"
                    self._send_file(path, content_type)
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path != "/api/run":
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return

                try:
                    body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    payload = json.loads(body.decode("utf-8") or "{}")
                    result = self._run_agents(payload)
                except Exception as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return

                self._send_json(result)

            def log_message(self, format: str, *args: object) -> None:
                return

            def _run_agents(self, payload: dict) -> dict:
                mode = payload.get("mode", "mock")
                message = str(payload.get("message", "")).strip()
                customer_name = str(payload.get("customer_name", "Pelanggan")).strip() or "Pelanggan"
                if not message:
                    raise ValueError("Message is required.")

                ticket = {
                    "id": "web-chat",
                    "customer_name": customer_name,
                    "channel": "Web Chat",
                    "subject": "Customer web chat",
                    "message": message,
                }
                knowledge_base = read_json(app.root / "data/knowledge_base.json")
                if mode == "live":
                    model = SumoPodChatModel(settings=load_settings(app.root))
                else:
                    model = MockChatModel()

                return run_workflow(
                    model=model,
                    ticket=ticket,
                    knowledge_base=knowledge_base,
                    output_dir=app.root / "runs",
                )

            def _send_json(self, data: object, status: HTTPStatus = HTTPStatus.OK) -> None:
                encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _send_file(self, path: Path, content_type: str) -> None:
                if not path.exists() or not path.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                data = path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        return Handler


def serve(root: Path, host: str = "127.0.0.1", port: int = 8000) -> None:
    app = WebApp(root)
    server = ThreadingHTTPServer((host, port), app.make_handler())
    print(f"QHome AI Agent web app: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
