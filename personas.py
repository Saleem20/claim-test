"""Persona loading utilities.

Supports two sources:
1. Default personas bundled with the app (data/default_personas.json).
2. User-uploaded JSON or CSV files with custom segment profiles.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Iterable, List, Union

from .schemas import Persona, PersonaFile

DEFAULT_PERSONA_PATH = Path(__file__).resolve().parent.parent / "data" / "default_personas.json"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_default_personas() -> List[Persona]:
    """Load the 10 bundled synthetic personas."""
    with open(DEFAULT_PERSONA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return PersonaFile.model_validate(raw).personas


def load_personas_from_json(payload: Union[str, bytes, dict]) -> List[Persona]:
    """Load personas from a JSON string, bytes or already-parsed dict."""
    if isinstance(payload, (str, bytes)):
        data = json.loads(payload)
    else:
        data = payload

    # Accept either a full PersonaFile or a bare list of personas.
    if isinstance(data, list):
        data = {"schema_version": "1.0", "personas": data}

    return PersonaFile.model_validate(data).personas


def load_personas_from_csv(payload: Union[str, bytes]) -> List[Persona]:
    """Load personas from a flattened CSV where list fields are pipe-separated.

    Expected columns:
        id,name,label,
        age,gender,life_stage,occupation,income_band,location_type,
        values,anxieties,motivations,
        oral_health,otc,wellness,
        media_habits,price_sensitivity,claim_skepticism,health_literacy,
        decision_heuristics
    """
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")

    reader = csv.DictReader(io.StringIO(payload))
    personas: List[Persona] = []

    for row in reader:
        persona_dict = {
            "id": row["id"].strip(),
            "name": row["name"].strip(),
            "label": row["label"].strip(),
            "demographics": {
                "age": int(row["age"]),
                "gender": row["gender"].strip(),
                "life_stage": row["life_stage"].strip(),
                "occupation": row["occupation"].strip(),
                "income_band": row["income_band"].strip(),
                "location_type": row["location_type"].strip(),
            },
            "psychographics": {
                "values": _split_pipe(row["values"]),
                "anxieties": _split_pipe(row["anxieties"]),
                "motivations": _split_pipe(row["motivations"]),
            },
            "category_engagement": {
                "oral_health": row["oral_health"].strip(),
                "otc": row["otc"].strip(),
                "wellness": row["wellness"].strip(),
            },
            "media_habits": row["media_habits"].strip(),
            "price_sensitivity": row["price_sensitivity"].strip(),
            "claim_skepticism": row["claim_skepticism"].strip(),
            "health_literacy": row["health_literacy"].strip(),
            "decision_heuristics": _split_pipe(row["decision_heuristics"]),
        }
        personas.append(Persona.model_validate(persona_dict))

    return personas


def _split_pipe(raw: str) -> List[str]:
    return [part.strip() for part in raw.split("|") if part.strip()]


def filter_by_ids(personas: Iterable[Persona], ids: Iterable[str]) -> List[Persona]:
    id_set = set(ids)
    return [p for p in personas if p.id in id_set]
