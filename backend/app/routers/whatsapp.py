"""
WhatsApp Autonomous Engine Router — Proxies and manages local Baileys service.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import urllib.request
import json

from app.auth import get_current_user
from app.whatsapp_manager import ensure_whatsapp_running

from datetime import datetime

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

SERVICE_URL = "http://127.0.0.1:3001/api/whatsapp"


class SendWhatsAppRequest(BaseModel):
    phone: str
    message: str


class SendTestRequest(BaseModel):
    phone: str


def _call_service(endpoint: str, method: str = "GET", data: Optional[dict] = None, timeout: float = 4.0):
    url = f"{SERVICE_URL}/{endpoint.lstrip('/')}"
    try:
        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        headers = {"Content-Type": "application/json"} if req_data else {}
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        ensure_whatsapp_running()
        return {
            "connected": False,
            "state": "offline",
            "user": None,
            "qr": None,
            "error": f"WhatsApp engine offline or starting ({str(e)})"
        }


@router.get("/status")
def get_whatsapp_status(current_user=Depends(get_current_user)):
    """Fetch current connection status and QR code."""
    res = _call_service("status", method="GET")
    return res


@router.post("/refresh-qr")
def refresh_whatsapp_qr(current_user=Depends(get_current_user)):
    """Force generate a fresh WhatsApp QR code."""
    res = _call_service("refresh-qr", method="POST", data={})
    return res


@router.post("/disconnect")
def disconnect_whatsapp(current_user=Depends(get_current_user)):
    """Unlink current WhatsApp account and regenerate QR."""
    res = _call_service("disconnect", method="POST", data={})
    return res


@router.post("/send")
def send_whatsapp(req: SendWhatsAppRequest, current_user=Depends(get_current_user)):
    """Send text bill or notification."""
    res = _call_service("send", method="POST", data={"phone": req.phone, "message": req.message}, timeout=10.0)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to dispatch WhatsApp message"))
    return res


@router.post("/send-test")
def send_test_whatsapp(req: SendTestRequest, current_user=Depends(get_current_user)):
    """Send a test message to verify autonomous delivery."""
    now_str = datetime.now().strftime("%d/%m/%Y, %I:%M %p")
    test_msg = (
        "💎 *MOIRA LUXE BILLING SYSTEM* 💎\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ *WhatsApp Connection Test Successful!*\n\n"
        "Your billing software is now autonomously connected to WhatsApp.\n"
        "Customer bills will be dispatched in real-time.\n\n"
        f"📅 Verified on: {now_str}\n"
        "✨ *Thank you!* ✨"
    )
    res = _call_service("send", method="POST", data={"phone": req.phone, "message": test_msg}, timeout=10.0)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to send test message"))
    return res
