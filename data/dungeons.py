"""
Données de base pour les thèmes de donjon.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DungeonTheme:
    id: str
    name: str
    # Plus tard : tables de loot, types d'ennemis, pièges, décor, etc.
    dominant_biome_tags: List[str]
    ascii_floor: str
    ascii_wall: str


THEMES: List[DungeonTheme] = [
    DungeonTheme(
        id="necromancy",
        name="Nécromancie",
        dominant_biome_tags=["ruines", "foret_morte"],
        ascii_floor=".",
        ascii_wall="#",
    ),
    DungeonTheme(
        id="cult",
        name="Culte du vide",
        dominant_biome_tags=["marécage", "désert_cendre"],
        ascii_floor="-",
        ascii_wall="█",
    ),
    DungeonTheme(
        id="old_gods",
        name="Anciens dieux",
        dominant_biome_tags=["ruines", "marécage"],
        ascii_floor="·",
        ascii_wall="▓",
    ),
]


def get_theme_by_id(theme_id: str) -> DungeonTheme:
    for t in THEMES:
        if t.id == theme_id:
            return t
    # Fallback
    return THEMES[0]


