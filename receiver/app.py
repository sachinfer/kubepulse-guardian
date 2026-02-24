import os
import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from dateutil import tz

app = FastAPI(title="KubePulse Guardian Receiver", version="1.0")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
API_KEY = os.getenv("API_KEY", "")

IST = tz.gettz("Asia/Colombo")  # user timezone


class PodEvent(BaseModel):
    cluster: str = Field(..., examples=["pr", "dr"])
    namespace: str
    pod: str
    reason: str
    restarts: int = 0
    node: str | None = None
    severity: str = Field("warning", examples=["info", "warning", "critical"])
    timestamp: str | None = None  # ISO8601


def must_have_env():
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    if not API_KEY:
        raise RuntimeError("Missing API_KEY")


def to_local_time(ts: str | None) -> str:
    if not ts:
        dt = datetime.utcnow().replace(tzinfo=tz.gettz("UTC"))
    else:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.utcnow().replace(tzinfo=tz.gettz("UTC"))
    return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S %Z")


def telegram_send(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram send failed: {r.status_code} {r.text}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/event")
def event(evt: PodEvent, x_api_key: str = Header(default="")):
    must_have_env()
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    cluster = evt.cluster.upper()
    icon = "🚨" if evt.severity.lower() == "critical" else "⚠️" if evt.severity.lower() == "warning" else "ℹ️"
    time_local = to_local_time(evt.timestamp)

    msg = (
        f"{icon} KubePulse Guardian Alert\n"
        f"Cluster: {cluster}\n"
        f"Namespace: {evt.namespace}\n"
        f"Pod: {evt.pod}\n"
        f"Reason: {evt.reason}\n"
        f"Restarts: {evt.restarts}\n"
        f"Node: {evt.node or '-'}\n"
        f"Time: {time_local}"
    )

    telegram_send(msg)
    return {"sent": True}