"""Orchestrates a full synthetic-persona test run.

Given a test input and a list of personas, this module fans out API calls
in parallel, validates each response against the schema and returns a
TestRun object.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional

from .claude_client import ClaudeClient
from .prompts import build_system_prompt, build_user_prompt
from .schemas import Persona, PersonaResponse, TestInput, TestRun

logger = logging.getLogger(__name__)

MAX_WORKERS = 8  # Concurrent API calls


def run_test(
    test_input: TestInput,
    personas: List[Persona],
    client: ClaudeClient,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> TestRun:
    """Run a full test across the chosen personas."""
    responses: List[PersonaResponse] = []
    total = len(personas)
    completed = 0

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, total)) as pool:
        future_to_persona = {
            pool.submit(_evaluate_single_persona, test_input, persona, client): persona
            for persona in personas
        }

        for future in as_completed(future_to_persona):
            persona = future_to_persona[future]
            try:
                response = future.result()
                responses.append(response)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Persona %s failed: %s", persona.id, exc)
            completed += 1
            if progress_callback is not None:
                progress_callback(completed, total)

    # Keep output order stable even though calls finish out of order.
    persona_order = {p.id: i for i, p in enumerate(personas)}
    responses.sort(key=lambda r: persona_order.get(r.persona_id, 999))

    return TestRun(input=test_input, responses=responses)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _evaluate_single_persona(
    test_input: TestInput,
    persona: Persona,
    client: ClaudeClient,
) -> PersonaResponse:
    system_prompt = build_system_prompt(persona)
    user_prompt = build_user_prompt(
        test_type=test_input.test_type,
        category=test_input.category,
        subject=test_input.subject,
        product_context=test_input.product_context,
    )
    payload = client.generate_persona_response(system_prompt, user_prompt)
    _validate_scores(payload, test_input.test_type)

    return PersonaResponse(
        persona_id=persona.id,
        test_type=test_input.test_type,
        scores=payload["scores"],
        verbatim=payload.get("verbatim", "").strip(),
        top_positive=payload.get("top_positive", "").strip(),
        top_concern=payload.get("top_concern", "").strip(),
        three_word_association=[
            str(w).strip() for w in payload.get("three_word_association", [])
        ][:3],
    )


CLAIM_DIMENSIONS = {
    "believability",
    "relevance",
    "differentiation",
    "clarity",
    "purchase_intent",
}
NAME_DIMENSIONS = {
    "memorability",
    "appeal",
    "category_fit",
    "pronounceability",
    "trust",
}


def _validate_scores(payload: dict, test_type: str) -> None:
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("Missing 'scores' object in persona response")

    expected = CLAIM_DIMENSIONS if test_type == "claim" else NAME_DIMENSIONS
    missing = expected - scores.keys()
    if missing:
        raise ValueError(f"Response missing required score dimensions: {sorted(missing)}")

    for dim in expected:
        value = scores[dim]
        if not isinstance(value, (int, float)) or not (1 <= value <= 7):
            raise ValueError(f"Score for '{dim}' must be an integer 1-7, got {value!r}")
        scores[dim] = int(round(value))
