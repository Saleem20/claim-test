"""Pydantic schemas for structured persona responses and test artefacts.

Keeping schemas centralised lets us validate Claude's JSON output once
and treat it as typed data everywhere else.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, conint


# ---------------------------------------------------------------------------
# Persona schema
# ---------------------------------------------------------------------------


class Demographics(BaseModel):
    age: int
    gender: str
    life_stage: str
    occupation: str
    income_band: str
    location_type: str


class Psychographics(BaseModel):
    values: List[str]
    anxieties: List[str]
    motivations: List[str]


class CategoryEngagement(BaseModel):
    oral_health: str
    otc: str
    wellness: str


class Persona(BaseModel):
    id: str
    name: str
    label: str
    demographics: Demographics
    psychographics: Psychographics
    category_engagement: CategoryEngagement
    media_habits: str
    price_sensitivity: str
    claim_skepticism: str
    health_literacy: str
    decision_heuristics: List[str]


class PersonaFile(BaseModel):
    schema_version: str
    personas: List[Persona]


# ---------------------------------------------------------------------------
# Test input / output schemas
# ---------------------------------------------------------------------------


Category = Literal["Oral Health", "OTC", "Wellness"]
TestType = Literal["claim", "name"]


Score = conint(ge=1, le=7)


class ClaimScores(BaseModel):
    believability: Score
    relevance: Score
    differentiation: Score
    clarity: Score
    purchase_intent: Score


class NameScores(BaseModel):
    memorability: Score
    appeal: Score
    category_fit: Score
    pronounceability: Score
    trust: Score


class PersonaResponse(BaseModel):
    """Single persona's reaction to one claim or one name."""

    persona_id: str
    test_type: TestType
    scores: dict  # holds ClaimScores or NameScores fields
    verbatim: str = Field(..., description="Two to three sentence first-person reaction")
    top_positive: str
    top_concern: str
    three_word_association: List[str]


class TestInput(BaseModel):
    test_type: TestType
    category: Category
    subject: str = Field(..., description="The claim text or the pack/brand name being tested")
    product_context: Optional[str] = Field(
        default=None,
        description="Optional extra context shown to personas (e.g., product form, target user).",
    )


class TestRun(BaseModel):
    input: TestInput
    responses: List[PersonaResponse]
