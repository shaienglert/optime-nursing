"""Event-driven, durable user incident mail. Never store request bodies or errors."""
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from app.database import SessionLocal
from app.models.agent_execution import SupervisorIncidentLog
from app.services.email_service import send_email_detailed, validate_email_configuration

log = logging.getLogger(__name__)
TYPE = "USER_SITE_INCIDENT"
OWNER = "shaienglert@gmail.com"
wake = threading.Event()
stop = threading.Event()
worker = None
lock = threading.Lock()
browser_counts = {}
USER_PAGES = {"/", "/intake", "/intake-confirmation", "/adaptive-interview", "/results", "/facilities", "/compare"}


def production_origins():
    return {s.strip().rstrip("/") for s in os.getenv("OOMNIK_USER_INCIDENT_PRODUCTION_ORIGINS", "https://optime-nursing.vercel.app").split(",") if s.strip().startswith("https://")}


def user_request_page(scope):
    if os.getenv("OOMNIK_USER_INCIDENT_ALERTS_ENABLED", "0") != "1":
        return None
    path = scope.get("path", "")
    if path.startswith(("/admin", "/health", "/api/user-incidents")):
        return None
    headers = dict(scope.get("headers", []))
    try:
        referer = urlsplit(headers.get(b"referer", b"").decode("latin-1"))
    except ValueError:
        return None
    origin = f"{referer.scheme}://{referer.netloc}"
    page = "/" if referer.path == "/" else safe_path(referer.path)
    if origin not in production_origins() or page not in USER_PAGES:
        return None
    return page


def safe_path(path):
    # Do not retain tokens, IDs, queries or personal destinations.
    if str(path).split("?")[0] == "/":
        return "/"
    first = str(path).split("?")[0].strip("/").split("/")[0]
    known = {"intake", "intake-confirmation", "adaptive-interview", "results", "facilities",
             "decision-engine", "personal-report", "api", "compare", "health"}
    return "/" + first if first in known else "/other"


def record_incident(*, kind, path, status=0, event_id=None):
    if kind == "DELIVERY_PROBE":
        return None
    event_id = str(event_id or uuid.uuid4())
    data = {"event_id": event_id, "kind": kind, "path": safe_path(path), "status": status,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "version": os.getenv("RENDER_GIT_COMMIT", "UNKNOWN"),
            "delivery": "PENDING", "attempts": 0, "retry_at": 0,
            "scope": "PRODUCTION_USER"}
    db = SessionLocal()
    try:
        summary = "OOmnik incident " + event_id
        old = db.query(SupervisorIncidentLog).filter_by(incident_type=TYPE, summary=summary).first()
        if old is not None:
            return event_id
        db.add(SupervisorIncidentLog(incident_type=TYPE, severity="HIGH", status="PENDING",
                                    agent_key="user_incident_delivery", domain="website",
                                    summary=summary, details_json=json.dumps(data)))
        db.commit()
        wake.set()  # Immediate delivery wake-up; retry timer is only a fallback.
        return event_id
    finally:
        db.close()


def emit_safely(**kwargs):
    try:
        return record_incident(**kwargs)
    except Exception:
        log.error("user_incident_persistence_failed", exc_info=False)
        return None


