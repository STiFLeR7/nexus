"""OpenRouter LLM gateway integration client.

Handles connection to the OpenRouter completions API, error catching,
and sequential model fallbacks.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from nexus.config import get_settings
from nexus.core.exceptions import ModelRouterError

logger = structlog.get_logger("nexus.intelligence.openrouter")


class OpenRouterClient:
    """Gateway client to generate completions via OpenRouter with fallbacks."""

    def __init__(self, settings: Any = None) -> None:
        """Initialize settings and endpoints config."""
        self.settings = settings or get_settings()

    async def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Post a completion prompt to OpenRouter, with fallbacks on failure."""
        api_key = self.settings.openrouter.api_key
        if not api_key:
            raise ModelRouterError("OpenRouter API key is missing from configuration.")

        # Compile fallback list: primary model followed by fallback list
        models = [self.settings.openrouter.primary_model, *self.settings.openrouter.fallback_models]
        last_error: Exception | None = None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/STiFLeR7/nexus",
            "X-Title": "Nexus Control Plane",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in models:
                if not model:
                    continue

                logger.info("attempting_llm_completion", model=model)
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.2,
                }

                try:
                    import time
                    start_time = time.perf_counter()
                    res = await client.post(
                        f"{self.settings.openrouter.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )

                    if res.status_code != 200:
                        raise httpx.HTTPStatusError(
                            f"OpenRouter API error: Status {res.status_code}. Response: {res.text}",
                            request=res.request,
                            response=res,
                        )

                    data = res.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise ModelRouterError(f"OpenRouter response contained no choices: {data}")

                    content = choices[0].get("message", {}).get("content", "")
                    duration = (time.perf_counter() - start_time) * 1000.0
                    from nexus.core.metrics import record_metric
                    record_metric("openrouter_latency_ms", duration)
                    logger.info("llm_completion_successful", model=model, openrouter_latency_ms=round(duration, 2))
                    return str(content)

                except Exception as e:
                    logger.warning(
                        "llm_completion_failed_falling_back",
                        model=model,
                        error=str(e),
                    )
                    last_error = e

        # If we got here, all models in the fallback chain failed
        raise ModelRouterError(
            f"All configured models failed completion. Last error: {last_error!s}"
        )
