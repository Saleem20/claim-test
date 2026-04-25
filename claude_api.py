"""
Claude API interface for synthetic persona claim testing.
Handles prompt construction, API calls and response parsing.
"""

import json
import anthropic


def build_prompt(persona: dict, category: str, product_name: str, claim: str) -> str:
    """Build the synthetic persona prompt for a single claim test."""
    return f"""You are a synthetic consumer persona for market research.

PERSONA: {persona['label']}, age {persona['age']}
PROFILE: {persona['profile']}

PRODUCT CATEGORY: {category}
PRODUCT NAME: "{product_name}"
CLAIM BEING TESTED: "{claim}"

Respond ONLY as valid JSON (no markdown, no extra text) using this exact structure:
{{
  "first_reaction": "One sentence gut reaction to this claim as this persona",
  "name_score": <integer 1-5, how well the product name lands for this persona>,
  "claim_score": <integer 1-5, how compelling this specific claim is for this persona>,
  "claim_feedback": "2-3 sentences on what works or does not work about this claim for this persona",
  "resonates": ["short phrase that lands well", "another phrase"],
  "concerns": ["short concern", "another concern"],
  "verdict": "Pass | Revise | Reject",
  "verdict_reason": "One sentence explaining the verdict"
}}"""


def test_claim(
    client: anthropic.Anthropic,
    persona: dict,
    category: str,
    product_name: str,
    claim: str,
    model: str = "claude-opus-4-5",
) -> dict:
    """
    Run a single claim test against one persona.

    Returns a dict with the parsed result, or an error dict on failure.
    """
    prompt = build_prompt(persona, category, product_name, claim)

    try:
        message = client.messages.create(
            model=model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip any accidental markdown code fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        result["persona_id"] = persona["id"]
        result["persona_label"] = persona["label"]
        result["claim"] = claim
        result["error"] = False
        return result

    except json.JSONDecodeError as e:
        return {
            "persona_id": persona["id"],
            "persona_label": persona["label"],
            "claim": claim,
            "error": True,
            "error_message": f"JSON parse error: {e}",
        }
    except anthropic.APIError as e:
        return {
            "persona_id": persona["id"],
            "persona_label": persona["label"],
            "claim": claim,
            "error": True,
            "error_message": f"API error: {e}",
        }


def avg_score(results: list[dict]) -> float:
    """Return the average combined score across a list of persona results."""
    valid = [r for r in results if not r.get("error")]
    if not valid:
        return 0.0
    scores = [(r.get("name_score", 0) + r.get("claim_score", 0)) / 2 for r in valid]
    return round(sum(scores) / len(scores), 2)


def verdict_counts(results: list[dict]) -> dict:
    """Count Pass / Revise / Reject verdicts across a list of results."""
    counts = {"Pass": 0, "Revise": 0, "Reject": 0}
    for r in results:
        if not r.get("error") and r.get("verdict") in counts:
            counts[r["verdict"]] += 1
    return counts
