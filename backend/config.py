"""Environment-backed configuration for the LegalEdge inbound intake backend.

Self-contained: loads backend/.env first (primary), then a folder-root .env as a
fallback (override=False) so the whole `legaledge/` tree relocates cleanly with
its own secrets. Shares only Twilio + Gemini credentials with the interviewer;
no shared code, port, database, or process.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

_HERE = Path(__file__).resolve().parent
# backend/.env first (primary), then the folder-root .env as a non-overriding
# fallback for values shared with the frontend build.
load_dotenv(_HERE / ".env")
load_dotenv(_HERE.parent / ".env", override=False)


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


class Settings:
    def __init__(self) -> None:
        # ── Gemini (reuse the interviewer's key + Live model) ─────────────────
        self.GEMINI_API_KEY = _get("GEMINI_API_KEY")
        self.GEMINI_LIVE_MODEL = _get("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
        self.GEMINI_VOICE = _get("GEMINI_VOICE", "Puck")

        # ── Twilio (SAME account as the interviewer; no REST client needed) ───
        # Dedicated INBOUND number this agent answers on.
        self.TWILIO_INBOUND_NUMBER = _get("TWILIO_INBOUND_NUMBER")
        # Optional: enables X-Twilio-Signature validation on /api/voice.
        self.TWILIO_AUTH_TOKEN = _get("TWILIO_AUTH_TOKEN")

        # ── Public origin (include the /legalEdge subpath) ───────────────────
        self.PUBLIC_URL = _get("PUBLIC_URL", "http://localhost:8091").rstrip("/")
        # Optional host[/path] override for the wss:// base (no scheme).
        self.PUBLIC_DOMAIN = _get("PUBLIC_DOMAIN")
        self.SUBPATH = _get("SUBPATH", "/legalEdge")

        # ── Firm identity / conversation ─────────────────────────────────────
        self.FIRM_NAME = _get("FIRM_NAME", "Wexler & Associates")
        self.AGENT_NAME = _get("AGENT_NAME", "Jordan")
        self.INTAKE_TIMEZONE = _get("INTAKE_TIMEZONE", "America/New_York")

        # ── SQLite (relative path so the folder relocates cleanly) ───────────
        self.DB_PATH = _get("DB_PATH", "./legaledge.db")

        # ── Dashboard read-endpoint gate (optional) ─────────────────────────
        self.DASHBOARD_API_KEY = _get("DASHBOARD_API_KEY")

        # ── LegalEdge CRM push — STUBBED (echoed, unused by the stub) ────────
        self.LEGALEDGE_API_BASE = _get("LEGALEDGE_API_BASE", "https://api.legaledge.example/v1")
        self.LEGALEDGE_API_KEY = _get("LEGALEDGE_API_KEY")

    def require_gemini(self) -> None:
        if not self.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set — required to bridge to Gemini Live.")

    @property
    def public_ws_base(self) -> str:
        """wss:// base for Twilio Media Streams. Uses PUBLIC_DOMAIN (host[/path],
        no scheme) if set, else derives from PUBLIC_URL by swapping the scheme so
        any subpath (e.g. /legalEdge) is preserved. Copied verbatim from the
        screening config.py public_ws_base logic."""
        if self.PUBLIC_DOMAIN:
            host = self.PUBLIC_DOMAIN.replace("https://", "").replace("http://", "").rstrip("/")
            return f"wss://{host}"
        base = self.PUBLIC_URL
        if base.startswith("https://"):
            return "wss://" + base[len("https://") :]
        if base.startswith("http://"):
            return "ws://" + base[len("http://") :]
        return base


settings = Settings()
