"""Planner — turns a conversation turn into a typed :class:`ChatAction`.

Responsibility boundary: the planner decides *what* to do (action type + parameters) using the LLM,
then stamps governance requirements from a **trusted server-side policy table**. It never executes
anything and never trusts the model to set ``requires_owner`` / ``requires_approval``.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from nexus.communication.chat.contracts import ChatAction, ChatActionType

logger = structlog.get_logger("nexus.communication.chat.planner")

# Trusted governance policy per action type: (requires_owner, requires_approval).
# This is the ONLY place these flags are set — the LLM cannot influence them.
_ACTION_POLICY: dict[ChatActionType, tuple[bool, bool]] = {
    ChatActionType.REPLY: (False, False),
    ChatActionType.SEND_EMAIL: (True, False),  # owner-only, low-risk
    ChatActionType.CREATE_TASK: (True, False),
    ChatActionType.RUN_RESEARCH: (True, False),
    ChatActionType.SHOW_STATUS: (False, False),
    ChatActionType.APPROVAL_REQUEST: (True, True),
}

_SYSTEM_PROMPT = (
    "You are Nexus (call-sign 'Dex'), an AI Orchestration Control Plane assistant for your operator. "
    "Use the prior turns for context. Decide the single best action and reply with ONE JSON object "
    "and nothing else, using this schema:\n"
    '  {"type": "reply", "message": "<conversational answer>"}\n'
    '  {"type": "send_email", "subject": "<short>", "body": "<email body>"}\n'
    '  {"type": "create_task", "title": "<title>", "description": "<desc>", "priority": 2}\n'
    '  {"type": "run_research", "topic": "<topic>"}\n'
    '  {"type": "show_status"}\n'
    "Choose send_email ONLY when explicitly asked to email/mail/send something (it goes to the "
    "operator). Choose create_task / run_research only when explicitly asked to. Otherwise use "
    "reply. Optionally include a numeric \"confidence\" between 0 and 1."
)

# Map JSON "type" strings to enum, tolerant of synonyms.
_TYPE_ALIASES: dict[str, ChatActionType] = {
    "reply": ChatActionType.REPLY,
    "send_email": ChatActionType.SEND_EMAIL,
    "email": ChatActionType.SEND_EMAIL,
    "create_task": ChatActionType.CREATE_TASK,
    "task": ChatActionType.CREATE_TASK,
    "run_research": ChatActionType.RUN_RESEARCH,
    "research": ChatActionType.RUN_RESEARCH,
    "show_status": ChatActionType.SHOW_STATUS,
    "status": ChatActionType.SHOW_STATUS,
    "approval_request": ChatActionType.APPROVAL_REQUEST,
}


class Planner:
    """Plans a :class:`ChatAction` from a message + history using the LLM gateway."""

    def __init__(self, llm_client: Any) -> None:
        self.llm_client = llm_client

    async def plan(self, text: str, history: list[dict[str, str]] | None = None) -> ChatAction:
        """Produce a governance-stamped ChatAction; degrade to a plain REPLY on any failure."""
        if self.llm_client is None:
            return self._reply("⚠️ Chat is unavailable: no LLM gateway is configured.", confidence=1.0)
        try:
            raw = await self.llm_client.complete(
                text, system_prompt=_SYSTEM_PROMPT, history=history or []
            )
        except Exception as e:  # propagate as a reply; never crash the pipeline
            logger.error("planner_llm_failed", error=str(e))
            return self._reply(f"❌ Chat error: {e!s}", confidence=1.0)

        data = self._extract_json(raw)
        if data is None:
            # Not structured — treat the whole text as a conversational reply.
            return self._reply((raw or "").strip() or "(no response)")

        action_type = _TYPE_ALIASES.get(str(data.get("type", "reply")).lower(), ChatActionType.REPLY)
        payload = {k: v for k, v in data.items() if k not in ("type", "confidence")}
        if action_type is ChatActionType.REPLY and not payload.get("message"):
            payload["message"] = (raw or "").strip() or "(no response)"
        confidence = self._as_float(data.get("confidence"), default=0.9)
        requires_owner, requires_approval = _ACTION_POLICY[action_type]
        return ChatAction(
            type=action_type,
            payload=payload,
            confidence=confidence,
            requires_owner=requires_owner,
            requires_approval=requires_approval,
        )

    @staticmethod
    def _reply(message: str, confidence: float = 0.9) -> ChatAction:
        owner, approval = _ACTION_POLICY[ChatActionType.REPLY]
        return ChatAction(
            type=ChatActionType.REPLY,
            payload={"message": message},
            confidence=confidence,
            requires_owner=owner,
            requires_approval=approval,
        )

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any] | None:
        text = (raw or "").strip()
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            return None
        return data if isinstance(data, dict) and "type" in data else None

    @staticmethod
    def _as_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
