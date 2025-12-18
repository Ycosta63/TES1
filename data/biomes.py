"""
Définition des biomes dark fantasy.

Chaque biome a :
- un identifiant interne
- un nom lisible
- une catégorie (marécage, désert cendré, ruine, forêt morte, etc.)
- une plage de bruit (altitude / "humidité" fictive) pour l'affectation
- un caractère ASCII pour rendu rapide style 90s
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, List


@dataclass(frozen=True)
class Biome:
    id: str
    name: str
    category: str
    noise_range: Tuple[float, float]
    ascii_char: str


BIOMES: List[Biome] = [
    Biome(
        id="corrupted_swamp",
        name="Marécage corrompu",
        category="marécage",
        noise_range=(-0.2, 0.3),
        ascii_char="≈",
    ),
    Biome(
        id="ashen_wastes",
        name="Désert cendré",
        category="désert_cendre",
        noise_range=(0.3, 0.65),
        ascii_char=".",
    ),
    Biome(
        id="dead_forest",
        name="Forêt morte",
        category="foret_morte",
        noise_range=(-0.6, -0.2),
        ascii_char="♣",
    ),
    Biome(
        id="ruined_lands",
        name="Terres en ruines",
        category="ruines",
        noise_range=(0.65, 1.0),
        ascii_char="▧",
    ),
]


def pick_biome_from_noise(value: float) -> Biome:
    """
    Sélectionne un biome en fonction de la valeur de bruit dans [-1, 1].
    """
    for biome in BIOMES:
        low, high = biome.noise_range
        if low <= value <= high:
            return biome

    # Fallback : clamp et prendre le plus proche
    clamped = max(-1.0, min(1.0, value))
    # tri par distance au centre de la plage
    sorted_biomes = sorted(
        BIOMES,
        key=lambda b: abs(((b.noise_range[0] + b.noise_range[1]) * 0.5) - clamped),
    )
    return sorted_biomes[0]


