"""Prompt templates for synthetic persona evaluation.

Two design principles:

1. The system prompt embeds the persona deeply so the model responds in
   first person with that worldview. This follows the "segment as infrastructure"
   idea: the persona does the structural work, Claude does the response.
2. The user prompt enforces a strict JSON output schema so downstream code
   can validate with Pydantic instead of parsing prose.
"""

from __future__ import annotations

import json
from typing import Optional

from .schemas import Persona


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


SYSTEM_PROMPT_TEMPLATE = """You are simulating a real consumer for product research.

You are NOT an AI assistant for this task. You are {name} ({label}), and you answer in first person, in your own voice, with the worldview below.

# Who you are

Age: {age}
Gender: {gender}
Life stage: {life_stage}
Occupation: {occupation}
Income band: {income_band}
Where you live: {location_type}

# What drives you

Values: {values}
Anxieties: {anxieties}
Motivations: {motivations}

# How you engage with these health and wellness categories

Oral Health: {oral_health}
OTC (over-the-counter medicines): {otc}
Wellness / supplements: {wellness}

# How you shop

Media habits: {media_habits}
Price sensitivity: {price_sensitivity}
Claim skepticism: {claim_skepticism}
Health literacy: {health_literacy}
Decision heuristics: {decision_heuristics}

# Rules for your response

- Respond as this specific person, not as an average consumer.
- Be honest. If a claim does not appeal to you, say so. If a name sounds wrong in your world, say so.
- Score strictly. A 7/7 means "I would actively advocate for this." A 4/7 means "fine, but not exciting." A 1/7 means "this is a dealbreaker."
- Avoid marketing language. Use the plain words you would actually use.
- Always return valid JSON matching the exact schema provided. No prose outside the JSON object. No code fences.
"""


# ---------------------------------------------------------------------------
# User prompt templates
# ---------------------------------------------------------------------------


CLAIM_PROMPT_TEMPLATE = """I am testing a product claim in the {category} category.

Claim: "{subject}"
{product_context}

Rate this claim on a 1-7 scale across five dimensions and give me a short, honest reaction in your own voice.

Return ONLY a JSON object with this exact structure, no extra keys, no code fences:

{{
  "scores": {{
    "believability": <1-7>,
    "relevance": <1-7>,
    "differentiation": <1-7>,
    "clarity": <1-7>,
    "purchase_intent": <1-7>
  }},
  "verbatim": "<2-3 sentences, first person, in your voice>",
  "top_positive": "<one sentence, what works best for you>",
  "top_concern": "<one sentence, what bothers you most>",
  "three_word_association": ["<word1>", "<word2>", "<word3>"]
}}"""


NAME_PROMPT_TEMPLATE = """I am testing a product / pack name in the {category} category.

Name: "{subject}"
{product_context}

Rate this name on a 1-7 scale across five dimensions and give me a short, honest reaction in your own voice.

Return ONLY a JSON object with this exact structure, no extra keys, no code fences:

{{
  "scores": {{
    "memorability": <1-7>,
    "appeal": <1-7>,
    "category_fit": <1-7>,
    "pronounceability": <1-7>,
    "trust": <1-7>
  }},
  "verbatim": "<2-3 sentences, first person, in your voice>",
  "top_positive": "<one sentence, what you like best>",
  "top_concern": "<one sentence, what could go wrong>",
  "three_word_association": ["<word1>", "<word2>", "<word3>"]
}}"""


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def build_system_prompt(persona: Persona) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=persona.name,
        label=persona.label,
        age=persona.demographics.age,
        gender=persona.demographics.gender,
        life_stage=persona.demographics.life_stage,
        occupation=persona.demographics.occupation,
        income_band=persona.demographics.income_band,
        location_type=persona.demographics.location_type,
        values=", ".join(persona.psychographics.values),
        anxieties=", ".join(persona.psychographics.anxieties),
        motivations=", ".join(persona.psychographics.motivations),
        oral_health=persona.category_engagement.oral_health,
        otc=persona.category_engagement.otc,
        wellness=persona.category_engagement.wellness,
        media_habits=persona.media_habits,
        price_sensitivity=persona.price_sensitivity,
        claim_skepticism=persona.claim_skepticism,
        health_literacy=persona.health_literacy,
        decision_heuristics=", ".join(persona.decision_heuristics),
    )


def build_user_prompt(
    test_type: str,
    category: str,
    subject: str,
    product_context: Optional[str] = None,
) -> str:
    context_block = f"Extra context: {product_context}" if product_context else ""
    if test_type == "claim":
        template = CLAIM_PROMPT_TEMPLATE
    elif test_type == "name":
        template = NAME_PROMPT_TEMPLATE
    else:
        raise ValueError(f"Unknown test_type: {test_type!r}")

    return template.format(
        category=category,
        subject=subject,
        product_context=context_block,
    )
