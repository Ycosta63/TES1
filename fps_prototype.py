"""
TES1: Arena - Monde Ouvert RPG Rétro avec Ursina Engine.

Fonctionnalités :
- Terrain avec relief procédural (collines, vallées)
- Villages avec bâtiments variés (maisons, tavernes, tours, temples)
- PNJ interactifs avec dialogues et comportements
- Système de quêtes simple
- Menu de personnalisation du personnage
- Combat FPS avec armes variées
- Cycle jour/nuit basique

Contrôles :
- ZQSD : Déplacement
- Souris : Regarder
- Clic gauche : Attaquer
- E : Interagir avec PNJ
- 1/2/3 : Changer d'arme
- ESC : Menu pause

Lancement : python fps_prototype.py
"""

from __future__ import annotations

import random
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from ursina import (
    Ursina,
    Entity,
    color,
    Vec3,
    Vec2,
    camera,
    mouse,
    Text,
    raycast,
    time,
    held_keys,
    destroy,
    application,
    Button,
    InputField,
)


# =============================================================================
# CONFIGURATION GLOBALE
# =============================================================================

WORLD_SIZE = 80
CELL_SIZE = 2.0
PLAYER_SPEED = 6.0
MOUSE_SENSITIVITY = 40.0

# Classes de personnage
CHARACTER_CLASSES = {
    "Guerrier": {
        "description": "Expert au combat rapproché",
        "health": 120, "speed": 5.0, "damage_bonus": 1.2, "mana": 20,
        "color": (0.8, 0.2, 0.2), "starting_weapon": "sword",
    },
    "Mage": {
        "description": "Maître des arcanes",
        "health": 70, "speed": 5.5, "damage_bonus": 1.0, "mana": 100,
        "color": (0.2, 0.2, 0.8), "starting_weapon": "staff",
    },
    "Voleur": {
        "description": "Rapide et furtif",
        "health": 85, "speed": 7.5, "damage_bonus": 1.5, "mana": 40,
        "color": (0.2, 0.6, 0.2), "starting_weapon": "dagger",
    },
    "Paladin": {
        "description": "Guerrier sacré",
        "health": 110, "speed": 4.5, "damage_bonus": 1.3, "mana": 60,
        "color": (0.9, 0.8, 0.2), "starting_weapon": "sword",
    },
}

WEAPONS = {
    "dagger": {"name": "Dague", "damage": 15, "range": 3, "speed": 0.2},
    "sword": {"name": "Épée", "damage": 28, "range": 5, "speed": 0.4},
    "axe": {"name": "Hache", "damage": 50, "range": 4, "speed": 0.7},
    "staff": {"name": "Bâton", "damage": 35, "range": 8, "speed": 0.5},
}

PLAYER_COLORS = [
    ("Rouge", (1.0, 0.2, 0.2)), ("Bleu", (0.2, 0.4, 1.0)),
    ("Vert", (0.2, 0.8, 0.2)), ("Or", (0.9, 0.7, 0.1)),
    ("Violet", (0.6, 0.2, 0.8)), ("Cyan", (0.2, 0.8, 0.8)),
    ("Orange", (1.0, 0.5, 0.1)), ("Argent", (0.8, 0.8, 0.85)),
]

# Types de PNJ
NPC_TYPES = {
    "villager": {
        "name": "Villageois",
        "color": (0.6, 0.5, 0.4),
        "dialogues": [
            "Bienvenue dans notre village, voyageur!",
            "Les temps sont durs depuis l'arrivée des monstres...",
            "Avez-vous vu le forgeron? Il a du bon équipement.",
            "Faites attention aux gobelins dans la forêt!",
        ],
    },
    "merchant": {
        "name": "Marchand",
        "color": (0.7, 0.5, 0.2),
        "dialogues": [
            "Bienvenue! Regardez mes marchandises!",
            "J'ai les meilleurs prix de la région!",
            "Potions, armes, armures... J'ai tout ce qu'il vous faut!",
            "Revenez quand vous aurez plus d'or!",
        ],
    },
    "guard": {
        "name": "Garde",
        "color": (0.4, 0.4, 0.5),
        "dialogues": [
            "Halte! Qui va là? Ah, un aventurier...",
            "Gardez vos armes rangées dans le village.",
            "Des créatures rôdent au nord, soyez prudent.",
            "Je protège ce village depuis 20 ans.",
        ],
    },
    "blacksmith": {
        "name": "Forgeron",
        "color": (0.5, 0.3, 0.2),
        "dialogues": [
            "Ah! Un client! Que puis-je forger pour vous?",
            "Mon acier est le meilleur de la région!",
            "Cette épée? Elle a tué un dragon, dit-on...",
            "Le minerai devient rare ces temps-ci.",
        ],
    },
    "innkeeper": {
        "name": "Tavernier",
        "color": (0.6, 0.4, 0.3),
        "dialogues": [
            "Bienvenue à l'Auberge du Dragon d'Or!",
            "Une chambre? 10 pièces d'or la nuit.",
            "Notre hydromel est réputé dans tout le royaume!",
            "J'ai entendu des rumeurs sur un trésor au nord...",
        ],
    },
    "elder": {
        "name": "Ancien",
        "color": (0.7, 0.7, 0.7),
        "dialogues": [
            "Ah, jeune aventurier... Écoutez les paroles d'un vieil homme.",
            "Jadis, ce royaume était prospère...",
            "La tour noire au nord cache de terribles secrets.",
            "Puissent les anciens dieux vous protéger.",
        ],
    },
}

# Types d'ennemis
ENEMY_TYPES = {
    "goblin": {"name": "Gobelin", "health": 25, "damage": 8, "speed": 3.0, "color": (0.3, 0.5, 0.2)},
    "orc": {"name": "Orc", "health": 50, "damage": 15, "speed": 2.0, "color": (0.4, 0.3, 0.2)},
    "skeleton": {"name": "Squelette", "health": 30, "damage": 12, "speed": 2.5, "color": (0.9, 0.9, 0.85)},
    "troll": {"name": "Troll", "health": 80, "damage": 25, "speed": 1.5, "color": (0.5, 0.4, 0.3)},
    "wolf": {"name": "Loup", "health": 20, "damage": 10, "speed": 4.5, "color": (0.4, 0.4, 0.4)},
}


