"""Synthetic Persona Lab — single-file Streamlit app.

Test product claims and pack names against synthetic consumers
across Oral Health, OTC and Wellness categories.

Everything (personas, prompts, engine, aggregation, UI) is in this one
file. Upload it to GitHub alongside requirements.txt and that's it.
"""

from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
from typing import Any, Callable, Dict, List, Optional

import anthropic
import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Persona data (10 archetypes spanning Oral Health, OTC and Wellness)
# ---------------------------------------------------------------------------


DEFAULT_PERSONAS: List[Dict[str, Any]] = [
    {
        "id": "health_first_mum",
        "name": "Sarah M.",
        "label": "Health-First Mum",
        "demographics": {
            "age": 38, "gender": "Female",
            "life_stage": "Married with school-age kids (7 and 10)",
            "occupation": "Primary school teacher",
            "income_band": "Middle-upper household income",
            "location_type": "Suburban, owner-occupier",
        },
        "psychographics": {
            "values": ["family wellbeing", "prevention over cure", "trusted science"],
            "anxieties": ["kids getting sick", "hidden ingredients", "sugar and additives"],
            "motivations": ["keep family healthy", "feel like a capable parent"],
        },
        "category_engagement": {
            "oral_health": "High - family routines, kids' toothpaste, flossing, whitening for herself",
            "otc": "High - kids' pain relief, cold and flu, allergy",
            "wellness": "Moderate-High - family multivitamins, immunity, magnesium for sleep",
        },
        "media_habits": "Instagram parenting accounts, school mums' WhatsApp groups, pharmacist chats",
        "price_sensitivity": "Moderate - will pay more if efficacy for kids is clear",
        "claim_skepticism": "Medium - needs substantiation for bold claims but responds to pediatric endorsement",
        "health_literacy": "Medium-High",
        "decision_heuristics": ["Is it safe for the kids?", "What does my pharmacist say?", "Is the ingredient list clean?"],
    },
    {
        "id": "budget_senior",
        "name": "Raj P.",
        "label": "Budget-Conscious Senior",
        "demographics": {
            "age": 68, "gender": "Male",
            "life_stage": "Widowed, retired, lives alone",
            "occupation": "Retired warehouse worker",
            "income_band": "Fixed pension, low",
            "location_type": "Small town, renter",
        },
        "psychographics": {
            "values": ["value for money", "tried-and-tested", "independence"],
            "anxieties": ["running out of medicine", "rising costs", "side effects"],
            "motivations": ["manage chronic aches", "stay self-reliant"],
        },
        "category_engagement": {
            "oral_health": "Low - dentures user, occasional denture cleaner and mouthwash",
            "otc": "High - daily pain relief, sleep, cold remedies, indigestion",
            "wellness": "Low - maybe fish oil if on special",
        },
        "media_habits": "Free-to-air TV ads, local newspaper, chemist leaflets",
        "price_sensitivity": "Very high - compares unit price, waits for half-price catalogue deals",
        "claim_skepticism": "High for new brands, low for heritage brands he has trusted for decades",
        "health_literacy": "Medium",
        "decision_heuristics": ["Is it on special?", "Have I used this brand before?", "What did the pharmacist say?"],
    },
    {
        "id": "wellness_maximalist",
        "name": "Chloe T.",
        "label": "Wellness Maximalist",
        "demographics": {
            "age": 31, "gender": "Female",
            "life_stage": "Single, no kids",
            "occupation": "Marketing manager",
            "income_band": "High personal income",
            "location_type": "Inner-city apartment renter",
        },
        "psychographics": {
            "values": ["optimisation", "aesthetics", "being ahead of the curve"],
            "anxieties": ["ageing visibly", "burnout", "missing out on the next best thing"],
            "motivations": ["peak performance", "glow from the inside", "signal status"],
        },
        "category_engagement": {
            "oral_health": "High - premium whitening, electric toothbrush, tongue scraper",
            "otc": "Moderate - stress, sleep, skin-related",
            "wellness": "Very High - adaptogens, collagen, greens powder, probiotics, nootropics",
        },
        "media_habits": "TikTok, Instagram, wellness podcasts, Substack newsletters",
        "price_sensitivity": "Low - premium expected, suspects cheap products of being ineffective",
        "claim_skepticism": "Medium - responds to science-y language but bored by old-world framing",
        "health_literacy": "High for wellness buzzwords, medium for medical",
        "decision_heuristics": ["Is this the new hero ingredient?", "Does the packaging look premium?", "Who is endorsing this online?"],
    },
    {
        "id": "skeptical_pragmatist",
        "name": "David L.",
        "label": "Skeptical Pragmatist",
        "demographics": {
            "age": 47, "gender": "Male",
            "life_stage": "Married with two teenagers",
            "occupation": "IT consultant",
            "income_band": "High household income",
            "location_type": "Suburban, owner-occupier",
        },
        "psychographics": {
            "values": ["evidence", "efficiency", "not being marketed to"],
            "anxieties": ["wasting money on snake oil", "declining mid-life health"],
            "motivations": ["fix a specific problem", "maintain performance"],
        },
        "category_engagement": {
            "oral_health": "Moderate - electric toothbrush, interdental, targeted toothpaste for sensitivity",
            "otc": "Moderate-High - headache, allergy, occasional sleep aid",
            "wellness": "Moderate - creatine, magnesium, vitamin D, only if evidence is strong",
        },
        "media_habits": "Reddit, Huberman-style podcasts, product reviews, clinical abstracts",
        "price_sensitivity": "Low if efficacy is proven, high if it smells like marketing",
        "claim_skepticism": "Very high - reads the fine print, notices weasel words",
        "health_literacy": "High",
        "decision_heuristics": ["Where is the clinical evidence?", "Is the dose in the study the same as in the product?", "Who funded this?"],
    },
    {
        "id": "genz_ingredient_hunter",
        "name": "Aisha K.",
        "label": "Gen Z Ingredient Hunter",
        "demographics": {
            "age": 23, "gender": "Female",
            "life_stage": "Student, shares flat with two friends",
            "occupation": "University student and part-time barista",
            "income_band": "Low disposable income",
            "location_type": "Inner-city share house",
        },
        "psychographics": {
            "values": ["transparency", "sustainability", "brand ethics"],
            "anxieties": ["greenwashing", "harmful additives", "big-brand trust"],
            "motivations": ["align purchases with values", "feel informed"],
        },
        "category_engagement": {
            "oral_health": "Moderate - natural toothpaste, no-SLS, charcoal curious",
            "otc": "Low - prefers natural remedies, only OTC as last resort",
            "wellness": "High - gummies for sleep, focus, beauty-from-within, sustainable packaging",
        },
        "media_habits": "TikTok, Instagram Reels, ingredient-scanning apps, YouTube explainers",
        "price_sensitivity": "High - but will pay more for brands whose values match",
        "claim_skepticism": "High for heritage brands, medium for indie brands she has discovered online",
        "health_literacy": "Medium - ingredient-focused more than medical",
        "decision_heuristics": ["Is it clean-label?", "Is the brand ethical?", "What does my favourite creator say?"],
    },
    {
        "id": "traditional_homemaker",
        "name": "Margaret R.",
        "label": "Traditional Homemaker",
        "demographics": {
            "age": 58, "gender": "Female",
            "life_stage": "Married, grown children, sometimes minding grandkids",
            "occupation": "Part-time retail assistant",
            "income_band": "Modest household income",
            "location_type": "Outer suburban, owner-occupier",
        },
        "psychographics": {
            "values": ["reliability", "tradition", "looking after the family"],
            "anxieties": ["change for change's sake", "trusting the wrong thing"],
            "motivations": ["keep doing what has always worked"],
        },
        "category_engagement": {
            "oral_health": "Moderate - brand-loyal toothpaste and mouthwash she has bought for 20 years",
            "otc": "High - household staples for colds, pain, stomach",
            "wellness": "Low-Moderate - basic multivitamin",
        },
        "media_habits": "Commercial TV, women's magazines, chemist aisle browsing",
        "price_sensitivity": "Moderate - loyal to brands on special",
        "claim_skepticism": "Low for heritage claims, high for trendy or scientific-sounding new claims",
        "health_literacy": "Medium-Low",
        "decision_heuristics": ["Have I always bought this?", "Does it feel trustworthy?", "What will my family think?"],
    },
    {
        "id": "chronic_manager",
        "name": "Tom H.",
        "label": "Chronic Condition Manager",
        "demographics": {
            "age": 62, "gender": "Male",
            "life_stage": "Married, adult kids moved out",
            "occupation": "Retired secondary school teacher",
            "income_band": "Moderate household income",
            "location_type": "Regional town, owner-occupier",
        },
        "psychographics": {
            "values": ["accuracy", "self-management", "dignity"],
            "anxieties": ["condition worsening", "contraindications", "being misled"],
            "motivations": ["stay ahead of his conditions", "protect quality of life"],
        },
        "category_engagement": {
            "oral_health": "High - gum-disease-aware, specialist toothpaste and rinse",
            "otc": "Very High - central to daily life alongside prescription meds",
            "wellness": "Moderate - magnesium, fish oil, CoQ10 if recommended",
        },
        "media_habits": "Health charity newsletters, GP and pharmacist, condition-specific forums",
        "price_sensitivity": "Low to moderate - efficacy matters more",
        "claim_skepticism": "Very high - abandons brands that feel misleading",
        "health_literacy": "High",
        "decision_heuristics": ["Is this safe with my other meds?", "Has my GP or pharmacist mentioned it?", "Are the claims specific?"],
    },
    {
        "id": "multicultural_family_shopper",
        "name": "Priya S.",
        "label": "Multicultural Family Shopper",
        "demographics": {
            "age": 42, "gender": "Female",
            "life_stage": "Married, 3 kids and mother-in-law at home",
            "occupation": "Accounts officer",
            "income_band": "Moderate-high household income",
            "location_type": "Outer suburban, owner-occupier",
        },
        "psychographics": {
            "values": ["family", "value", "shared wellbeing"],
            "anxieties": ["kids' and elders' health", "wasteful spending", "unfamiliar ingredients"],
            "motivations": ["care for all generations under one roof", "stretch the household budget"],
        },
        "category_engagement": {
            "oral_health": "High - family toothpaste, kids' flavours, sensitive range for mother-in-law",
            "otc": "Very High - bulk buys, multi-age needs",
            "wellness": "Moderate-High - kids' multivitamins, immunity, turmeric, joint support for elders",
        },
        "media_habits": "WhatsApp family groups, YouTube in first language, supermarket catalogues",
        "price_sensitivity": "High - value per use matters, bulk and multipacks win",
        "claim_skepticism": "Medium - trusts word of mouth from extended family more than ads",
        "health_literacy": "Medium-High",
        "decision_heuristics": ["Can the whole family use it?", "Is it better value than the pack I usually buy?", "What does my sister say?"],
    },
    {
        "id": "busy_executive",
        "name": "Marcus B.",
        "label": "Busy Executive",
        "demographics": {
            "age": 44, "gender": "Male",
            "life_stage": "Divorced, shared custody of one child",
            "occupation": "Senior finance executive",
            "income_band": "Very high personal income",
            "location_type": "Inner-city apartment owner",
        },
        "psychographics": {
            "values": ["performance", "convenience", "premium quality"],
            "anxieties": ["energy dips", "not keeping up", "looking run-down"],
            "motivations": ["perform at peak", "look the part", "save time"],
        },
        "category_engagement": {
            "oral_health": "High - premium whitening, professional-grade electric brush",
            "otc": "Moderate - targeted (jet lag, immunity, headache)",
            "wellness": "High - nootropics, sleep optimisation, recovery",
        },
        "media_habits": "Business podcasts, LinkedIn, curated newsletters, gym community",
        "price_sensitivity": "Very low - premium is a signal of quality",
        "claim_skepticism": "Medium - responds to specific performance claims and professional endorsements",
        "health_literacy": "Medium-High",
        "decision_heuristics": ["Will this give me an edge?", "Does it look premium?", "Can I decide in 30 seconds at the shelf?"],
    },
    {
        "id": "young_urban_renter",
        "name": "Lisa N.",
        "label": "Young Urban Renter",
        "demographics": {
            "age": 27, "gender": "Female",
            "life_stage": "Single, shares an apartment with a friend",
            "occupation": "Admin coordinator",
            "income_band": "Moderate personal income",
            "location_type": "Inner-city renter",
        },
        "psychographics": {
            "values": ["self-expression", "discovery", "social connection"],
            "anxieties": ["stress, skin, sleep", "being behind on trends"],
            "motivations": ["feel good and look good", "try new things"],
        },
        "category_engagement": {
            "oral_health": "Moderate - whitening interest, basic routine",
            "otc": "Low-Moderate - occasional cold and flu, period pain",
            "wellness": "High - entry-level gummies, sleep, mood, hair-skin-nails",
        },
        "media_habits": "TikTok, Instagram, friends' recommendations",
        "price_sensitivity": "Medium-High - tries cheaper versions of trending products first",
        "claim_skepticism": "Low-Medium - gives new brands a try, happy to switch",
        "health_literacy": "Medium",
        "decision_heuristics": ["Is this what everyone is talking about?", "Does it look good on my shelf?", "Can I try it without a big commitment?"],
    },
]


