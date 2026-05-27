from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import load_settings
from .io_utils import read_json
from .llm import SumoPodChatModel
from .mock_llm import MockChatModel
from .orchestrator import run_workflow


class SessionStore:
    """Thread-safe in-memory session store for the web demo."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, dict] = {}

    def update(self, session_id: str, customer_name: str, message: str, result: dict) -> None:
        with self._lock:
            now = datetime.now(UTC).isoformat()
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    "session_id": session_id,
                    "customer_name": customer_name,
                    "history": [],
                    "triage": None,
                    "staff_status": "new",
                    "staff_notes": "",
                    "created_at": now,
                    "updated_at": now,
                }
            session = self._sessions[session_id]
            session["customer_name"] = customer_name
            session["history"].append({"role": "customer", "content": message})
            reply = (result.get("final") or {}).get("customer_reply", "")
            if reply:
                session["history"].append({"role": "assistant", "content": reply})
            session["triage"] = result
            session["updated_at"] = now

    def get(self, session_id: str) -> dict | None:
        with self._lock:
            session = self._sessions.get(session_id)
            return dict(session) if session else None

    def update_staff(self, session_id: str, staff_status: str | None, staff_notes: str | None) -> dict | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if staff_status is not None and staff_status in {"new", "in_progress", "done"}:
                session["staff_status"] = staff_status
            if staff_notes is not None:
                session["staff_notes"] = staff_notes
            session["updated_at"] = datetime.now(UTC).isoformat()
            return dict(session)

    def list_all(self) -> list[dict]:
        with self._lock:
            summaries = []
            for session in self._sessions.values():
                triage = session.get("triage") or {}
                final = triage.get("final", {})
                outputs = triage.get("agent_outputs", {})
                classifier = outputs.get("intent_classifier", {})
                missing = normalize_list(classifier.get("missing_information", []))
                if missing:
                    status = "waiting_info"
                elif final.get("escalate"):
                    status = "needs_staff"
                else:
                    status = "resolved"
                last_msg = ""
                for msg in reversed(session["history"]):
                    if msg["role"] == "customer":
                        last_msg = msg["content"]
                        break
                summaries.append({
                    "session_id": session["session_id"],
                    "customer_name": session["customer_name"],
                    "intent": final.get("intent"),
                    "category": final.get("category"),
                    "priority": final.get("priority"),
                    "escalate": final.get("escalate"),
                    "escalation_team": final.get("escalation_team"),
                    "ai_status": status,
                    "staff_status": session.get("staff_status", "new"),
                    "last_message": last_msg[:120],
                    "message_count": len(session["history"]),
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                })
            summaries.sort(key=lambda x: x["updated_at"], reverse=True)
            return summaries


class WebApp:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.static_dir = root / "web"
        self.sessions = SessionStore()

    def make_handler(self) -> type[BaseHTTPRequestHandler]:
        app = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/":
                    self._send_file(app.static_dir / "customer.html", "text/html; charset=utf-8")
                    return
                if parsed.path == "/staff":
                    self._send_file(app.static_dir / "staff.html", "text/html; charset=utf-8")
                    return
                if parsed.path == "/api/sessions":
                    self._send_json(app.sessions.list_all())
                    return
                if parsed.path == "/api/session":
                    qs = parse_qs(parsed.query)
                    sid = qs.get("id", [""])[0]
                    session = app.sessions.get(sid)
                    if session is None:
                        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                        return
                    self._send_json(session)
                    return
                if parsed.path.startswith("/static/"):
                    requested = parsed.path.removeprefix("/static/")
                    path = app.static_dir / requested
                    ct = "text/css; charset=utf-8" if path.suffix == ".css" else "application/javascript; charset=utf-8"
                    self._send_file(path, ct)
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/api/run":
                    self._handle_run()
                    return
                if parsed.path == "/api/session/update":
                    self._handle_session_update()
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def _handle_run(self) -> None:
                try:
                    body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    payload = json.loads(body.decode("utf-8") or "{}")
                    result = self._run_agents(payload)
                except Exception as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                session_id = str(payload.get("session_id", ""))
                customer_name = str(payload.get("customer_name", "Pelanggan")).strip() or "Pelanggan"
                message = str(payload.get("message", "")).strip()
                if session_id and message:
                    app.sessions.update(session_id, customer_name, message, result)
                self._send_json(result)

            def _handle_session_update(self) -> None:
                try:
                    body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    payload = json.loads(body.decode("utf-8") or "{}")
                except Exception:
                    self._send_json({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
                    return
                sid = str(payload.get("session_id", ""))
                result = app.sessions.update_staff(
                    sid,
                    staff_status=payload.get("staff_status"),
                    staff_notes=payload.get("staff_notes"),
                )
                if result is None:
                    self._send_json({"error": "Session not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json({"ok": True})

            def log_message(self, format: str, *args: object) -> None:
                return

            def _run_agents(self, payload: dict) -> dict:
                mode = payload.get("mode", "mock")
                message = str(payload.get("message", "")).strip()
                customer_name = str(payload.get("customer_name", "Pelanggan")).strip() or "Pelanggan"
                history = payload.get("history", [])
                if not message:
                    raise ValueError("Message is required.")
                transcript = self._build_transcript(history, message)
                ticket = {
                    "id": "web-chat",
                    "customer_name": customer_name,
                    "channel": "Web Chat",
                    "subject": "Customer web chat",
                    "message": transcript,
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

            def _build_transcript(self, history: object, message: str) -> str:
                lines = []
                if isinstance(history, list):
                    for item in history[-10:]:
                        if not isinstance(item, dict):
                            continue
                        role = str(item.get("role", "")).strip().lower()
                        content = str(item.get("content", "")).strip()
                        if role in {"customer", "assistant"} and content:
                            label = "Customer" if role == "customer" else "Assistant"
                            lines.append(f"{label}: {content}")
                lines.append(f"Customer: {message}")
                return "\n".join(lines)

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
    print(f"  Customer chat:    http://{host}:{port}/")
    print(f"  Staff dashboard:  http://{host}:{port}/staff")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def normalize_list(value: object) -> list:
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    if value in (None, ""):
        return []
    return [value]
