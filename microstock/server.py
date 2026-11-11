"""Local Desktop REST & IPC Server.

Provides a fast, zero-dependency HTTP server on localhost that bridges the
desktop frontend (Tauri shell or native webview window) to the microstock core pipeline.
Eliminates Streamlit's full-script re-execution and high memory consumption.
"""
from __future__ import annotations

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import socketserver
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import (
    analytics,
    compliance,
    config,
    db,
    distributor,
    folder_watcher,
    metadata,
    prompt_enhancer,
    seasonality,
    security,
)

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class DesktopAPIHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the desktop SPA and REST API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        """Mute standard access log output to keep terminal clean."""
        pass

    def _send_json(self, status: int, data: Any):
        """Send a JSON HTTP response with CORS headers for local IPC."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        """Route GET requests to API endpoints or static web assets."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            sec_info = security.get_security_status()
            recent_assets = db.list_recent_assets(limit=1)
            api_key = security.get_gemini_api_key()
            self._send_json(200, {
                "status": "online",
                "version": "2.5.0-desktop",
                "database_mode": "SQLite WAL",
                "total_assets": len(db.list_recent_assets(limit=1000)),
                "has_api_key": bool(api_key),
                "security": sec_info,
                "default_download_dir": folder_watcher.get_default_downloads_dir(),
            })
            return

        elif path == "/api/assets":
            query = parse_qs(parsed.query)
            limit = int(query.get("limit", [50])[0])
            assets = db.list_recent_assets(limit=limit)
            self._send_json(200, {"assets": assets})
            return

        elif path == "/api/categories":
            self._send_json(200, {
                "adobe_categories": metadata.ADOBE_CATEGORIES,
                "shutterstock_categories": metadata.SHUTTERSTOCK_CATEGORIES,
            })
            return

        elif path == "/api/submissions":
            logs = db.list_recent_submissions(limit=50)
            self._send_json(200, {"submissions": logs})
            return

        elif path == "/api/seasonality":
            opps = seasonality.get_current_seasonal_opportunities()
            self._send_json(200, {"seasonality": [o.to_dict() for o in opps]})
            return

        elif path == "/api/analytics":
            stats = analytics.get_curation_analytics()
            self._send_json(200, {"analytics": stats})
            return

        # Fallback to static files in WEB_DIR (SPA index.html)
        if path == "/" or not os.path.exists(os.path.join(WEB_DIR, path.lstrip("/"))):
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        """Route POST requests to API action endpoints."""
        parsed = urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_len) if content_len > 0 else b""
        payload = {}
        if raw_body:
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception:
                pass

        api_key = payload.get("api_key") or security.get_gemini_api_key()

        if path == "/api/prompt/generate":
            idea = payload.get("idea", "")
            style_cat = payload.get("style_category", config.DEFAULT_STYLE_CATEGORY)
            style_name = payload.get("style", config.DEFAULT_STYLE)
            aspect_ratio = payload.get("aspect_ratio", "16:9")
            lighting = payload.get("lighting")
            lens = payload.get("lens")

            if not idea:
                self._send_json(400, {"error": "Ide prompt tidak boleh kosong."})
                return
            if not api_key:
                self._send_json(400, {"error": "API Key belum disetel."})
                return

            try:
                result = prompt_enhancer.enhance_prompt(
                    base_idea=idea,
                    api_key=api_key,
                    style_category=style_cat,
                    style=style_name,
                    aspect_ratio=aspect_ratio,
                    lighting=lighting,
                    lens=lens,
                )
                self._send_json(200, {"result": result.to_dict()})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        elif path == "/api/compliance/check":
            title = payload.get("title", "")
            desc = payload.get("description", "")
            keywords = payload.get("keywords", [])
            prompt = payload.get("prompt", "")

            rep = compliance.evaluate_commercial_compliance(title, desc, keywords, prompt)
            self._send_json(200, {"compliance": rep.to_dict()})
            return

        elif path == "/api/accounts/save":
            agency = payload.get("agency_name", "")
            host = payload.get("host", "")
            port = int(payload.get("port", 21))
            proto = payload.get("protocol", "ftp")
            user = payload.get("username", "")
            pwd = payload.get("password", "")

            if not agency or not user:
                self._send_json(400, {"error": "Nama agensi dan username wajib diisi."})
                return

            db.save_agency_account(agency, host, port, proto, user, pwd)
            self._send_json(200, {"success": True, "message": f"Kredensial untuk {agency} berhasil disimpan."})
            return

        elif path == "/api/accounts/test":
            host = payload.get("host", "")
            port = int(payload.get("port", 21))
            proto = payload.get("protocol", "ftp")
            user = payload.get("username", "")
            pwd = payload.get("password", "")

            ok, msg = distributor.test_agency_connection(host, port, proto, user, pwd)
            self._send_json(200, {"success": ok, "message": msg})
            return

        self._send_json(404, {"error": f"Endpoint '{path}' tidak ditemukan."})


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_desktop_server(host: str = "127.0.0.1", port: int = 8505) -> ThreadedHTTPServer:
    """Start local desktop server on localhost."""
    os.makedirs(WEB_DIR, exist_ok=True)
    server = ThreadedHTTPServer((host, port), DesktopAPIHandler)
    return server