# =============================================================================
# GÉNÉRATION DE BRUIT POUR LE TERRAIN
# =============================================================================

class NoiseGenerator:
    """Générateur de bruit pour le terrain."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.permutation = list(range(256))
        self.rng.shuffle(self.permutation)
        self.permutation *= 2

    def _fade(self, t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def _grad(self, hash_val: int, x: float, y: float) -> float:
        h = hash_val & 3
        u = x if h < 2 else y
        v = y if h < 2 else x
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

    def noise2d(self, x: float, y: float) -> float:
        """Génère du bruit 2D de type Perlin."""
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255
        x -= math.floor(x)
        y -= math.floor(y)

        u = self._fade(x)
        v = self._fade(y)

        A = self.permutation[X] + Y
        B = self.permutation[X + 1] + Y

        return self._lerp(
            self._lerp(self._grad(self.permutation[A], x, y),
                      self._grad(self.permutation[B], x - 1, y), u),
            self._lerp(self._grad(self.permutation[A + 1], x, y - 1),
                      self._grad(self.permutation[B + 1], x - 1, y - 1), u),
            v
        )

    def fbm(self, x: float, y: float, octaves: int = 4, persistence: float = 0.5) -> float:
        """Fractional Brownian Motion pour un terrain plus naturel."""
        total = 0.0
        frequency = 1.0
        amplitude = 1.0
        max_value = 0.0

        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2.0

        return total / max_value


# =============================================================================
# SYSTÈME DE MENU
# =============================================================================

class MainMenu:
    """Menu principal du jeu."""

    def __init__(self, on_start_game):
        self.on_start_game = on_start_game
        self.elements = []
        self._build()

    def _build(self):
        self.bg = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 220), scale=2, z=1)
        self.elements.append(self.bg)

        self.title = Text("TES1: ARENA", parent=camera.ui, position=(0, 0.38),
                         origin=(0, 0), scale=4.5, color=color.gold)
        self.elements.append(self.title)

        self.subtitle = Text("Monde Ouvert - Aventure Épique", parent=camera.ui,
                            position=(0, 0.28), origin=(0, 0), scale=1.5, color=color.light_gray)
        self.elements.append(self.subtitle)

        self.btn_play = Button(text="Nouvelle Aventure", parent=camera.ui,
                              position=(0, 0.05), scale=(0.45, 0.09),
                              color=color.dark_gray, on_click=self._start)
        self.elements.append(self.btn_play)

        self.btn_quit = Button(text="Quitter", parent=camera.ui,
                              position=(0, -0.12), scale=(0.45, 0.09),
                              color=color.dark_gray, highlight_color=color.red,
                              on_click=application.quit)
        self.elements.append(self.btn_quit)

        self.info = Text("ZQSD: Déplacer | Souris: Regarder | E: Parler | Clic: Attaquer",
                        parent=camera.ui, position=(0, -0.4), origin=(0, 0),
                        scale=0.9, color=color.gray)
        self.elements.append(self.info)

    def _start(self):
        self.hide()
        self.on_start_game()

    def hide(self):
        for e in self.elements:
            e.enabled = False

    def show(self):
        for e in self.elements:
            e.enabled = True

    def destroy(self):
        for e in self.elements:
            destroy(e)


class CharacterCreation:
    """Menu de création de personnage."""

    def __init__(self, on_confirm, on_back):
        self.on_confirm = on_confirm
        self.on_back = on_back
        self.elements = []
        self.selected_class = "Guerrier"
        self.selected_weapon = "sword"
        self.selected_color_idx = 0
        self._build()

    def _build(self):
        self.bg = Entity(parent=camera.ui, model='quad', color=color.rgba(15, 15, 25, 240), scale=2, z=1)
        self.elements.append(self.bg)

        self.title = Text("CRÉATION DU HÉROS", parent=camera.ui, position=(0, 0.42),
                         origin=(0, 0), scale=2.5, color=color.gold)
        self.elements.append(self.title)

        # Nom
        self.name_label = Text("Nom:", parent=camera.ui, position=(-0.45, 0.3),
                              origin=(-0.5, 0), scale=1.2, color=color.white)
        self.elements.append(self.name_label)
        self.name_input = InputField(default_value="Héros", parent=camera.ui,
                                    position=(0.1, 0.3), scale=(0.35, 0.05))
        self.elements.append(self.name_input)

        # Classes
        self.class_label = Text("Classe:", parent=camera.ui, position=(-0.45, 0.18),
                               origin=(-0.5, 0), scale=1.2, color=color.white)
        self.elements.append(self.class_label)

        self.class_buttons = []
        for i, cname in enumerate(CHARACTER_CLASSES.keys()):
            btn = Button(text=cname[:4], parent=camera.ui,
                        position=(-0.25 + i * 0.18, 0.1), scale=(0.14, 0.055),
                        color=color.azure if i == 0 else color.dark_gray,
                        on_click=lambda c=cname, idx=i: self._select_class(c, idx))
            self.class_buttons.append(btn)
            self.elements.append(btn)

        self.class_desc = Text(CHARACTER_CLASSES["Guerrier"]["description"],
                              parent=camera.ui, position=(0, 0.02), origin=(0, 0),
                              scale=1, color=color.light_gray)
        self.elements.append(self.class_desc)

        self.class_stats = Text(self._stats_text(), parent=camera.ui,
                               position=(0, -0.06), origin=(0, 0), scale=0.85, color=color.orange)
        self.elements.append(self.class_stats)

        # Armes
        self.weapon_label = Text("Arme:", parent=camera.ui, position=(-0.45, -0.16),
                                origin=(-0.5, 0), scale=1.2, color=color.white)
        self.elements.append(self.weapon_label)

        self.weapon_buttons = []
        for i, wkey in enumerate(WEAPONS.keys()):
            is_sel = wkey == self.selected_weapon
            btn = Button(text=WEAPONS[wkey]["name"], parent=camera.ui,
                        position=(-0.25 + i * 0.17, -0.23), scale=(0.13, 0.05),
                        color=color.azure if is_sel else color.dark_gray,
                        on_click=lambda w=wkey, idx=i: self._select_weapon(w, idx))
            self.weapon_buttons.append(btn)
            self.elements.append(btn)

        self.weapon_stats = Text(self._weapon_text(), parent=camera.ui,
                                position=(0, -0.31), origin=(0, 0), scale=0.85, color=color.yellow)
        self.elements.append(self.weapon_stats)

        # Couleurs
        self.color_label = Text("Couleur:", parent=camera.ui, position=(-0.45, -0.4),
                               origin=(-0.5, 0), scale=1.2, color=color.white)
        self.elements.append(self.color_label)

        self.color_buttons = []
        for i, (_, cval) in enumerate(PLAYER_COLORS):
            btn = Button(text="", parent=camera.ui, position=(-0.3 + i * 0.09, -0.46),
                        scale=(0.055, 0.055),
                        color=color.rgb(int(cval[0]*255), int(cval[1]*255), int(cval[2]*255)),
                        on_click=lambda idx=i: self._select_color(idx))
            if i == 0:
                btn.scale = (0.065, 0.065)
            self.color_buttons.append(btn)
            self.elements.append(btn)

        # Boutons navigation
        self.btn_back = Button(text="< Retour", parent=camera.ui, position=(-0.22, -0.58),
                              scale=(0.18, 0.06), color=color.dark_gray,
                              highlight_color=color.red, on_click=self._back)
        self.elements.append(self.btn_back)

        self.btn_start = Button(text="PARTIR À L'AVENTURE >", parent=camera.ui,
                               position=(0.22, -0.58), scale=(0.3, 0.07),
                               color=color.lime, on_click=self._confirm)
        self.elements.append(self.btn_start)

    def _stats_text(self):
        s = CHARACTER_CLASSES[self.selected_class]
        return f"PV: {s['health']} | Vitesse: {s['speed']} | Dégâts: x{s['damage_bonus']} | Mana: {s['mana']}"

    def _weapon_text(self):
        w = WEAPONS[self.selected_weapon]
        return f"Dégâts: {w['damage']} | Portée: {w['range']} | Vitesse: {w['speed']}"

    def _select_class(self, cname, idx):
        self.selected_class = cname
        for i, btn in enumerate(self.class_buttons):
            btn.color = color.azure if i == idx else color.dark_gray
        self.class_desc.text = CHARACTER_CLASSES[cname]["description"]
        self.class_stats.text = self._stats_text()

    def _select_weapon(self, wkey, idx):
        self.selected_weapon = wkey
        for i, btn in enumerate(self.weapon_buttons):
            btn.color = color.azure if i == idx else color.dark_gray
        self.weapon_stats.text = self._weapon_text()

    def _select_color(self, idx):
        self.selected_color_idx = idx
        for i, btn in enumerate(self.color_buttons):
            btn.scale = (0.065, 0.065) if i == idx else (0.055, 0.055)

    def _back(self):
        self.hide()
        self.on_back()

    def _confirm(self):
        config = {
            "name": self.name_input.text or "Héros",
            "class": self.selected_class,
            "weapon": self.selected_weapon,
            "color": PLAYER_COLORS[self.selected_color_idx][1],
            "stats": CHARACTER_CLASSES[self.selected_class].copy(),
        }
        self.hide()
        self.on_confirm(config)

    def hide(self):
        for e in self.elements:
            e.enabled = False

    def show(self):
        for e in self.elements:
            e.enabled = True

    def destroy(self):
        for e in self.elements:
            destroy(e)


# =============================================================================
# ENTITÉS DU MONDE
# =============================================================================

class TerrainTile(Entity):
    """Tuile de terrain avec hauteur."""

    def __init__(self, position: Vec3, height: float, terrain_type: str):
        # Couleur selon le type
        colors = {
            "grass": color.rgb(45, 140, 45),
            "dirt": color.rgb(140, 100, 60),
            "stone": color.rgb(120, 120, 125),
            "sand": color.rgb(210, 190, 140),
            "snow": color.rgb(240, 245, 250),
        }
        tile_color = colors.get(terrain_type, colors["grass"])

        # Variation de couleur pour plus de réalisme
        variation = random.uniform(0.85, 1.15)
        r = min(255, int(tile_color.r * variation))
        g = min(255, int(tile_color.g * variation))
        b = min(255, int(tile_color.b * variation))

        super().__init__(
            model="cube",
            color=color.rgb(r, g, b),
            position=position + Vec3(0, height / 2, 0),
            scale=(CELL_SIZE, max(0.3, height), CELL_SIZE),
            collider="box" if height > 1.5 else None,
        )
        self.terrain_type = terrain_type
        self.height = height


class Water(Entity):
    """Étendue d'eau."""

    def __init__(self, position: Vec3):
        super().__init__(
            model="cube",
            color=color.rgba(40, 120, 200, 180),
            position=position + Vec3(0, -0.3, 0),
            scale=(CELL_SIZE, 0.5, CELL_SIZE),
        )


