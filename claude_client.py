"""Thin wrapper around the Anthropic Claude API.

Isolated here so the rest of the app does not depend on a specific SDK
version. If the organisation later moves to a different provider, only
this module needs to change.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

import anthropic

DEFAULT_MODEL = "claude-sonnet-4-5"  # Balance of reasoning quality and cost
DEFAULT_MAX_TOKENS = 1024


class ClaudeClient:
    """Minimal wrapper around anthropic.Anthropic for persona simulation."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL) -> None:
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Missing Anthropic API key. Provide it via the UI or set "
                "ANTHROPIC_API_KEY in your environment / Streamlit secrets."
            )
        self.client = anthropic.Anthropic(api_key=resolved_key)
        self.model = model

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def generate_persona_response(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Call Claude and return the parsed JSON payload.

        Raises a RuntimeError if the response cannot be parsed as JSON.
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ).strip()

        return _parse_json_payload(text)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json_payload(text: str) -> Dict[str, Any]:
    """Tolerant JSON parser.

    Some models occasionally wrap JSON in code fences or add a short preamble.
    We strip common wrappers before parsing and only raise if that still fails.
    """
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].lstrip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(candidate)
        if not match:
            raise RuntimeError(f"Could not find a JSON object in model output:\n{text}")
        return json.loads(match.group(0))
