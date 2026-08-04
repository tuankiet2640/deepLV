"""Transactional email delivery via Resend's HTTP API.

Never raises: a Resend outage must not block registration or password
reset, and callers must not be able to distinguish "send failed" from
"recipient doesn't exist" (enumeration). When RESEND_API_KEY is unset
(local dev), the email content is logged instead of sent.
"""

import httpx
import structlog

from src.shared.config import APISettings

log = structlog.get_logger()
settings = APISettings()

RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, html: str) -> bool:
    if not settings.resend_api_key:
        log.warning("email_not_configured", to=to, subject=subject, preview=html[:200])
        return False

    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": settings.email_from_address,
        "to": [to],
        "subject": subject,
        "html": html,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(RESEND_API_URL, headers=headers, json=payload)
    except httpx.HTTPError as e:
        log.warning("email_send_failed", to=to, subject=subject, error=str(e))
        return False

    if resp.status_code >= 300:
        log.warning(
            "email_send_failed",
            to=to,
            subject=subject,
            status=resp.status_code,
            body=resp.text[:200],
        )
        return False

    return True


async def send_verification_email(to: str, code: str) -> bool:
    html = f"""
    <p>Your DeepLV verification code is:</p>
    <p style="font-size: 28px; font-weight: bold; letter-spacing: 4px;">{code}</p>
    <p>This code expires in 15 minutes. If you didn't request this, you can ignore this email.</p>
    """
    return await send_email(to, "Verify your DeepLV account", html)


async def send_password_reset_email(to: str, reset_link: str) -> bool:
    html = f"""
    <p>We received a request to reset your DeepLV password.</p>
    <p><a href="{reset_link}">Reset your password</a></p>
    <p>This link expires in 1 hour. If you didn't request this, you can ignore this email.</p>
    """
    return await send_email(to, "Reset your DeepLV password", html)