CATEGORIES = ["Oral Health", "OTC", "Wellness"]
VERDICT_COLOURS = {"GO": "#16a34a", "ITERATE": "#eab308", "REJECT": "#dc2626"}

CLAIM_DIMENSIONS = ["believability", "relevance", "differentiation", "clarity", "purchase_intent"]
NAME_DIMENSIONS = ["memorability", "appeal", "category_fit", "pronounceability", "trust"]

CLAIM_WEIGHTS = {"believability": 1.0, "relevance": 1.0, "differentiation": 0.8, "clarity": 0.8, "purchase_intent": 1.6}
NAME_WEIGHTS = {"memorability": 1.0, "appeal": 1.6, "category_fit": 1.0, "pronounceability": 0.6, "trust": 1.2}

DECISION_DIMENSION = {"claim": "purchase_intent", "name": "appeal"}
TRUST_DIMENSION = {"claim": "believability", "name": "trust"}

GO_THRESHOLD = 5.5
ITERATE_THRESHOLD = 4.0
TRUST_RED_FLAG_SCORE = 3
MAX_WORKERS = 8
DEFAULT_MODEL = "claude-sonnet-4-5"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt builders
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


def build_system_prompt(persona: Dict[str, Any]) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=persona["name"],
        label=persona["label"],
        age=persona["demographics"]["age"],
        gender=persona["demographics"]["gender"],
        life_stage=persona["demographics"]["life_stage"],
        occupation=persona["demographics"]["occupation"],
        income_band=persona["demographics"]["income_band"],
        location_type=persona["demographics"]["location_type"],
        values=", ".join(persona["psychographics"]["values"]),
        anxieties=", ".join(persona["psychographics"]["anxieties"]),
        motivations=", ".join(persona["psychographics"]["motivations"]),
        oral_health=persona["category_engagement"]["oral_health"],
        otc=persona["category_engagement"]["otc"],
        wellness=persona["category_engagement"]["wellness"],
        media_habits=persona["media_habits"],
        price_sensitivity=persona["price_sensitivity"],
        claim_skepticism=persona["claim_skepticism"],
        health_literacy=persona["health_literacy"],
        decision_heuristics=", ".join(persona["decision_heuristics"]),
    )