class Tree(Entity):
    """Arbre avec tronc et feuillage."""

    def __init__(self, position: Vec3, height: float):
        super().__init__(
            model="cube",
            color=color.rgb(80, 50, 30),
            position=position + Vec3(0, height + 1.5, 0),
            scale=(0.6, 3, 0.6),
            collider="box",
        )
        # Feuillage
        self.leaves = Entity(
            model="cube",
            color=color.rgb(30 + random.randint(-10, 10), 100 + random.randint(-20, 20), 30),
            position=position + Vec3(0, height + 4, 0),
            scale=(2.5, 3, 2.5),
        )


class Rock(Entity):
    """Rocher décoratif."""

    def __init__(self, position: Vec3, height: float):
        size = random.uniform(0.8, 2.0)
        super().__init__(
            model="cube",
            color=color.rgb(100 + random.randint(-20, 20), 100 + random.randint(-20, 20), 105),
            position=position + Vec3(0, height + size / 2, 0),
            scale=(size, size * 0.7, size),
            collider="box",
        )


# =============================================================================
# BÂTIMENTS
# =============================================================================

class Building:
    """Classe de base pour les bâtiments."""

    def __init__(self, position: Vec3, building_type: str):
        self.position = position
        self.building_type = building_type
        self.entities = []
        self._build()

    def _build(self):
        pass

    def destroy(self):
        for e in self.entities:
            destroy(e)


