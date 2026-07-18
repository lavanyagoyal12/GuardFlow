from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.logger import logger
from app.core.settings import settings
from app.services.prompt_builder import PromptBuilder


class LLMService:
    """Calls a local Ollama instance and returns a normalized website-risk payload."""

    def __init__(self, client: httpx.Client | None = None, prompt_builder: PromptBuilder | None = None):
        # NOTE: timeout is intentionally generous (default 30s, see settings).
        # Local Ollama inference - especially the first call after a model is
        # loaded into memory - routinely takes several seconds. A short
        # timeout here was the main cause of "LLM unavailable" fallbacks: the
        # request was simply cut off before Ollama finished responding, not a
        # real connectivity failure.
        self.client = client or httpx.Client(timeout=httpx.Timeout(settings.OLLAMA_TIMEOUT))
        self.prompt_builder = prompt_builder or PromptBuilder()
        # Built once from settings.OLLAMA_URL (configurable via .env), instead
        # of a hardcoded "http://127.0.0.1:11434" - this is what let the
        # service silently fail whenever Ollama wasn't reachable at exactly
        # that hardcoded address (different port, Docker host, remote box,
        # WSL, etc).
        self._generate_url = f"{settings.OLLAMA_URL.rstrip('/')}/api/generate"

    def analyze_page(self, page_analysis: dict[str, Any] | None, events: list[Any] | None = None) -> dict[str, Any]:
        prompt = self.prompt_builder.build_prompt(page_analysis, events)
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }

        try:
            response = self.client.post(self._generate_url, json=payload)
            response.raise_for_status()
            return self._normalize_llm_payload(response.json())

        except httpx.ConnectError as exc:
            # Ollama isn't reachable at all at settings.OLLAMA_URL - almost
            # always means the Ollama service isn't running, or OLLAMA_URL
            # in .env doesn't match where it's actually listening.
            logger.error(
                f"Ollama unreachable at {self._generate_url}: {exc}. "
                f"Is 'ollama serve' running, and does OLLAMA_URL in .env "
                f"match its address?"
            )
        except httpx.TimeoutException as exc:
            # Ollama is reachable but didn't respond in time - usually a slow
            # model load or a model that's too large for the machine, not a
            # connectivity problem. Distinguished from ConnectError so it's
            # obvious in logs which situation you're in.
            logger.warning(
                f"Ollama request timed out after {settings.OLLAMA_TIMEOUT}s: {exc}. "
                f"Consider raising OLLAMA_TIMEOUT or using a smaller model."
            )
        except httpx.HTTPStatusError as exc:
            # Reached Ollama, but it returned an error status - most common
            # cause is settings.OLLAMA_MODEL not being pulled locally (404).
            logger.error(
                f"Ollama returned {exc.response.status_code} for model "
                f"'{settings.OLLAMA_MODEL}': {exc}. Run 'ollama pull "
                f"{settings.OLLAMA_MODEL}' if the model isn't available yet."
            )
        except Exception as exc:
            logger.warning(f"Ollama analysis failed: {exc}")

        return {
            "website_score": 0,
            "confidence": 20,
            "reasons": ["LLM unavailable; used fallback score"],
            "indicators": [],
        }

    def _normalize_llm_payload(self, llm_payload: dict[str, Any]) -> dict[str, Any]:
        text = None
        if isinstance(llm_payload, dict):
            text = llm_payload.get("response") or llm_payload.get("text")
        if not isinstance(text, str) or not text.strip():
            return {
                "website_score": 0,
                "confidence": 20,
                "reasons": ["Invalid LLM response; used fallback score"],
                "indicators": [],
            }

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`\n")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                parsed = json.loads(cleaned.split("{", 1)[1].rsplit("}", 1)[0])
            except Exception:
                logger.warning(f"Could not parse LLM response as JSON: {cleaned[:200]!r}")
                return {
                    "website_score": 0,
                    "confidence": 20,
                    "reasons": ["Invalid LLM response; used fallback score"],
                    "indicators": [],
                }

        website_score = int(parsed.get("website_score", 0))
        confidence = int(parsed.get("confidence", 20))
        reasons = parsed.get("reasons") or ["No reasons provided"]
        indicators = parsed.get("indicators") or []
        if not isinstance(reasons, list):
            reasons = [str(reasons)]
        if not isinstance(indicators, list):
            indicators = [str(indicators)]

        return {
            "website_score": max(0, min(100, website_score)),
            "confidence": max(0, min(100, confidence)),
            "reasons": [str(reason) for reason in reasons[:5]],
            "indicators": [str(indicator) for indicator in indicators[:8]],
        }