def build_user_prompt(test_type: str, category: str, subject: str, product_context: Optional[str]) -> str:
    template = CLAIM_PROMPT_TEMPLATE if test_type == "claim" else NAME_PROMPT_TEMPLATE
    context_block = f"Extra context: {product_context}" if product_context else ""
    return template.format(category=category, subject=subject, product_context=context_block)


# ---------------------------------------------------------------------------
# Claude client
# ---------------------------------------------------------------------------


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_payload(text: str) -> Dict[str, Any]:
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
            raise RuntimeError(f"Could not find JSON in model output:\n{text}")
        return json.loads(match.group(0))


def call_claude(client: "anthropic.Anthropic", system_prompt: str, user_prompt: str,
                model: str = DEFAULT_MODEL, max_tokens: int = 1024,
                temperature: float = 0.7) -> Dict[str, Any]:
    msg = client.messages.create(
        model=model, max_tokens=max_tokens, temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
    return parse_json_payload(text)


# ---------------------------------------------------------------------------
# Test orchestration
# ---------------------------------------------------------------------------


def validate_scores(payload: Dict[str, Any], test_type: str) -> None:
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("Missing 'scores' object")
    expected = set(CLAIM_DIMENSIONS) if test_type == "claim" else set(NAME_DIMENSIONS)
    missing = expected - scores.keys()
    if missing:
        raise ValueError(f"Missing dimensions: {sorted(missing)}")
    for dim in expected:
        v = scores[dim]
        if not isinstance(v, (int, float)) or not (1 <= v <= 7):
            raise ValueError(f"Score for {dim} must be 1-7, got {v!r}")
        scores[dim] = int(round(v))


def evaluate_persona(client: "anthropic.Anthropic", persona: Dict[str, Any],
                     test_type: str, category: str, subject: str,
                     product_context: Optional[str]) -> Dict[str, Any]:
    sys_prompt = build_system_prompt(persona)
    user_prompt = build_user_prompt(test_type, category, subject, product_context)
    payload = call_claude(client, sys_prompt, user_prompt)
    validate_scores(payload, test_type)
    return {
        "persona_id": persona["id"],
        "test_type": test_type,
        "scores": payload["scores"],
        "verbatim": (payload.get("verbatim") or "").strip(),
        "top_positive": (payload.get("top_positive") or "").strip(),
        "top_concern": (payload.get("top_concern") or "").strip(),
        "three_word_association": [str(w).strip() for w in payload.get("three_word_association", [])][:3],
    }


def run_test(personas: List[Dict[str, Any]], test_type: str, category: str,
             subject: str, product_context: Optional[str], client: "anthropic.Anthropic",
             progress_cb: Optional[Callable[[int, int], None]] = None) -> List[Dict[str, Any]]:
    responses: List[Dict[str, Any]] = []
    total = len(personas)
    done = 0
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, total)) as pool:
        futures = {
            pool.submit(evaluate_persona, client, p, test_type, category, subject, product_context): p
            for p in personas
        }
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                responses.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                logger.exception("Persona %s failed: %s", p["id"], exc)
            done += 1
            if progress_cb is not None:
                progress_cb(done, total)
    order = {p["id"]: i for i, p in enumerate(personas)}
    responses.sort(key=lambda r: order.get(r["persona_id"], 999))
    return responses


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def weighted_overall(response: Dict[str, Any]) -> float:
    weights = CLAIM_WEIGHTS if response["test_type"] == "claim" else NAME_WEIGHTS
    total = sum(weights.values())
    return round(sum(response["scores"][k] * w for k, w in weights.items()) / total, 2)