class House(Building):
    """Maison de village."""

    def _build(self):
        pos = self.position
        # Fondation
        foundation = Entity(model="cube", color=color.rgb(80, 60, 40),
                           position=pos + Vec3(0, 0.25, 0), scale=(6, 0.5, 5), collider="box")
        self.entities.append(foundation)

        # Murs
        wall_color = color.rgb(180 + random.randint(-20, 20), 160 + random.randint(-20, 20), 120)
        for wall_pos, wall_scale in [
            (Vec3(0, 2, 2.4), (6, 3.5, 0.3)),  # Mur arrière
            (Vec3(0, 2, -2.4), (6, 3.5, 0.3)),  # Mur avant
            (Vec3(2.9, 2, 0), (0.3, 3.5, 5)),  # Mur droit
            (Vec3(-2.9, 2, 0), (0.3, 3.5, 5)),  # Mur gauche
        ]:
            wall = Entity(model="cube", color=wall_color,
                         position=pos + wall_pos, scale=wall_scale, collider="box")
            self.entities.append(wall)

        # Toit (deux pans)
        roof_color = color.rgb(120, 60, 40)
        roof1 = Entity(model="cube", color=roof_color,
                      position=pos + Vec3(-1.5, 4.5, 0), scale=(3.5, 0.3, 6),
                      rotation=(0, 0, 30))
        roof2 = Entity(model="cube", color=roof_color,
                      position=pos + Vec3(1.5, 4.5, 0), scale=(3.5, 0.3, 6),
                      rotation=(0, 0, -30))
        self.entities.extend([roof1, roof2])

        # Porte
        door = Entity(model="cube", color=color.rgb(100, 70, 40),
                     position=pos + Vec3(0, 1.2, -2.5), scale=(1.2, 2.2, 0.2))
        self.entities.append(door)

        # Fenêtres
        for fx in [-1.5, 1.5]:
            window = Entity(model="cube", color=color.rgb(150, 200, 230),
                           position=pos + Vec3(fx, 2.5, -2.5), scale=(0.8, 0.8, 0.2))
            self.entities.append(window)


class Tavern(Building):
    """Taverne/Auberge."""

    def _build(self):
        pos = self.position
        # Bâtiment principal plus grand
        main = Entity(model="cube", color=color.rgb(160, 130, 90),
                     position=pos + Vec3(0, 2.5, 0), scale=(10, 5, 8), collider="box")
        self.entities.append(main)

        # Toit
        roof = Entity(model="cube", color=color.rgb(80, 40, 30),
                     position=pos + Vec3(0, 5.5, 0), scale=(11, 1, 9))
        self.entities.append(roof)

        # Enseigne
        sign_post = Entity(model="cube", color=color.rgb(100, 70, 40),
                          position=pos + Vec3(-5.5, 3, 0), scale=(0.3, 3, 0.3))
        sign = Entity(model="cube", color=color.rgb(180, 150, 100),
                     position=pos + Vec3(-6.5, 4, 0), scale=(2, 1, 0.2))
        self.entities.extend([sign_post, sign])

        # Grande porte
        door = Entity(model="cube", color=color.rgb(90, 60, 35),
                     position=pos + Vec3(0, 1.5, -4.1), scale=(2, 3, 0.2))
        self.entities.append(door)

        # Fenêtres illuminées
        for fx, fz in [(-3, -4), (3, -4), (-3, 4), (3, 4)]:
            window = Entity(model="cube", color=color.rgb(255, 220, 150),
                           position=pos + Vec3(fx, 2.5, fz), scale=(1.5, 1.5, 0.3))
            self.entities.append(window)


class Tower(Building):
    """Tour de garde."""

    def _build(self):
        pos = self.position
        # Base
        base = Entity(model="cube", color=color.rgb(100, 100, 105),
                     position=pos + Vec3(0, 3, 0), scale=(5, 6, 5), collider="box")
        self.entities.append(base)

        # Étage supérieur
        top = Entity(model="cube", color=color.rgb(90, 90, 95),
                    position=pos + Vec3(0, 8, 0), scale=(6, 4, 6), collider="box")
        self.entities.append(top)

        # Créneaux
        for cx, cz in [(-2.5, 0), (2.5, 0), (0, -2.5), (0, 2.5)]:
            crenel = Entity(model="cube", color=color.rgb(85, 85, 90),
                           position=pos + Vec3(cx, 10.5, cz), scale=(1.5, 1, 1.5))
            self.entities.append(crenel)

        # Toit conique (approximé)
        roof = Entity(model="cube", color=color.rgb(60, 40, 40),
                     position=pos + Vec3(0, 11.5, 0), scale=(4, 2, 4))
        self.entities.append(roof)


