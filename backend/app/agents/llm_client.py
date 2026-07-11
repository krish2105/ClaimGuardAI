"""Thin wrapper around the Claude API used by the reasoning/extraction agents.

If ANTHROPIC_API_KEY is unset, every call transparently falls back to a
deterministic, rule-based mock so the entire 5-agent pipeline is runnable
end-to-end with zero cost and zero external dependency (see each agent's
`_mock_*` function). This is a demo-mode fallback, not a design shortcut:
production use sets ANTHROPIC_API_KEY and the same code path calls Claude.
"""
import json
import re
from typing import Callable, Optional

from app.config import get_settings


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


class LLMClient:
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        if not self.settings.llm_mock_mode:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self.settings.anthropic_api_key)

    @property
    def mock_mode(self) -> bool:
        return self._client is None

    def call_json(
        self,
        *,
        system: str,
        user: str,
        model: str,
        mock_fn: Callable[[], dict],
        max_tokens: int = 1024,
        max_retries: int = 2,
    ) -> dict:
        if self.mock_mode:
            return mock_fn()

        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                text = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                return _extract_json(text)
            except Exception as exc:  # noqa: BLE001 - any LLM/JSON failure retries then falls back
                last_error = exc
                continue

        result = mock_fn()
        result["_llm_error"] = str(last_error)
        result["_llm_fallback"] = True
        return result


_singleton: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
