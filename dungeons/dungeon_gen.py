"""
Génération procédurale de donjons :
- grille de tuiles (salles + couloirs)
- thèmes (nécromancie, cultes, anciens dieux)
- difficulté influençant la taille / densité
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

from data.dungeons import DungeonTheme, get_theme_by_id


@dataclass
class DungeonTile:
    x: int
    y: int
    solid: bool = True


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> Tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def intersects(self, other: "Room") -> bool:
        return not (
            self.x + self.w <= other.x
            or other.x + other.w <= self.x
            or self.y + self.h <= other.y
            or other.y + other.h <= self.y
        )


@dataclass
class Dungeon:
    width: int
    height: int
    tiles: List[List[DungeonTile]]
    theme: DungeonTheme

    def render_ascii(self) -> str:
        """
        Rendu ASCII simple du donjon.
        """
        lines: List[str] = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                t = self.tiles[y][x]
                if t.solid:
                    row.append(self.theme.ascii_wall)
                else:
                    row.append(self.theme.ascii_floor)
            lines.append("".join(row))
        return "\n".join(lines)


class DungeonGenerator:
    """
    Génération de donjons style "rooms & corridors".
    """

    def __init__(self, seed: int) -> None:
        self.seed = seed

    def generate_dungeon(
        self,
        width: int,
        height: int,
        theme: str = "necromancy",
        difficulty: float = 0.5,
    ) -> Dungeon:
        rng = random.Random(self.seed ^ int(difficulty * 10_000))
        theme_data = get_theme_by_id(theme)

        tiles: List[List[DungeonTile]] = [
            [DungeonTile(x=x, y=y, solid=True) for x in range(width)]
            for y in range(height)
        ]

        rooms: List[Room] = []

        # Nombre de salles augmente avec la difficulté
        min_rooms = 6
        max_rooms = 18
        room_count = int(min_rooms + (max_rooms - min_rooms) * max(0.0, min(1.0, difficulty)))

        for _ in range(room_count):
            w = rng.randint(4, 10)
            h = rng.randint(4, 8)
            x = rng.randint(1, max(1, width - w - 2))
            y = rng.randint(1, max(1, height - h - 2))
            new_room = Room(x=x, y=y, w=w, h=h)

            # On évite la superposition brute pour un layout plus clair
            if any(new_room.intersects(r) for r in rooms):
                continue

            self._carve_room(tiles, new_room)

            if rooms:
                # Connecter la nouvelle salle avec la précédente
                prev_cx, prev_cy = rooms[-1].center
                cx, cy = new_room.center
                self._carve_corridor(tiles, prev_cx, prev_cy, cx, cy, rng)

            rooms.append(new_room)

        return Dungeon(width=width, height=height, tiles=tiles, theme=theme_data)

    # --- Carving -----------------------------------------------------

    def _carve_room(self, tiles: List[List[DungeonTile]], room: Room) -> None:
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                tiles[y][x].solid = False

    def _carve_corridor(
        self,
        tiles: List[List[DungeonTile]],
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        rng: random.Random,
    ) -> None:
        """
        Couloir en "L" avec inversion aléatoire (d'abord horizontal ou vertical).
        """
        if rng.random() < 0.5:
            self._carve_h_corridor(tiles, x1, x2, y1)
            self._carve_v_corridor(tiles, y1, y2, x2)
        else:
            self._carve_v_corridor(tiles, y1, y2, x1)
            self._carve_h_corridor(tiles, x1, x2, y2)

    def _carve_h_corridor(self, tiles: List[List[DungeonTile]], x1: int, x2: int, y: int) -> None:
        if x2 < x1:
            x1, x2 = x2, x1
        for x in range(x1, x2 + 1):
            tiles[y][x].solid = False

    def _carve_v_corridor(self, tiles: List[List[DungeonTile]], y1: int, y2: int, x: int) -> None:
        if y2 < y1:
            y1, y2 = y2, y1
        for y in range(y1, y2 + 1):
            tiles[y][x].solid = False


