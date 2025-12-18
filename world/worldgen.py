"""
Génération procédurale de la world map :
- grille de tuiles
- régions
- biomes via bruit 2D
- points d'intérêt (villes, donjons, ruines, sanctuaires)
- routes de base entre certains lieux
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from data.biomes import Biome, pick_biome_from_noise
from world.noise import ValueNoise2D


class PoiType(str, Enum):
    VILLE = "ville"
    DONJON = "donjon"
    RUINE = "ruine"
    SANCTUAIRE = "sanctuaire"


@dataclass
class Tile:
    x: int
    y: int
    biome: Biome
    height: float  # valeur directe de bruit / altitude relative


@dataclass
class Region:
    id: int
    tiles: List[Tile]
    center: Tuple[int, int]


@dataclass
class PointOfInterest:
    type: PoiType
    x: int
    y: int
    region_id: int


@dataclass
class Route:
    a: int  # index de POI
    b: int  # index de POI
    # Plus tard : chemin détaillé en tuiles pour pathfinding / dessin


@dataclass
class World:
    width: int
    height: int
    region_size: int
    tiles: List[List[Tile]]
    regions: List[Region]
    points_of_interest: List[PointOfInterest]
    routes: List[Route]
    seed: int

    def find_starting_location(self) -> Tuple[int, int]:
        """
        Heuristique simple :
        - si une ville existe, prendre la première
        - sinon, centre de la carte
        """
        for poi in self.points_of_interest:
            if poi.type == PoiType.VILLE:
                return poi.x, poi.y
        return self.width // 2, self.height // 2

    def find_first_dungeon(self) -> Optional[Tuple[Tuple[int, int], float]]:
        """
        Renvoie ((x, y), difficulté_normalisée) pour le premier donjon, ou None.
        Difficulté basée sur la distance au centre de la carte.
        """
        if not self.points_of_interest:
            return None

        cx = self.width / 2.0
        cy = self.height / 2.0
        max_dist = math.hypot(cx, cy)

        for poi in self.points_of_interest:
            if poi.type == PoiType.DONJON:
                dist = math.hypot(poi.x - cx, poi.y - cy)
                difficulty = dist / max_dist  # 0 (centre) -> 1 (bords)
                return (poi.x, poi.y), difficulty
        return None

    def render_ascii_view(self, center: Tuple[int, int], radius: int) -> str:
        """
        Rendu ASCII d'un carré centré sur 'center'.
        Les POI sont marqués par un caractère spécifique.
        """
        cx, cy = center
        min_x = max(0, cx - radius)
        max_x = min(self.width - 1, cx + radius)
        min_y = max(0, cy - radius)
        max_y = min(self.height - 1, cy + radius)

        # Indexation rapide des POI
        poi_map: Dict[Tuple[int, int], PoiType] = {}
        for poi in self.points_of_interest:
            poi_map[(poi.x, poi.y)] = poi.type

        lines: List[str] = []
        for y in range(min_y, max_y + 1):
            row_chars = []
            for x in range(min_x, max_x + 1):
                t = self.tiles[y][x]
                pos = (x, y)
                if pos in poi_map:
                    ttype = poi_map[pos]
                    if ttype == PoiType.VILLE:
                        row_chars.append("¤")
                    elif ttype == PoiType.DONJON:
                        row_chars.append("D")
                    elif ttype == PoiType.RUINE:
                        row_chars.append("r")
                    elif ttype == PoiType.SANCTUAIRE:
                        row_chars.append("†")
                else:
                    row_chars.append(t.biome.ascii_char)
            lines.append("".join(row_chars))
        return "\n".join(lines)


class WorldGenerator:
    """
    Générateur de world map déterministe.
    """

    def __init__(self, seed: int, width: int, height: int, region_size: int) -> None:
        self.seed = seed
        self.width = width
        self.height = height
        self.region_size = region_size

        self._rng = random.Random(seed)
        self._noise = ValueNoise2D(seed=seed, frequency=0.03, octaves=4)

    def generate_world(self) -> World:
        tiles = self._generate_tiles()
        regions = self._build_regions(tiles)
        pois = self._place_points_of_interest(regions)
        routes = self._connect_routes(pois)
        return World(
            width=self.width,
            height=self.height,
            region_size=self.region_size,
            tiles=tiles,
            regions=regions,
            points_of_interest=pois,
            routes=routes,
            seed=self.seed,
        )

    # --- Génération de tuiles / biomes -------------------------------------------------

    def _generate_tiles(self) -> List[List[Tile]]:
        tiles: List[List[Tile]] = []
        for y in range(self.height):
            row: List[Tile] = []
            for x in range(self.width):
                # On peut introduire de faux gradients "climatiques" pour plus de variété
                # Ex: plus aride vers l'est, plus marécageux vers l'ouest
                climate = (x / max(1, self.width - 1)) * 0.6 - 0.3  # [-0.3, 0.3]
                base = self._noise.sample(x, y)
                height = base + climate
                biome = pick_biome_from_noise(height)
                row.append(Tile(x=x, y=y, biome=biome, height=height))
            tiles.append(row)
        return tiles

    # --- Régions -----------------------------------------------------------------------

    def _build_regions(self, tiles: List[List[Tile]]) -> List[Region]:
        regions: List[Region] = []
        region_id = 0
        for ry in range(0, self.height, self.region_size):
            for rx in range(0, self.width, self.region_size):
                region_tiles: List[Tile] = []
                for y in range(ry, min(ry + self.region_size, self.height)):
                    for x in range(rx, min(rx + self.region_size, self.width)):
                        region_tiles.append(tiles[y][x])
                if not region_tiles:
                    continue
                cx = rx + min(self.region_size // 2, self.width - 1 - rx)
                cy = ry + min(self.region_size // 2, self.height - 1 - ry)
                regions.append(Region(id=region_id, tiles=region_tiles, center=(cx, cy)))
                region_id += 1
        return regions

    # --- Points d'intérêt --------------------------------------------------------------

    def _place_points_of_interest(self, regions: List[Region]) -> List[PointOfInterest]:
        pois: List[PointOfInterest] = []
        for region in regions:
            # Probabilités simples, ajustables facilement
            if self._rng.random() < 0.35:
                pois.append(self._make_poi_in_region(region, PoiType.VILLE))
            if self._rng.random() < 0.45:
                pois.append(self._make_poi_in_region(region, PoiType.DONJON))
            if self._rng.random() < 0.25:
                pois.append(self._make_poi_in_region(region, PoiType.RUINE))
            if self._rng.random() < 0.15:
                pois.append(self._make_poi_in_region(region, PoiType.SANCTUAIRE))
        return pois

    def _make_poi_in_region(self, region: Region, poi_type: PoiType) -> PointOfInterest:
        # Choix biaisé vers le centre de la région pour quelque chose de lisible
        cx, cy = region.center
        max_offset = max(1, self.region_size // 3)
        ox = self._rng.randint(-max_offset, max_offset)
        oy = self._rng.randint(-max_offset, max_offset)
        x = max(0, min(self.width - 1, cx + ox))
        y = max(0, min(self.height - 1, cy + oy))
        return PointOfInterest(type=poi_type, x=x, y=y, region_id=region.id)

    # --- Routes ------------------------------------------------------------------------

    def _connect_routes(self, pois: List[PointOfInterest]) -> List[Route]:
        """
        Connecte une partie des POI via une MST approximative + quelques liens aléatoires.
        Pour l'instant, on stocke seulement les couples (a,b), pas le chemin exact.
        """
        if len(pois) < 2:
            return []

        # On numérote les POI par index
        indexed = list(enumerate(pois))
        remaining = set(i for i, _ in indexed)
        connected: List[int] = []
        routes: List[Route] = []

        # Initialisation : premier POI
        first = next(iter(remaining))
        remaining.remove(first)
        connected.append(first)

        # Prim-like MST
        while remaining:
            best_pair = None
            best_dist = float("inf")
            for i in connected:
                pi = pois[i]
                for j in remaining:
                    pj = pois[j]
                    d = (pi.x - pj.x) ** 2 + (pi.y - pj.y) ** 2
                    if d < best_dist:
                        best_dist = d
                        best_pair = (i, j)
            if best_pair is None:
                break
            a, b = best_pair
            routes.append(Route(a=a, b=b))
            connected.append(b)
            remaining.remove(b)

        # Quelques routes supplémentaires aléatoires pour éviter la rigidité
        extra_count = max(1, len(pois) // 8)
        for _ in range(extra_count):
            a = self._rng.randrange(0, len(pois))
            b = self._rng.randrange(0, len(pois))
            if a != b:
                routes.append(Route(a=a, b=b))

        return routes


