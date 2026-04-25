"""
Synthetic persona definitions for the Bulk Claim Tester.
Each persona simulates a distinct consumer archetype grounded in
demographic, psychographic and behavioural characteristics.
"""

PERSONAS = [
    {
        "id": "young_urban",
        "label": "Young Urban Professional",
        "icon": "🏙️",
        "age": "25–34",
        "profile": (
            "City-based, degree-educated, renting, tech-savvy. Values convenience "
            "and status signals. Financially aspirational but cost-conscious. "
            "Highly influenced by social media and peer opinion. Responds well to "
            "brands that feel modern, credible and culturally aware."
        ),
    },
    {
        "id": "family_suburban",
        "label": "Suburban Family",
        "icon": "🏡",
        "age": "35–49",
        "profile": (
            "Homeowner in the suburbs, two or more children, dual income household. "
            "Values reliability, safety and value for money. Busy lifestyle means "
            "brand loyalty matters and decision fatigue is real. Risk-averse; "
            "trust is built through familiarity and clear benefit communication."
        ),
    },
    {
        "id": "empty_nester",
        "label": "Empty Nester",
        "icon": "🌿",
        "age": "50–64",
        "profile": (
            "Mortgage-free or nearly so, children have left home. Higher disposable "
            "income. Values quality over price and is sceptical of hype. Reads "
            "widely, prefers substance to flash. Responds to claims that are "
            "specific, honest and backed by evidence rather than aspirational language."
        ),
    },
    {
        "id": "budget_conscious",
        "label": "Budget-Conscious Shopper",
        "icon": "🧾",
        "age": "All ages",
        "profile": (
            "Price is the primary driver in every purchase decision. Compares options "
            "carefully, distrustful of premium claims without clear justification. "
            "Loyal to known brands when priced competitively. Practical and pragmatic; "
            "emotional or lifestyle-based messaging has little pull."
        ),
    },
    {
        "id": "health_wellness",
        "label": "Health & Wellness Seeker",
        "icon": "🧘",
        "age": "28–45",
        "profile": (
            "Prioritises wellbeing in all purchase decisions. Reads labels, researches "
            "ingredients and values transparency above all. Willing to pay a premium "
            "for natural, ethical or science-backed claims. Highly sceptical of "
            "greenwashing or unsubstantiated health assertions."
        ),
    },
    {
        "id": "senior_traditional",
        "label": "Senior Traditional",
        "icon": "☕",
        "age": "65+",
        "profile": (
            "Fixed or pension income, deeply established purchase habits, strong "
            "trust in familiar brands. Values simplicity, clarity of communication "
            "and personal service. Sceptical of novelty for its own sake. Claims "
            "need to be straightforward, reassuring and free of jargon."
        ),
    },
]

PERSONA_MAP = {p["id"]: p for p in PERSONAS}
