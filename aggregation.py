"""Aggregate persona responses into summary metrics and a verdict.

Decision logic (tuneable):

- Claim tests: the decision dimension is `purchase_intent`.
- Name tests: the decision dimension is `appeal`.
- Trust dimension for a claim is `believability`; for a name it is `trust`.

Verdict thresholds:
- GO:     overall weighted score >= 5.5 AND no persona has trust <= 3
- ITERATE: overall weighted score 4.0 - 5.49, OR trust red flags that look fixable
- REJECT: overall < 4.0, OR a majority of personas flag trust issues
"""

from __future__ import annotations

from statistics import mean
from typing import Dict, List

import pandas as pd

from .schemas import Persona, PersonaResponse, TestRun

CLAIM_WEIGHTS = {
    "believability": 1.0,
    "relevance": 1.0,
    "differentiation": 0.8,
    "clarity": 0.8,
    "purchase_intent": 1.6,  # Decision dimension
}

NAME_WEIGHTS = {
    "memorability": 1.0,
    "appeal": 1.6,  # Decision dimension
    "category_fit": 1.0,
    "pronounceability": 0.6,
    "trust": 1.2,
}

DECISION_DIMENSION = {"claim": "purchase_intent", "name": "appeal"}
TRUST_DIMENSION = {"claim": "believability", "name": "trust"}

GO_THRESHOLD = 5.5
ITERATE_THRESHOLD = 4.0
TRUST_RED_FLAG_SCORE = 3


# ---------------------------------------------------------------------------
# Score maths
# ---------------------------------------------------------------------------


def weighted_overall(response: PersonaResponse) -> float:
    weights = CLAIM_WEIGHTS if response.test_type == "claim" else NAME_WEIGHTS
    total_weight = sum(weights.values())
    weighted = sum(response.scores[k] * w for k, w in weights.items())
    return round(weighted / total_weight, 2)


def scores_dataframe(run: TestRun, personas: List[Persona]) -> pd.DataFrame:
    """Wide-form dataframe: one row per persona, one column per dimension + overall."""
    persona_by_id = {p.id: p for p in personas}
    rows = []
    for response in run.responses:
        persona = persona_by_id.get(response.persona_id)
        row = {
            "persona_id": response.persona_id,
            "persona_label": persona.label if persona else response.persona_id,
            "persona_name": persona.name if persona else response.persona_id,
        }
        row.update(response.scores)
        row["overall"] = weighted_overall(response)
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def verbatim_dataframe(run: TestRun, personas: List[Persona]) -> pd.DataFrame:
    """Long-form dataframe with qualitative output per persona."""
    persona_by_id = {p.id: p for p in personas}
    rows = []
    for response in run.responses:
        persona = persona_by_id.get(response.persona_id)
        rows.append(
            {
                "persona_name": persona.name if persona else response.persona_id,
                "persona_label": persona.label if persona else response.persona_id,
                "verbatim": response.verbatim,
                "top_positive": response.top_positive,
                "top_concern": response.top_concern,
                "associations": ", ".join(response.three_word_association),
                "overall": weighted_overall(response),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def summarise(run: TestRun, personas: List[Persona]) -> Dict:
    if not run.responses:
        return {
            "verdict": "NO DATA",
            "reason": "No persona responses were collected.",
            "overall_score": None,
            "dimension_means": {},
            "segment_winners": [],
            "red_flags": [],
            "persona_count": 0,
        }

    test_type = run.input.test_type
    decision_dim = DECISION_DIMENSION[test_type]
    trust_dim = TRUST_DIMENSION[test_type]
    persona_by_id = {p.id: p for p in personas}

    overalls = [weighted_overall(r) for r in run.responses]
    overall_mean = round(mean(overalls), 2)

    # Dimension means across personas
    dimensions = list((CLAIM_WEIGHTS if test_type == "claim" else NAME_WEIGHTS).keys())
    dimension_means = {
        dim: round(mean(r.scores[dim] for r in run.responses), 2) for dim in dimensions
    }

    # Segment winners: personas with decision score >= 5.5
    segment_winners = []
    for r in run.responses:
        if r.scores[decision_dim] >= GO_THRESHOLD:
            persona = persona_by_id.get(r.persona_id)
            segment_winners.append(
                {
                    "persona": persona.label if persona else r.persona_id,
                    "name": persona.name if persona else r.persona_id,
                    "decision_score": r.scores[decision_dim],
                    "overall": weighted_overall(r),
                    "why": r.top_positive,
                }
            )

    # Red flags: low trust/believability
    red_flags = []
    for r in run.responses:
        if r.scores[trust_dim] <= TRUST_RED_FLAG_SCORE:
            persona = persona_by_id.get(r.persona_id)
            red_flags.append(
                {
                    "persona": persona.label if persona else r.persona_id,
                    "name": persona.name if persona else r.persona_id,
                    "trust_score": r.scores[trust_dim],
                    "concern": r.top_concern,
                }
            )

    # Verdict
    trust_flag_ratio = len(red_flags) / len(run.responses)
    if overall_mean >= GO_THRESHOLD and not red_flags:
        verdict = "GO"
        reason = (
            f"Overall weighted score {overall_mean} across {len(run.responses)} personas "
            f"with no trust red flags. Winning segments: "
            f"{', '.join(w['persona'] for w in segment_winners) or 'broad appeal'}."
        )
    elif overall_mean < ITERATE_THRESHOLD or trust_flag_ratio >= 0.5:
        verdict = "REJECT"
        reason = (
            f"Overall weighted score {overall_mean}. "
            f"Trust red flags in {len(red_flags)} of {len(run.responses)} personas. "
            "Consider reworking the core proposition rather than iterating."
        )
    else:
        verdict = "ITERATE"
        reason = (
            f"Overall weighted score {overall_mean}. "
            f"{len(segment_winners)} segment(s) respond well, "
            f"{len(red_flags)} show trust concerns. "
            "Refine the claim / name to address concerns before re-testing."
        )

    return {
        "verdict": verdict,
        "reason": reason,
        "overall_score": overall_mean,
        "dimension_means": dimension_means,
        "segment_winners": segment_winners,
        "red_flags": red_flags,
        "persona_count": len(run.responses),
    }