class Temple(Building):
    """Temple/Sanctuaire."""

    def _build(self):
        pos = self.position
        # Plateforme
        platform = Entity(model="cube", color=color.rgb(200, 195, 185),
                         position=pos + Vec3(0, 0.5, 0), scale=(14, 1, 10), collider="box")
        self.entities.append(platform)

        # Colonnes
        for cx in [-5, -2.5, 2.5, 5]:
            for cz in [-3.5, 3.5]:
                column = Entity(model="cube", color=color.rgb(220, 215, 200),
                               position=pos + Vec3(cx, 4, cz), scale=(1, 7, 1), collider="box")
                self.entities.append(column)

        # Fronton
        front = Entity(model="cube", color=color.rgb(210, 205, 190),
                      position=pos + Vec3(0, 7.5, 0), scale=(12, 1, 8))
        self.entities.append(front)

        # Toit triangulaire
        roof = Entity(model="cube", color=color.rgb(180, 175, 160),
                     position=pos + Vec3(0, 9, 0), scale=(13, 2, 9),
                     rotation=(0, 0, 0))
        self.entities.append(roof)

        # Autel
        altar = Entity(model="cube", color=color.rgb(150, 140, 130),
                      position=pos + Vec3(0, 1.5, 0), scale=(2, 1.5, 1.5))
        self.entities.append(altar)


class Well(Building):
    """Puits de village."""

    def _build(self):
        pos = self.position
        # Base circulaire (approximée par un cube)
        base = Entity(model="cube", color=color.rgb(120, 110, 100),
                     position=pos + Vec3(0, 0.5, 0), scale=(2, 1, 2), collider="box")
        self.entities.append(base)

        # Poteaux
        for px in [-0.8, 0.8]:
            post = Entity(model="cube", color=color.rgb(90, 60, 40),
                         position=pos + Vec3(px, 2, 0), scale=(0.2, 3, 0.2))
            self.entities.append(post)

        # Toit
        roof = Entity(model="cube", color=color.rgb(100, 70, 45),
                     position=pos + Vec3(0, 3.5, 0), scale=(2.5, 0.3, 1.5))
        self.entities.append(roof)


# =============================================================================
# PNJ (Personnages Non-Joueurs)
# =============================================================================

class NPC(Entity):
    """PNJ interactif."""

    def __init__(self, position: Vec3, npc_type: str, name: str = None):
        npc_data = NPC_TYPES.get(npc_type, NPC_TYPES["villager"])
        npc_color = npc_data["color"]

        super().__init__(
            model="cube",
            color=color.rgb(int(npc_color[0]*255), int(npc_color[1]*255), int(npc_color[2]*255)),
            position=position + Vec3(0, 1, 0),
            scale=(0.8, 2, 0.6),
            collider="box",
        )

        self.npc_type = npc_type
        self.npc_name = name or npc_data["name"]
        self.dialogues = npc_data["dialogues"]
        self.current_dialogue = 0
        self.is_talking = False

        # Tête (plus claire)
        head_color = tuple(min(1.0, c + 0.2) for c in npc_color)
        self.head = Entity(
            model="cube",
            color=color.rgb(int(head_color[0]*255), int(head_color[1]*255), int(head_color[2]*255)),
            position=Vec3(0, 1.3, 0),
            scale=(0.5, 0.5, 0.5),
            parent=self,
        )

        # Indicateur d'interaction
        self.indicator = Text(
            text="[E]",
            position=Vec3(0, 2.5, 0),
            scale=15,
            color=color.yellow,
            parent=self,
            billboard=True,
            enabled=False,
        )

        # Nom au-dessus
        self.name_text = Text(
            text=self.npc_name,
            position=Vec3(0, 2.8, 0),
            scale=12,
            color=color.white,
            parent=self,
            billboard=True,
        )

    def get_dialogue(self) -> str:
        """Retourne le dialogue actuel et passe au suivant."""
        dialogue = self.dialogues[self.current_dialogue]
        self.current_dialogue = (self.current_dialogue + 1) % len(self.dialogues)
        return dialogue

    def show_indicator(self, show: bool):
        self.indicator.enabled = show


# =============================================================================
# ENNEMIS
# =============================================================================

class Enemy(Entity):
    """Ennemi hostile."""

    def __init__(self, position: Vec3, enemy_type: str):
        data = ENEMY_TYPES.get(enemy_type, ENEMY_TYPES["goblin"])

        super().__init__(
            model="cube",
            color=color.rgb(int(data["color"][0]*255), int(data["color"][1]*255), int(data["color"][2]*255)),
            position=position + Vec3(0, 1, 0),
            scale=(1, 2, 0.8),
            collider="box",
        )

        self.enemy_type = enemy_type
        self.enemy_name = data["name"]
        self.max_health = data["health"]
        self.health = self.max_health
        self.damage = data["damage"]
        self.speed = data["speed"]
        self.state = "idle"
        self.detection_range = 15.0
        self.attack_range = 2.0
        self.last_attack = 0

        # Barre de vie
        self.health_bar_bg = Entity(
            model="cube", color=color.dark_gray,
            position=Vec3(0, 1.5, 0), scale=(1.2, 0.15, 0.1),
            parent=self, billboard=True,
        )
        self.health_bar = Entity(
            model="cube", color=color.red,
            position=Vec3(0, 1.5, 0.01), scale=(1.1, 0.1, 0.1),
            parent=self, billboard=True,
        )

    def take_damage(self, amount: int):
        self.health -= amount
        # Mettre à jour la barre de vie
        ratio = max(0, self.health / self.max_health)
        self.health_bar.scale_x = 1.1 * ratio
        self.color = color.rgb(255, 150, 150)

        if self.health <= 0:
            destroy(self.health_bar_bg)
            destroy(self.health_bar)
            destroy(self)

    def update_ai(self, player_pos: Vec3, dt: float):
        if self.health <= 0:
            return

        to_player = player_pos - self.position
        dist = to_player.length()

        if dist < self.detection_range:
            self.state = "chase"
            if dist > self.attack_range:
                direction = Vec3(to_player.x, 0, to_player.z).normalized()
                self.position += direction * self.speed * dt
            self.look_at_2d(player_pos)
        else:
            self.state = "idle"

        # Reset couleur
        if self.health > 0:
            data = ENEMY_TYPES[self.enemy_type]
            self.color = color.rgb(int(data["color"][0]*255), int(data["color"][1]*255), int(data["color"][2]*255))

    def look_at_2d(self, target: Vec3):
        direction = target - self.position
        if direction.length() > 0:
            angle = math.degrees(math.atan2(direction.x, direction.z))
            self.rotation_y = angle


