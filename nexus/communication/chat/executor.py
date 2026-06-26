"""Executor — performs a validated :class:`ChatAction` via injected services.

Responsibility boundary: the executor decides *how* to carry out an action. It calls domain services
(EmailService, …) that are injected, emits a SYSTEM status card for side-effecting actions, and
returns a transport-neutral :class:`ChatResponse`. It performs no governance decisions (the Validator
already approved) and no LLM calls.
"""

from __future__ import annotations

from typing import Any

import structlog

from nexus.communication.channels import ChannelRole
from nexus.communication.chat.contracts import (
    ChatAction,
    ChatActionType,
    ChatResponse,
    OutboundPost,
)

logger = structlog.get_logger("nexus.communication.chat.executor")


class Executor:
    """Executes validated actions against injected domain services."""

    def __init__(self, email_service: Any = None, owner_email: str = "") -> None:
        self.email_service = email_service
        self.owner_email = owner_email

    async def execute(self, action: ChatAction) -> ChatResponse:
        """Dispatch the action; return a transport-neutral response."""
        if action.type is ChatActionType.REPLY:
            return ChatResponse(
                reply=str(action.payload.get("message") or "(no response)"),
                action_type=action.type,
                executed=True,
            )
        if action.type is ChatActionType.SEND_EMAIL:
            return await self._send_email(action)
        # Recognized but not yet wired to a domain service — honest, non-crashing response.
        return ChatResponse(
            reply=f"That action (`{action.type.value}`) is recognized but not wired up yet.",
            action_type=action.type,
            executed=False,
        )

    async def _send_email(self, action: ChatAction) -> ChatResponse:
        subject = str(action.payload.get("subject") or "Message from Nexus").strip()
        body = str(action.payload.get("body") or "").strip()
        recipient = self.owner_email or "operator"

        if self.email_service is None:
            return ChatResponse(
                reply="⚠️ Email is not configured.",
                action_type=ChatActionType.SEND_EMAIL,
                executed=False,
                posts=[_card(subject, "failed")],
            )
        try:
            html = (
                "<div style='font-family:sans-serif;line-height:1.5;white-space:pre-wrap'>"
                f"{body}</div>"
            )
            await self.email_service.send_briefing_email(subject, body, html)
        except Exception as e:  # surface failure; never crash
            logger.error("executor_send_email_failed", error=str(e))
            return ChatResponse(
                reply=f"❌ Email failed: {e!s}",
                action_type=ChatActionType.SEND_EMAIL,
                executed=False,
                posts=[_card(subject, "failed")],
            )
        logger.info("executor_email_sent", recipient=recipient, subject=subject)
        return ChatResponse(
            reply=f"📧 Sent to **{recipient}** — *{subject}*",
            action_type=ChatActionType.SEND_EMAIL,
            executed=True,
            posts=[_card(subject, "sent")],
        )


def _card(subject: str, verification: str) -> OutboundPost:
    """Build a SYSTEM-channel status card for an email action."""
    return OutboundPost(
        role=ChannelRole.SYSTEM,
        card={
            "title": "Dex • Email Action",
            "risk": "LOW",
            "plan": f"Email operator: {subject}",
            "tools": "send_email",
            "verification": verification,
        },
    )