def scores_dataframe(responses: List[Dict[str, Any]], personas: List[Dict[str, Any]]) -> pd.DataFrame:
    persona_by_id = {p["id"]: p for p in personas}
    rows = []
    for r in responses:
        p = persona_by_id.get(r["persona_id"], {})
        row = {
            "persona_id": r["persona_id"],
            "persona_name": p.get("name", r["persona_id"]),
            "persona_label": p.get("label", ""),
        }
        row.update(r["scores"])
        row["overall"] = weighted_overall(r)
        rows.append(row)
    return pd.DataFrame(rows)


def verbatim_dataframe(responses: List[Dict[str, Any]], personas: List[Dict[str, Any]]) -> pd.DataFrame:
    persona_by_id = {p["id"]: p for p in personas}
    rows = []
    for r in responses:
        p = persona_by_id.get(r["persona_id"], {})
        rows.append({
            "persona_name": p.get("name", r["persona_id"]),
            "persona_label": p.get("label", ""),
            "verbatim": r["verbatim"],
            "top_positive": r["top_positive"],
            "top_concern": r["top_concern"],
            "associations": ", ".join(r["three_word_association"]),
            "overall": weighted_overall(r),
        })
    return pd.DataFrame(rows)


def summarise(responses: List[Dict[str, Any]], personas: List[Dict[str, Any]],
              test_type: str) -> Dict[str, Any]:
    if not responses:
        return {"verdict": "NO DATA", "reason": "No persona responses.",
                "overall_score": None, "dimension_means": {},
                "segment_winners": [], "red_flags": [], "persona_count": 0}

    decision_dim = DECISION_DIMENSION[test_type]
    trust_dim = TRUST_DIMENSION[test_type]
    persona_by_id = {p["id"]: p for p in personas}

    overalls = [weighted_overall(r) for r in responses]
    overall_mean = round(mean(overalls), 2)

    dims = CLAIM_DIMENSIONS if test_type == "claim" else NAME_DIMENSIONS
    dim_means = {d: round(mean(r["scores"][d] for r in responses), 2) for d in dims}

    winners = []
    for r in responses:
        if r["scores"][decision_dim] >= GO_THRESHOLD:
            p = persona_by_id.get(r["persona_id"], {})
            winners.append({
                "persona": p.get("label", r["persona_id"]),
                "name": p.get("name", r["persona_id"]),
                "decision_score": r["scores"][decision_dim],
                "overall": weighted_overall(r),
                "why": r["top_positive"],
            })

    red_flags = []
    for r in responses:
        if r["scores"][trust_dim] <= TRUST_RED_FLAG_SCORE:
            p = persona_by_id.get(r["persona_id"], {})
            red_flags.append({
                "persona": p.get("label", r["persona_id"]),
                "name": p.get("name", r["persona_id"]),
                "trust_score": r["scores"][trust_dim],
                "concern": r["top_concern"],
            })

    flag_ratio = len(red_flags) / len(responses)
    if overall_mean >= GO_THRESHOLD and not red_flags:
        verdict = "GO"
        reason = (f"Overall weighted score {overall_mean} across {len(responses)} personas "
                  f"with no trust red flags. Winning segments: "
                  f"{', '.join(w['persona'] for w in winners) or 'broad appeal'}.")
    elif overall_mean < ITERATE_THRESHOLD or flag_ratio >= 0.5:
        verdict = "REJECT"
        reason = (f"Overall weighted score {overall_mean}. "
                  f"Trust red flags in {len(red_flags)} of {len(responses)} personas. "
                  "Consider reworking the proposition rather than iterating.")
    else:
        verdict = "ITERATE"
        reason = (f"Overall weighted score {overall_mean}. "
                  f"{len(winners)} segment(s) respond well, "
                  f"{len(red_flags)} show trust concerns. "
                  "Refine the claim / name to address concerns before re-testing.")

    return {
        "verdict": verdict, "reason": reason,
        "overall_score": overall_mean, "dimension_means": dim_means,
        "segment_winners": winners, "red_flags": red_flags,
        "persona_count": len(responses),
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------


st.set_page_config(
    page_title="Synthetic Persona Lab",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_session_personas() -> List[Dict[str, Any]]:
    if "personas" not in st.session_state:
        st.session_state.personas = list(DEFAULT_PERSONAS)
    return st.session_state.personas


def sidebar_controls() -> List[Dict[str, Any]]:
    st.sidebar.title("Setup")

    stored = ""
    try:
        stored = st.secrets.get("ANTHROPIC_API_KEY", "")  # type: ignore[attr-defined]
    except Exception:
        stored = ""

    api_key = st.sidebar.text_input(
        "Anthropic API key", type="password", value=stored,
        help="Used only for this session. Not stored by the app.",
    )
    st.session_state["api_key"] = api_key

    st.sidebar.divider()
    st.sidebar.subheader("Personas")

    source = st.sidebar.radio(
        "Source", options=["Use default 10 personas", "Upload custom personas (JSON)"], index=0,
    )

    if source == "Upload custom personas (JSON)":
        up = st.sidebar.file_uploader("Upload JSON", type=["json"])
        if up is not None:
            try:
                raw = json.loads(up.read())
                personas = raw["personas"] if isinstance(raw, dict) and "personas" in raw else raw
                # Light validation
                for p in personas:
                    for key in ("id", "name", "label", "demographics", "psychographics",
                                "category_engagement", "media_habits", "price_sensitivity",
                                "claim_skepticism", "health_literacy", "decision_heuristics"):
                        if key not in p:
                            raise ValueError(f"Persona missing key: {key}")
                st.session_state.personas = personas
                st.sidebar.success(f"Loaded {len(personas)} personas.")
            except Exception as exc:  # noqa: BLE001
                st.sidebar.error(f"Could not load file: {exc}")

    personas = get_session_personas()
    options = {f"{p['name']} - {p['label']}": p["id"] for p in personas}
    selected = st.sidebar.multiselect(
        "Personas to include", options=list(options.keys()), default=list(options.keys()),
    )
    selected_ids = {options[s] for s in selected}
    return [p for p in personas if p["id"] in selected_ids]


def test_input_panel() -> Optional[Dict[str, Any]]:
    st.title("Synthetic Persona Lab")
    st.caption(
        "A virtual pre-test for claims and pack names across Oral Health, OTC and Wellness. "
        "Use to filter weak options before primary research, not to replace it."
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        ttype_label = st.radio("Test type", options=["Claim test", "Pack name test"], horizontal=True)
    with c2:
        category = st.selectbox("Category", options=CATEGORIES, index=0)

    test_type = "claim" if ttype_label == "Claim test" else "name"

    subject = st.text_area(
        "Claim or name to test",
        placeholder="e.g. 'Clinically proven to whiten teeth 3 shades in 7 days' or 'ZenRoot Calm Gummies'",
        height=80,
    )

    with st.expander("Optional product context", expanded=False):
        ctx = st.text_area("Product context",
                           placeholder="e.g. 'Toothpaste for sensitive teeth, 100g tube, RRP $8.99, pharmacy channel'",
                           height=80)

    if not subject.strip():
        return None

    return {
        "test_type": test_type, "category": category,
        "subject": subject.strip(), "product_context": (ctx.strip() or None),
    }


def render_results(responses: List[Dict[str, Any]], personas: List[Dict[str, Any]],
                   test_input: Dict[str, Any]) -> None:
    summary = summarise(responses, personas, test_input["test_type"])
    scores_df = scores_dataframe(responses, personas)
    verbatim_df = verbatim_dataframe(responses, personas)

    st.divider()
    st.header("Results")

    colour = VERDICT_COLOURS.get(summary["verdict"], "#6b7280")
    st.markdown(
        f"""<div style="padding:16px;border-radius:8px;background:{colour};color:white;">
            <div style="font-size:14px;opacity:0.85;">Verdict</div>
            <div style="font-size:32px;font-weight:700;">{summary['verdict']}</div>
            <div style="font-size:14px;">{summary['reason']}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Overall score", summary["overall_score"])
    m2.metric("Personas tested", summary["persona_count"])
    m3.metric("Segment winners", len(summary["segment_winners"]))
    m4.metric("Red flags", len(summary["red_flags"]))

    st.subheader("Dimension averages")
    dim_df = pd.DataFrame({"dimension": list(summary["dimension_means"].keys()),
                           "mean_score": list(summary["dimension_means"].values())})
    st.bar_chart(dim_df.set_index("dimension"))

    st.subheader("Scores by persona")
    dim_cols = [c for c in scores_df.columns if c not in {"persona_id", "persona_name", "persona_label", "overall"}]
    display_df = scores_df.set_index("persona_name")[dim_cols + ["overall"]]
    try:
        styled = display_df.style.background_gradient(cmap="RdYlGn", vmin=1, vmax=7, subset=dim_cols)
        st.dataframe(styled, use_container_width=True)
    except Exception:
        st.dataframe(display_df, use_container_width=True)

    if summary["segment_winners"]:
        st.subheader("Segment winners")
        for w in summary["segment_winners"]:
            st.markdown(f"- **{w['persona']}** (score {w['decision_score']}/7) - _{w['why']}_")
    else:
        st.info("No segment winners - no persona scored the decision dimension >= 5.5.")

    if summary["red_flags"]:
        st.subheader("Red flags")
        for r in summary["red_flags"]:
            st.markdown(f"- **{r['persona']}** (trust {r['trust_score']}/7) - _{r['concern']}_")

    st.subheader("Persona verbatims")
    for _, row in verbatim_df.iterrows():
        with st.expander(f"{row['persona_name']} - {row['persona_label']}  (overall {row['overall']}/7)"):
            st.markdown(f"> {row['verbatim']}")
            st.markdown(f"**Top positive:** {row['top_positive']}")
            st.markdown(f"**Top concern:** {row['top_concern']}")
            st.markdown(f"**Associations:** {row['associations']}")

    st.subheader("Export")
    scores_csv = scores_df.to_csv(index=False).encode("utf-8")
    verbatim_csv = verbatim_df.to_csv(index=False).encode("utf-8")
    full_json = json.dumps({"input": test_input, "summary": summary, "responses": responses}, indent=2).encode("utf-8")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Download scores (CSV)", scores_csv, file_name="scores.csv", mime="text/csv")
    c2.download_button("Download verbatims (CSV)", verbatim_csv, file_name="verbatims.csv", mime="text/csv")
    c3.download_button("Download full run (JSON)", full_json, file_name="run.json", mime="application/json")


def main() -> None:
    selected_personas = sidebar_controls()
    test_input = test_input_panel()

    if test_input is None:
        st.info("Enter a claim or a pack name above to begin.")
        return

    api_key = st.session_state.get("api_key") or os.getenv("ANTHROPIC_API_KEY", "")
    can_run = bool(api_key) and bool(selected_personas)

    if st.button("Run test across personas", type="primary", disabled=not can_run, use_container_width=True):
        if not api_key:
            st.error("Enter an Anthropic API key in the sidebar.")
            return
        if not selected_personas:
            st.error("Select at least one persona in the sidebar.")
            return

        try:
            client = anthropic.Anthropic(api_key=api_key)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not initialise Claude client: {exc}")
            return

        progress_bar = st.progress(0.0, text="Running personas...")

        def _on_progress(done: int, total: int) -> None:
            progress_bar.progress(done / total, text=f"Completed {done} of {total} personas")

        with st.spinner("Querying personas..."):
            responses = run_test(
                personas=selected_personas,
                test_type=test_input["test_type"],
                category=test_input["category"],
                subject=test_input["subject"],
                product_context=test_input["product_context"],
                client=client,
                progress_cb=_on_progress,
            )

        progress_bar.empty()

        if not responses:
            st.error("No personas returned a valid response. Check your API key and try again.")
            return

        st.session_state.last_results = (responses, selected_personas, test_input)

    if "last_results" in st.session_state:
        responses, personas, test_input = st.session_state.last_results
        render_results(responses, personas, test_input)


if __name__ == "__main__":
    main()