def deliver_pending(limit=10):
    delivered = 0
    for _ in range(limit):
        db = SessionLocal()
        try:
            rows = (db.query(SupervisorIncidentLog).filter_by(incident_type=TYPE, status="PENDING")
                    .order_by(SupervisorIncidentLog.id).with_for_update(skip_locked=True).limit(50).all())
            row = next((r for r in rows if json.loads(r.details_json).get("retry_at", 0) <= time.time()), None)
            if row is None:
                return delivered
            data = json.loads(row.details_json)
            if data.get("scope") != "PRODUCTION_USER" or data.get("kind") == "DELIVERY_PROBE":
                row.status = "SUPPRESSED"
                db.commit()
                continue
            data["attempts"] += 1
            # SQL transaction lock prevents concurrent workers mailing the same row.
            result = send_email_detailed(subject="OOmnik SITE INCIDENT " + data["event_id"],
                                        body_text=json.dumps(data, ensure_ascii=False, indent=2),
                                        recipients=[OWNER], max_retries=0)
            accepted = result.ok and result.status == "DELIVERY_ACCEPTED"
            data["delivery"] = "SMTP_ACCEPTED" if accepted else "DELIVERY_BLOCKED"
            data["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
            data["retry_at"] = time.time() + min(300, 15 * 2 ** min(data["attempts"], 5))
            row.details_json = json.dumps(data)
            if accepted:
                row.status = "NOTIFIED"
                delivered += 1
            db.commit()
            log.info("user_incident_delivery event_id=%s status=%s", data["event_id"], data["delivery"])
        except Exception:
            db.rollback()
            log.error("user_incident_delivery_failed", exc_info=False)
            return delivered
        finally:
            db.close()
    return delivered


def run_worker():
    while not stop.is_set():
        wake.wait(15)
        wake.clear()
        if not stop.is_set():
            deliver_pending()


def start_worker():
    global worker
    if os.getenv("OOMNIK_USER_INCIDENT_ALERTS_ENABLED", "0") != "1":
        return
    with lock:
        if worker is None or not worker.is_alive():
            stop.clear()
            worker = threading.Thread(target=run_worker, name="user-incident-mail", daemon=True)
            worker.start()
            wake.set()


class ClientIncident(BaseModel):
    kind: Literal["CLIENT_RUNTIME_ERROR", "UNHANDLED_REJECTION", "API_FAILURE"]
    page: Literal["/", "/intake", "/intake-confirmation", "/adaptive-interview", "/results", "/facilities", "/compare"]
    event_id: uuid.UUID


class IncidentMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        page = user_request_page(scope)
        if page is None:
            return await self.app(scope, receive, send)
        import asyncio
        reported = False
        async def send_with_incident(message):
            nonlocal reported
            if message["type"] == "http.response.start" and message["status"] >= 500:
                reported = True
                await asyncio.to_thread(emit_safely, kind="SERVER_HTTP_ERROR", path=page, status=message["status"])
            await send(message)
        try:
            await self.app(scope, receive, send_with_incident)
        except Exception:
            if not reported:
                await asyncio.to_thread(emit_safely, kind="SERVER_EXCEPTION", path=page, status=500)
            raise


def install_incident_reporting(app, origins):
    app.add_middleware(IncidentMiddleware)
    app.router.add_event_handler("startup", start_worker)
    app.router.add_event_handler("shutdown", lambda: (stop.set(), wake.set()))

    @app.get("/api/user-incidents/status")
    def incident_status():
        cfg = validate_email_configuration()
        return {"enabled": os.getenv("OOMNIK_USER_INCIDENT_ALERTS_ENABLED", "0") == "1",
                "worker_running": worker is not None and worker.is_alive(),
                "mail_configured": cfg["configured"], "delivery_mode": "EVENT_DRIVEN",
                "alert_scope": "PRODUCTION_USER"}

    @app.post("/api/user-incidents", status_code=202)
    async def client_incident(payload: ClientIncident, request: Request):
        if os.getenv("OOMNIK_USER_INCIDENT_ALERTS_ENABLED", "0") != "1":
            raise HTTPException(403, "Production user alerts disabled")
        if request.headers.get("origin") not in production_origins() or request.headers.get("origin") not in origins:
            raise HTTPException(403, "Unknown site origin")
        # Bounded public telemetry; never accept free text, recipient or error payload.
        key = (request.client.host if request.client else "unknown", int(time.time() // 60))
        with lock:
            for old in list(browser_counts):
                if old[1] != key[1]:
                    del browser_counts[old]
            browser_counts[key] = browser_counts.get(key, 0) + 1
            if browser_counts[key] > 10 or sum(browser_counts.values()) > 100:
                raise HTTPException(429, "Incident telemetry rate limit")
        import asyncio
        event = await asyncio.to_thread(emit_safely, kind=payload.kind, path=payload.page, event_id=payload.event_id)
        if event is None:
            raise HTTPException(503, "Incident storage unavailable")
        return {"event_id": event, "persisted": True, "delivery": "PENDING"}