# =============================================================================
# JOUEUR
# =============================================================================

class Player(Entity):
    """Joueur contrôlable."""

    def __init__(self, position: Vec3, config: dict = None):
        super().__init__(
            model=None,
            collider="box",
            scale=(0.8, 2.0, 0.8),
            position=position + Vec3(0, 1, 0),
        )

        # Config personnage
        if config:
            self.player_name = config.get("name", "Héros")
            self.player_class = config.get("class", "Guerrier")
            stats = config.get("stats", {})
            self.health = stats.get("health", 100)
            self.max_health = self.health
            self.speed = stats.get("speed", 6.0)
            self.damage_bonus = stats.get("damage_bonus", 1.0)
            self.mana = stats.get("mana", 50)
            self.max_mana = self.mana
            self.player_color = config.get("color", (1.0, 0.2, 0.2))
            self.current_weapon = config.get("weapon", "sword")
        else:
            self.player_name = "Héros"
            self.player_class = "Guerrier"
            self.health = 100
            self.max_health = 100
            self.speed = 6.0
            self.damage_bonus = 1.0
            self.mana = 50
            self.max_mana = 50
            self.player_color = (1.0, 0.2, 0.2)
            self.current_weapon = "sword"

        self.yaw = 0.0
        self.pitch = 0.0
        self.last_attack = 0
        self.gold = 50

        # Camera setup
        camera.parent = self
        camera.position = Vec3(0, 0.8, 0)
        camera.rotation = Vec3(0, 0, 0)

        # Arme visible
        weapon_data = WEAPONS[self.current_weapon]
        self.weapon_model = Entity(
            model="cube",
            color=color.rgb(int(self.player_color[0]*200),
                           int(self.player_color[1]*180),
                           int(self.player_color[2]*150)),
            position=Vec3(0.35, -0.3, -0.5),
            scale=(0.12, 0.5, 0.08),
            parent=camera,
        )

    def handle_input(self, dt: float):
        # Rotation souris
        if mouse.locked:
            self.yaw -= mouse.velocity[0] * MOUSE_SENSITIVITY
            self.pitch -= mouse.velocity[1] * MOUSE_SENSITIVITY
            self.pitch = max(-89, min(89, self.pitch))
            self.rotation_y = self.yaw
            camera.rotation_x = self.pitch

        # Mouvement ZQSD
        move = Vec3(0, 0, 0)
        forward = Vec3(math.sin(math.radians(self.yaw)), 0, math.cos(math.radians(self.yaw)))
        right = Vec3(forward.z, 0, -forward.x)

        if held_keys["z"]: move += forward
        if held_keys["s"]: move -= forward
        if held_keys["q"]: move -= right
        if held_keys["d"]: move += right

        if move.length() > 0:
            move = move.normalized() * self.speed * dt
            self.position += move

    def attack(self, enemies: List[Enemy]) -> Optional[Enemy]:
        weapon = WEAPONS[self.current_weapon]
        now = time.time()

        if now - self.last_attack < weapon["speed"]:
            return None

        self.last_attack = now

        hit = raycast(camera.world_position, camera.forward,
                     distance=weapon["range"], ignore=[self])

        if hit.hit and isinstance(hit.entity, Enemy):
            damage = int(weapon["damage"] * self.damage_bonus)
            hit.entity.take_damage(damage)
            return hit.entity
        return None

    def change_weapon(self, weapon_key: str):
        if weapon_key in WEAPONS:
            self.current_weapon = weapon_key
            self.weapon_model.scale = (0.12, 0.4 + WEAPONS[weapon_key]["damage"] / 100, 0.08)


# =============================================================================
# SYSTÈME DE DIALOGUE
# =============================================================================

class DialogueBox:
    """Boîte de dialogue pour les PNJ."""

    def __init__(self):
        self.elements = []
        self.visible = False

    def show(self, npc_name: str, text: str):
        self.hide()
        self.visible = True

        self.bg = Entity(parent=camera.ui, model='quad',
                        color=color.rgba(20, 20, 30, 230),
                        position=(0, -0.35), scale=(1.2, 0.25), z=0)
        self.elements.append(self.bg)

        self.name_text = Text(npc_name, parent=camera.ui,
                             position=(-0.55, -0.26), origin=(-0.5, 0),
                             scale=1.3, color=color.gold)
        self.elements.append(self.name_text)

        self.dialogue_text = Text(text, parent=camera.ui,
                                 position=(-0.55, -0.35), origin=(-0.5, 0),
                                 scale=1, color=color.white)
        self.elements.append(self.dialogue_text)

        self.hint = Text("[E] Continuer", parent=camera.ui,
                        position=(0.45, -0.45), origin=(0.5, 0),
                        scale=0.8, color=color.gray)
        self.elements.append(self.hint)

    def hide(self):
        self.visible = False
        for e in self.elements:
            destroy(e)
        self.elements.clear()


# =============================================================================
# JEU PRINCIPAL
# =============================================================================

