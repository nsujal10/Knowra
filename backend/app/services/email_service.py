"""
Phase 26 – Enterprise Email Delivery Service

Provides robust, multi-provider outbound email delivery:
  1. Primary: Resend REST API (https://api.resend.com/emails)
  2. Fallback: Standard SMTP (Gmail, Microsoft 365, Amazon SES)
  3. Formatted HTML Executive Briefing templates with action items and decisions
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import requests
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


def generate_executive_briefing_html(
    meeting_title: str,
    summary: str,
    decisions: Optional[List[Dict[str, Any]]] = None,
    action_items: Optional[List[Dict[str, Any]]] = None,
    recipient_name: Optional[str] = None,
    meeting_date: Optional[str] = None,
) -> str:
    """Renders a responsive, high-end HTML executive meeting digest email."""

    decisions_html = ""
    if decisions:
        items_li = "".join(
            f"""
            <li style="margin-bottom: 12px; padding: 12px; background-color: #f8fafc; border-left: 3px solid #10b981; border-radius: 4px;">
                <div style="font-size: 13px; font-weight: 600; color: #0f172a;">{d.get('title', d.get('text', 'Decision'))}</div>
                <div style="font-size: 12px; color: #64748b; margin-top: 4px;">{d.get('description', d.get('summary', ''))}</div>
                <div style="font-size: 11px; color: #059669; font-weight: 600; margin-top: 4px;">
                    Consensus: {d.get('consensus', '100% Unanimous')} &bull; Decided by: {d.get('decided_by', 'Leadership')}
                </div>
            </li>
            """
            for d in decisions
        )
        decisions_html = f"""
        <div style="margin-top: 24px;">
            <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; margin-bottom: 12px;">
                &#9878; Key Confirmed Decisions ({len(decisions)})
            </h3>
            <ul style="list-style: none; padding: 0; margin: 0;">
                {items_li}
            </ul>
        </div>
        """

    actions_html = ""
    if action_items:
        rows = "".join(
            f"""
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 10px 8px; font-size: 13px; color: #1e293b; font-weight: 500;">
                    {a.get('title', a.get('item_title', 'Action Item'))}
                </td>
                <td style="padding: 10px 8px; font-size: 12px; color: #4338ca; font-weight: 600;">
                    {a.get('assignee', a.get('assigned_to', 'Unassigned'))}
                </td>
                <td style="padding: 10px 8px; font-size: 11px;">
                    <span style="background-color: #fef2f2; color: #b91c1c; padding: 2px 8px; border-radius: 9999px; font-weight: 600;">
                        {a.get('priority', 'URGENT')}
                    </span>
                </td>
            </tr>
            """
            for a in action_items
        )
        actions_html = f"""
        <div style="margin-top: 24px;">
            <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; margin-bottom: 12px;">
                &#10003; Assigned Deliverables & Action Items ({len(action_items)})
            </h3>
            <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                <thead>
                    <tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; text-align: left;">
                        <th style="padding: 8px; font-size: 11px; text-transform: uppercase; color: #64748b;">Task</th>
                        <th style="padding: 8px; font-size: 11px; text-transform: uppercase; color: #64748b;">Owner</th>
                        <th style="padding: 8px; font-size: 11px; text-transform: uppercase; color: #64748b;">Priority</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{meeting_title} - Executive Briefing</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; color: #1e293b;">
        <div style="max-width: 640px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;">
            <!-- Brand Header -->
            <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%); padding: 32px 28px; text-align: left;">
                <div style="display: inline-block; padding: 4px 10px; background-color: rgba(255, 255, 255, 0.15); border-radius: 9999px; font-size: 11px; font-weight: 600; color: #e0e7ff; margin-bottom: 12px; letter-spacing: 0.05em; text-transform: uppercase;">
                    &#9889; Knowra Executive Intelligence
                </div>
                <h1 style="color: #ffffff; font-size: 22px; font-weight: 700; margin: 0; line-height: 1.3;">
                    {meeting_title}
                </h1>
                <div style="color: #c7d2fe; font-size: 12px; margin-top: 8px;">
                    Date: {meeting_date or 'Today'} &bull; Delivery: Realtime AI Synthesis
                </div>
            </div>

            <!-- Content Container -->
            <div style="padding: 28px;">
                <!-- Summary Box -->
                <div style="background-color: #f8fafc; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #6366f1; letter-spacing: 0.05em; margin-bottom: 8px;">
                        Executive Meeting Summary
                    </div>
                    <p style="font-size: 13.5px; line-height: 1.6; color: #334155; margin: 0;">
                        {summary}
                    </p>
                </div>

                <!-- Decisions -->
                {decisions_html}

                <!-- Actions -->
                {actions_html}

                <!-- CTAs -->
                <div style="margin-top: 32px; text-align: center; padding-top: 24px; border-top: 1px solid #e2e8f0;">
                    <a href="{settings.FRONTEND_URL}/meetings" style="display: inline-block; background-color: #4f46e5; color: #ffffff; text-decoration: none; font-size: 13px; font-weight: 600; padding: 12px 24px; border-radius: 8px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
                        Open in Knowra Workspace &rarr;
                    </a>
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f8fafc; padding: 16px 28px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; line-height: 1.5;">
                This executive briefing was synthesized automatically by Knowra AI for {recipient_name or 'Workspace Attendees'}.<br>
                Payload encrypted at rest via AES-256 Fernet &bull; Confidential Enterprise Communication.
            </div>
        </div>
    </body>
    </html>
    """


def send_email_via_resend(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Delivers an email using Resend REST API (https://api.resend.com/emails).
    Falls back gracefully if RESEND_API_KEY is not yet supplied.
    """
    api_key = settings.RESEND_API_KEY.strip()
    from_email = settings.RESEND_FROM_EMAIL.strip() or "Knowra Intelligence <onboarding@resend.dev>"

    if not api_key:
        logger.warning(
            "RESEND_API_KEY is not configured in .env. Simulating delivery.",
            to=to_email,
            subject=subject,
        )
        return {
            "status": "SIMULATED",
            "id": "simulated_resend_dev_id",
            "message": "Email simulated: Set RESEND_API_KEY in .env to deliver live emails.",
        }

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }
    if text_content:
        payload["text"] = text_content

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12.0)
        if response.status_code in (200, 201):
            res_data = response.json()
            logger.info("Resend email delivered successfully", to=to_email, resend_id=res_data.get("id"))
            return {
                "status": "DELIVERED",
                "id": res_data.get("id"),
                "status_code": response.status_code,
            }
        else:
            logger.error("Resend API error", status_code=response.status_code, text=response.text)
            return {
                "status": "FAILED",
                "status_code": response.status_code,
                "error": response.text,
            }
    except Exception as exc:
        logger.error("Resend request failed", error=str(exc))
        return {
            "status": "FAILED",
            "error": str(exc),
        }


def send_email_via_smtp(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> Dict[str, Any]:
    """Fallback standard SMTP email sender."""
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        return {"status": "SKIPPED", "message": "SMTP not configured"}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email

    if text_content:
        msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        if settings.SMTP_TLS:
            server.starttls()
        if settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info("SMTP email delivered successfully", to=to_email)
        return {"status": "DELIVERED", "provider": "SMTP"}
    except Exception as exc:
        logger.error("SMTP delivery failed", error=str(exc))
        return {"status": "FAILED", "error": str(exc)}