class Game:
    """Gestionnaire principal du jeu."""

    def __init__(self):
        self.state = "menu"
        self.noise = NoiseGenerator(seed=42)
        self.rng = random.Random(42)

        # Entités
        self.player: Optional[Player] = None
        self.npcs: List[NPC] = []
        self.enemies: List[Enemy] = []
        self.buildings: List[Building] = []
        self.terrain_tiles: List[Entity] = []

        # UI
        self.main_menu: Optional[MainMenu] = None
        self.char_creation: Optional[CharacterCreation] = None
        self.dialogue_box = DialogueBox()
        self.hud_elements = []
        self.current_npc: Optional[NPC] = None

        # Démarrer
        self._show_main_menu()

    def _show_main_menu(self):
        self.state = "menu"
        mouse.locked = False
        if self.char_creation:
            self.char_creation.destroy()
        self.main_menu = MainMenu(on_start_game=self._show_character_creation)

    def _show_character_creation(self):
        self.state = "creation"
        if self.main_menu:
            self.main_menu.destroy()
        self.char_creation = CharacterCreation(
            on_confirm=self._start_game,
            on_back=self._show_main_menu
        )

    def _start_game(self, config: dict):
        self.state = "playing"
        if self.char_creation:
            self.char_creation.destroy()

        self._build_world()
        self._create_player(config)
        self._spawn_npcs()
        self._spawn_enemies()
        self._build_hud(config)

        mouse.locked = True

    def _build_world(self):
        """Construit le monde avec terrain, bâtiments, etc."""
        # Ciel
        Entity(model="sphere", color=color.rgb(135, 190, 220),
               scale=2000, double_sided=True)

        # Soleil
        Entity(model="sphere", color=color.rgb(255, 240, 200),
               scale=50, position=Vec3(500, 600, 300))

        # Générer le terrain
        height_map = {}
        for y in range(WORLD_SIZE):
            for x in range(WORLD_SIZE):
                # Bruit pour la hauteur
                nx = x / WORLD_SIZE * 3
                ny = y / WORLD_SIZE * 3
                height = self.noise.fbm(nx, ny, octaves=4) * 8 + 2

                # Type de terrain selon la hauteur
                if height < 0.5:
                    terrain_type = "sand"
                elif height < 3:
                    terrain_type = "grass"
                elif height < 6:
                    terrain_type = "dirt"
                elif height < 9:
                    terrain_type = "stone"
                else:
                    terrain_type = "snow"

                wx = (x - WORLD_SIZE / 2) * CELL_SIZE
                wz = (y - WORLD_SIZE / 2) * CELL_SIZE
                pos = Vec3(wx, 0, wz)

                height_map[(x, y)] = height

                # Eau pour les zones basses
                if height < 0.5:
                    Water(pos)
                else:
                    tile = TerrainTile(pos, height, terrain_type)
                    self.terrain_tiles.append(tile)

                    # Arbres sur l'herbe
                    if terrain_type == "grass" and self.rng.random() < 0.05:
                        tree = Tree(pos, height)
                        self.terrain_tiles.append(tree)
                        self.terrain_tiles.append(tree.leaves)

                    # Rochers sur pierre/terre
                    if terrain_type in ["stone", "dirt"] and self.rng.random() < 0.03:
                        rock = Rock(pos, height)
                        self.terrain_tiles.append(rock)

        # Créer un village au centre
        self._create_village(Vec3(0, 3, 0))

        # Créer quelques structures dispersées
        for _ in range(3):
            rx = self.rng.randint(-30, 30) * CELL_SIZE
            rz = self.rng.randint(-30, 30) * CELL_SIZE
            self.buildings.append(Tower(Vec3(rx, 3, rz), "tower"))

    def _create_village(self, center: Vec3):
        """Crée un village avec plusieurs bâtiments."""
        # Place centrale aplatie
        for dx in range(-8, 9):
            for dz in range(-8, 9):
                Entity(model="cube", color=color.rgb(180, 160, 140),
                       position=center + Vec3(dx * 2, -0.2, dz * 2),
                       scale=(2, 0.5, 2))

        # Bâtiments du village
        self.buildings.append(Tavern(center + Vec3(-20, 0, 0), "tavern"))
        self.buildings.append(Temple(center + Vec3(25, 0, 0), "temple"))
        self.buildings.append(Well(center + Vec3(0, 0, 0), "well"))

        # Maisons autour
        house_positions = [
            Vec3(-20, 0, 20), Vec3(-10, 0, 25), Vec3(10, 0, 25),
            Vec3(20, 0, 20), Vec3(-25, 0, -15), Vec3(25, 0, -15),
        ]
        for pos in house_positions:
            self.buildings.append(House(center + pos, "house"))

        # Tour de garde
        self.buildings.append(Tower(center + Vec3(0, 0, -30), "tower"))

    def _create_player(self, config: dict):
        """Crée le joueur."""
        self.player = Player(Vec3(0, 5, -20), config)

    def _spawn_npcs(self):
        """Fait apparaître les PNJ."""
        npc_spawns = [
            (Vec3(-18, 4, 2), "innkeeper", "Gérard"),
            (Vec3(22, 4, 2), "elder", "Sage Aldric"),
            (Vec3(-8, 4, 8), "merchant", "Marco"),
            (Vec3(8, 4, 8), "blacksmith", "Bjorn"),
            (Vec3(-5, 4, -25), "guard", "Capitaine Léon"),
            (Vec3(5, 4, -25), "guard", "Garde Erik"),
            (Vec3(-15, 4, 22), "villager", "Marie"),
            (Vec3(15, 4, 22), "villager", "Pierre"),
            (Vec3(0, 4, 15), "villager", "Élise"),
        ]
        for pos, npc_type, name in npc_spawns:
            npc = NPC(pos, npc_type, name)
            self.npcs.append(npc)

    def _spawn_enemies(self):
        """Fait apparaître les ennemis loin du village."""
        enemy_zones = [
            (Vec3(-60, 4, -60), "goblin", 4),
            (Vec3(60, 4, -60), "orc", 3),
            (Vec3(-60, 4, 60), "wolf", 5),
            (Vec3(60, 4, 60), "skeleton", 4),
            (Vec3(0, 4, 70), "troll", 2),
        ]
        for base_pos, enemy_type, count in enemy_zones:
            for _ in range(count):
                offset = Vec3(self.rng.uniform(-15, 15), 0, self.rng.uniform(-15, 15))
                enemy = Enemy(base_pos + offset, enemy_type)
                self.enemies.append(enemy)

    def _build_hud(self, config: dict):
        """Construit l'interface utilisateur."""
        name = config.get("name", "Héros")
        player_class = config.get("class", "Guerrier")
        pcolor = config.get("color", (1.0, 0.2, 0.2))

        # Nom et classe
        self.hud_name = Text(f"{name} - {player_class}",
                            position=Vec2(-0.88, 0.48), origin=(0, 0), scale=1.2,
                            color=color.rgb(int(pcolor[0]*255), int(pcolor[1]*255), int(pcolor[2]*255)))
        self.hud_elements.append(self.hud_name)

        # Barre de vie
        self.hud_hp_bg = Entity(parent=camera.ui, model='quad', color=color.dark_gray,
                               position=(-0.68, 0.43), scale=(0.35, 0.025), origin=(-0.5, 0))
        self.hud_hp = Entity(parent=camera.ui, model='quad', color=color.red,
                            position=(-0.68, 0.43), scale=(0.35, 0.02), origin=(-0.5, 0))
        self.hud_hp_text = Text(f"PV: {self.player.health}/{self.player.max_health}",
                               position=Vec2(-0.88, 0.40), origin=(0, 0), scale=0.9, color=color.white)
        self.hud_elements.extend([self.hud_hp_bg, self.hud_hp, self.hud_hp_text])

        # Barre de mana
        self.hud_mp_bg = Entity(parent=camera.ui, model='quad', color=color.dark_gray,
                               position=(-0.68, 0.36), scale=(0.25, 0.02), origin=(-0.5, 0))
        self.hud_mp = Entity(parent=camera.ui, model='quad', color=color.azure,
                            position=(-0.68, 0.36), scale=(0.25, 0.015), origin=(-0.5, 0))
        self.hud_mp_text = Text(f"Mana: {self.player.mana}/{self.player.max_mana}",
                               position=Vec2(-0.88, 0.33), origin=(0, 0), scale=0.85, color=color.cyan)
        self.hud_elements.extend([self.hud_mp_bg, self.hud_mp, self.hud_mp_text])

        # Arme
        weapon_name = WEAPONS.get(self.player.current_weapon, {}).get("name", "Arme")
        self.hud_weapon = Text(f"Arme: {weapon_name} (1/2/3/4)",
                              position=Vec2(-0.88, 0.26), origin=(0, 0), scale=0.9, color=color.yellow)
        self.hud_elements.append(self.hud_weapon)

        # Or
        self.hud_gold = Text(f"Or: {self.player.gold}",
                            position=Vec2(-0.88, 0.19), origin=(0, 0), scale=0.9, color=color.gold)
        self.hud_elements.append(self.hud_gold)

        # Ennemis
        self.hud_enemies = Text(f"Ennemis: {len(self.enemies)}",
                               position=Vec2(-0.88, 0.12), origin=(0, 0), scale=0.9, color=color.orange)
        self.hud_elements.append(self.hud_enemies)

        # Crosshair
        self.crosshair = Text("+", position=(0, 0), origin=(0, 0), scale=2, color=color.white)
        self.hud_elements.append(self.crosshair)

    def handle_input(self, key: str):
        if self.state != "playing":
            return

        if key == "escape":
            mouse.locked = not mouse.locked

        if key == "left mouse down" and mouse.locked:
            if not self.dialogue_box.visible:
                self.player.attack(self.enemies)

        # Changement d'armes
        weapon_keys = {"1": "dagger", "2": "sword", "3": "axe", "4": "staff"}
        if key in weapon_keys:
            self.player.change_weapon(weapon_keys[key])

        # Interaction avec PNJ
        if key == "e":
            if self.dialogue_box.visible:
                if self.current_npc:
                    dialogue = self.current_npc.get_dialogue()
                    self.dialogue_box.show(self.current_npc.npc_name, dialogue)
            elif self.current_npc:
                dialogue = self.current_npc.get_dialogue()
                self.dialogue_box.show(self.current_npc.npc_name, dialogue)

        # Fermer dialogue
        if key == "escape" and self.dialogue_box.visible:
            self.dialogue_box.hide()
            self.current_npc = None

    def update(self):
        if self.state != "playing" or not self.player:
            return

        dt = time.dt

        # Joueur
        if not self.dialogue_box.visible:
            self.player.handle_input(dt)

        # Ennemis IA
        for enemy in list(self.enemies):
            if hasattr(enemy, "health") and enemy.health > 0:
                enemy.update_ai(self.player.position, dt)

        # Nettoyer ennemis morts
        self.enemies = [e for e in self.enemies if hasattr(e, "health") and e.health > 0]

        # Détection PNJ proche
        self._check_npc_proximity()

        # Mise à jour HUD
        self._update_hud()

    def _check_npc_proximity(self):
        """Vérifie si un PNJ est proche pour interaction."""
        closest_npc = None
        min_dist = 5.0

        for npc in self.npcs:
            dist = (npc.position - self.player.position).length()
            if dist < min_dist:
                min_dist = dist
                closest_npc = npc

        # Mettre à jour les indicateurs
        for npc in self.npcs:
            npc.show_indicator(npc == closest_npc)

        self.current_npc = closest_npc

    def _update_hud(self):
        """Met à jour l'affichage du HUD."""
        # Vie
        hp_ratio = max(0, self.player.health / self.player.max_health)
        self.hud_hp.scale_x = 0.35 * hp_ratio
        self.hud_hp_text.text = f"PV: {self.player.health}/{self.player.max_health}"

        # Mana
        mp_ratio = max(0, self.player.mana / self.player.max_mana)
        self.hud_mp.scale_x = 0.25 * mp_ratio
        self.hud_mp_text.text = f"Mana: {self.player.mana}/{self.player.max_mana}"

        # Arme
        weapon_name = WEAPONS.get(self.player.current_weapon, {}).get("name", "Arme")
        self.hud_weapon.text = f"Arme: {weapon_name} (1/2/3/4)"

        # Or
        self.hud_gold.text = f"Or: {self.player.gold}"

        # Ennemis
        self.hud_enemies.text = f"Ennemis: {len(self.enemies)}"


# =============================================================================
# LANCEMENT
# =============================================================================

if __name__ == "__main__":
    app = Ursina(title="TES1: Arena - Monde Ouvert")

    game = Game()

    def update():
        game.update()

    def input(key):
        game.handle_input(key)

    app.run()
