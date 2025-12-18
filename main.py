"""
RPG Rétro TES1: Arena - FPS avec textures procédurales Ursina Engine.

Fonctionnalités :
- Génération de textures procédurales en mémoire (brique, bois, herbe)
- Monde labyrinthe procédural texturé
- Arme FPS avec animation d'attaque
- Combat avec raycast
- Style pixel-art rétro
- ZQSD pour bouger, souris pour regarder, clic pour attaquer

Lancement : python main.py
"""

from __future__ import annotations
import random
import math
from typing import List

from panda3d.core import PNMImage, Texture
from ursina import (
    Ursina,
    Entity,
    camera,
    mouse,
    Text,
    Vec3,
    Vec2,
    color,
    time,
    held_keys,
    raycast,
    destroy,
    application,
    Button,
    Slider,
    InputField,
    Audio,
)


# ============================================================================
# CONFIGURATION DES CLASSES DE PERSONNAGE
# ============================================================================

CHARACTER_CLASSES = {
    "Guerrier": {
        "description": "Expert au combat rapproché",
        "health": 120,
        "speed": 5.0,
        "damage_bonus": 1.2,
        "mana": 20,
        "color": (0.8, 0.2, 0.2),  # Rouge
        "starting_weapon": "sword",
    },
    "Mage": {
        "description": "Maître des arcanes",
        "health": 70,
        "speed": 5.5,
        "damage_bonus": 1.0,
        "mana": 100,
        "color": (0.2, 0.2, 0.8),  # Bleu
        "starting_weapon": "dagger",
    },
    "Voleur": {
        "description": "Rapide et furtif",
        "health": 85,
        "speed": 7.5,
        "damage_bonus": 1.5,
        "mana": 40,
        "color": (0.2, 0.6, 0.2),  # Vert
        "starting_weapon": "dagger",
    },
    "Berserker": {
        "description": "Force brute dévastatrice",
        "health": 150,
        "speed": 4.0,
        "damage_bonus": 1.8,
        "mana": 10,
        "color": (0.6, 0.3, 0.1),  # Brun
        "starting_weapon": "axe",
    },
}

WEAPONS = {
    "dagger": {"name": "Dague", "damage": 12, "range": 3, "speed": 0.15},
    "sword": {"name": "Épée", "damage": 25, "range": 5, "speed": 0.4},
    "axe": {"name": "Hache", "damage": 45, "range": 4, "speed": 0.6},
}

PLAYER_COLORS = [
    ("Rouge", (1.0, 0.2, 0.2)),
    ("Bleu", (0.2, 0.4, 1.0)),
    ("Vert", (0.2, 0.8, 0.2)),
    ("Or", (0.9, 0.7, 0.1)),
    ("Violet", (0.6, 0.2, 0.8)),
    ("Cyan", (0.2, 0.8, 0.8)),
    ("Orange", (1.0, 0.5, 0.1)),
    ("Blanc", (0.9, 0.9, 0.9)),
]


# ============================================================================
# SYSTÈME DE MENU
# ============================================================================

class MainMenu:
    """Menu principal du jeu."""

    def __init__(self, on_start_game):
        self.on_start_game = on_start_game
        self.elements = []
        self.visible = True
        self._build_menu()

    def _build_menu(self):
        """Construit le menu principal."""
        # Fond semi-transparent
        self.background = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgba(0, 0, 0, 200),
            scale=(2, 2),
            z=1,
        )
        self.elements.append(self.background)

        # Titre du jeu
        self.title = Text(
            text="TES1: ARENA",
            parent=camera.ui,
            position=(0, 0.35),
            origin=(0, 0),
            scale=4,
            color=color.gold,
        )
        self.elements.append(self.title)

        # Sous-titre
        self.subtitle = Text(
            text="RPG Rétro - Aventure dans les ténèbres",
            parent=camera.ui,
            position=(0, 0.25),
            origin=(0, 0),
            scale=1.5,
            color=color.light_gray,
        )
        self.elements.append(self.subtitle)

        # Bouton Nouvelle Partie
        self.btn_new_game = Button(
            text="Nouvelle Partie",
            parent=camera.ui,
            position=(0, 0.05),
            scale=(0.4, 0.08),
            color=color.dark_gray,
            highlight_color=color.gray,
            on_click=self._on_new_game,
        )
        self.elements.append(self.btn_new_game)

        # Bouton Quitter
        self.btn_quit = Button(
            text="Quitter",
            parent=camera.ui,
            position=(0, -0.15),
            scale=(0.4, 0.08),
            color=color.dark_gray,
            highlight_color=color.red,
            on_click=application.quit,
        )
        self.elements.append(self.btn_quit)

        # Instructions
        self.instructions = Text(
            text="Contrôles: ZQSD - Déplacer | Souris - Regarder | Clic - Attaquer",
            parent=camera.ui,
            position=(0, -0.4),
            origin=(0, 0),
            scale=1,
            color=color.gray,
        )
        self.elements.append(self.instructions)

    def _on_new_game(self):
        """Appelé quand on clique sur Nouvelle Partie."""
        self.hide()
        self.on_start_game()

    def hide(self):
        """Cache le menu."""
        self.visible = False
        for element in self.elements:
            element.enabled = False

    def show(self):
        """Affiche le menu."""
        self.visible = True
        for element in self.elements:
            element.enabled = True

    def destroy(self):
        """Détruit le menu."""
        for element in self.elements:
            destroy(element)
        self.elements.clear()


class CharacterCustomization:
    """Menu de personnalisation du personnage."""

    def __init__(self, on_confirm, on_back):
        self.on_confirm = on_confirm
        self.on_back = on_back
        self.elements = []
        self.visible = True

        # Valeurs sélectionnées
        self.selected_class = "Guerrier"
        self.selected_weapon = "sword"
        self.selected_color_index = 0
        self.player_name = "Héros"

        self._build_menu()

    def _build_menu(self):
        """Construit le menu de personnalisation."""
        # Fond
        self.background = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgba(20, 20, 30, 230),
            scale=(2, 2),
            z=1,
        )
        self.elements.append(self.background)

        # Titre
        self.title = Text(
            text="CRÉATION DU PERSONNAGE",
            parent=camera.ui,
            position=(0, 0.42),
            origin=(0, 0),
            scale=2.5,
            color=color.gold,
        )
        self.elements.append(self.title)

        # === Section Nom ===
        self.name_label = Text(
            text="Nom du héros:",
            parent=camera.ui,
            position=(-0.5, 0.3),
            origin=(-0.5, 0),
            scale=1.2,
            color=color.white,
        )
        self.elements.append(self.name_label)

        self.name_input = InputField(
            default_value="Héros",
            parent=camera.ui,
            position=(0.1, 0.3),
            scale=(0.4, 0.05),
        )
        self.elements.append(self.name_input)

        # === Section Classe ===
        self.class_label = Text(
            text="Classe:",
            parent=camera.ui,
            position=(-0.5, 0.18),
            origin=(-0.5, 0),
            scale=1.2,
            color=color.white,
        )
        self.elements.append(self.class_label)

        # Boutons de classe
        class_names = list(CHARACTER_CLASSES.keys())
        self.class_buttons = []
        for i, class_name in enumerate(class_names):
            x_pos = -0.3 + i * 0.2
            btn = Button(
                text=class_name[:3],
                parent=camera.ui,
                position=(x_pos, 0.1),
                scale=(0.15, 0.06),
                color=color.dark_gray if i != 0 else color.azure,
                on_click=lambda cn=class_name, idx=i: self._select_class(cn, idx),
            )
            self.class_buttons.append(btn)
            self.elements.append(btn)

        # Description de la classe
        self.class_desc = Text(
            text=CHARACTER_CLASSES[self.selected_class]["description"],
            parent=camera.ui,
            position=(0, 0.02),
            origin=(0, 0),
            scale=1,
            color=color.light_gray,
        )
        self.elements.append(self.class_desc)

        # Stats de la classe
        self.class_stats = Text(
            text=self._get_class_stats_text(),
            parent=camera.ui,
            position=(0, -0.06),
            origin=(0, 0),
            scale=0.9,
            color=color.orange,
        )
        self.elements.append(self.class_stats)

        # === Section Arme ===
        self.weapon_label = Text(
            text="Arme de départ:",
            parent=camera.ui,
            position=(-0.5, -0.15),
            origin=(-0.5, 0),
            scale=1.2,
            color=color.white,
        )
        self.elements.append(self.weapon_label)

        self.weapon_buttons = []
        weapon_keys = list(WEAPONS.keys())
        for i, weapon_key in enumerate(weapon_keys):
            x_pos = -0.2 + i * 0.2
            is_selected = weapon_key == self.selected_weapon
            btn = Button(
                text=WEAPONS[weapon_key]["name"],
                parent=camera.ui,
                position=(x_pos, -0.22),
                scale=(0.15, 0.06),
                color=color.azure if is_selected else color.dark_gray,
                on_click=lambda wk=weapon_key, idx=i: self._select_weapon(wk, idx),
            )
            self.weapon_buttons.append(btn)
            self.elements.append(btn)

        # Stats de l'arme
        self.weapon_stats = Text(
            text=self._get_weapon_stats_text(),
            parent=camera.ui,
            position=(0, -0.3),
            origin=(0, 0),
            scale=0.9,
            color=color.yellow,
        )
        self.elements.append(self.weapon_stats)

        # === Section Couleur ===
        self.color_label = Text(
            text="Couleur:",
            parent=camera.ui,
            position=(-0.5, -0.38),
            origin=(-0.5, 0),
            scale=1.2,
            color=color.white,
        )
        self.elements.append(self.color_label)

        self.color_buttons = []
        for i, (color_name, color_val) in enumerate(PLAYER_COLORS):
            x_pos = -0.35 + i * 0.1
            btn = Button(
                text="",
                parent=camera.ui,
                position=(x_pos, -0.44),
                scale=(0.06, 0.06),
                color=color.rgb(int(color_val[0]*255), int(color_val[1]*255), int(color_val[2]*255)),
                on_click=lambda idx=i: self._select_color(idx),
            )
            if i == 0:
                btn.scale = (0.07, 0.07)  # Sélectionné
            self.color_buttons.append(btn)
            self.elements.append(btn)

        # Prévisualisation personnage
        self.preview_label = Text(
            text="Aperçu:",
            parent=camera.ui,
            position=(0.35, 0.18),
            origin=(0, 0),
            scale=1.2,
            color=color.white,
        )
        self.elements.append(self.preview_label)

        self.preview_entity = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgb(int(PLAYER_COLORS[0][1][0]*255),
                           int(PLAYER_COLORS[0][1][1]*255),
                           int(PLAYER_COLORS[0][1][2]*255)),
            position=(0.35, 0),
            scale=(0.08, 0.15),
            z=0,
        )
        self.elements.append(self.preview_entity)

        # === Boutons de navigation ===
        self.btn_back = Button(
            text="< Retour",
            parent=camera.ui,
            position=(-0.25, -0.55),
            scale=(0.2, 0.07),
            color=color.dark_gray,
            highlight_color=color.red,
            on_click=self._on_back,
        )
        self.elements.append(self.btn_back)

        self.btn_confirm = Button(
            text="COMMENCER >",
            parent=camera.ui,
            position=(0.25, -0.55),
            scale=(0.25, 0.08),
            color=color.lime,
            highlight_color=color.green,
            on_click=self._on_confirm,
        )
        self.elements.append(self.btn_confirm)

    def _get_class_stats_text(self):
        """Retourne le texte des stats de la classe."""
        stats = CHARACTER_CLASSES[self.selected_class]
        return f"PV: {stats['health']} | Vitesse: {stats['speed']} | Dégâts: x{stats['damage_bonus']} | Mana: {stats['mana']}"

    def _get_weapon_stats_text(self):
        """Retourne le texte des stats de l'arme."""
        weapon = WEAPONS[self.selected_weapon]
        return f"Dégâts: {weapon['damage']} | Portée: {weapon['range']} | Vitesse: {weapon['speed']}"

    def _select_class(self, class_name, index):
        """Sélectionne une classe."""
        self.selected_class = class_name
        # Mettre à jour les boutons
        for i, btn in enumerate(self.class_buttons):
            btn.color = color.azure if i == index else color.dark_gray
        # Mettre à jour la description et les stats
        self.class_desc.text = CHARACTER_CLASSES[class_name]["description"]
        self.class_stats.text = self._get_class_stats_text()
        # Mettre à jour l'arme par défaut de la classe
        default_weapon = CHARACTER_CLASSES[class_name]["starting_weapon"]
        weapon_idx = list(WEAPONS.keys()).index(default_weapon)
        self._select_weapon(default_weapon, weapon_idx)

    def _select_weapon(self, weapon_key, index):
        """Sélectionne une arme."""
        self.selected_weapon = weapon_key
        for i, btn in enumerate(self.weapon_buttons):
            btn.color = color.azure if i == index else color.dark_gray
        self.weapon_stats.text = self._get_weapon_stats_text()

    def _select_color(self, index):
        """Sélectionne une couleur."""
        self.selected_color_index = index
        for i, btn in enumerate(self.color_buttons):
            btn.scale = (0.07, 0.07) if i == index else (0.06, 0.06)
        # Mettre à jour la prévisualisation
        color_val = PLAYER_COLORS[index][1]
        self.preview_entity.color = color.rgb(
            int(color_val[0]*255),
            int(color_val[1]*255),
            int(color_val[2]*255)
        )

    def _on_back(self):
        """Retour au menu principal."""
        self.hide()
        self.on_back()

    def _on_confirm(self):
        """Confirme la création et lance le jeu."""
        # Récupérer le nom
        self.player_name = self.name_input.text if self.name_input.text else "Héros"

        # Créer la configuration du personnage
        character_config = {
            "name": self.player_name,
            "class": self.selected_class,
            "weapon": self.selected_weapon,
            "color": PLAYER_COLORS[self.selected_color_index][1],
            "stats": CHARACTER_CLASSES[self.selected_class].copy(),
        }

        self.hide()
        self.on_confirm(character_config)

    def hide(self):
        """Cache le menu."""
        self.visible = False
        for element in self.elements:
            element.enabled = False

    def show(self):
        """Affiche le menu."""
        self.visible = True
        for element in self.elements:
            element.enabled = True

    def destroy(self):
        """Détruit le menu."""
        for element in self.elements:
            destroy(element)
        self.elements.clear()


# ============================================================================
# GÉNÉRATEUR DE TEXTURES PROCÉDURALES
# ============================================================================

class TextureGenerator:
    """Génère des textures procédurales en mémoire pour Ursina."""
    
    @staticmethod
    def create_brick_texture(width: int = 64, height: int = 64) -> Texture:
        """Génère une texture de brique simple en pixel-art."""
        img = PNMImage(width, height)
        
        # Remplir de couleur de base brun-gris
        for y in range(height):
            for x in range(width):
                img.setXel(x, y, 0.6, 0.4, 0.3)
        
        # Ajouter des lignes de mortier
        for y in range(0, height, 8):
            for x in range(width):
                img.setXel(x, y, 0.4, 0.35, 0.3)
        
        for x in range(0, width, 16):
            for y in range(height):
                img.setXel(x, y, 0.4, 0.35, 0.3)
        
        # Ajouter des petits détails aléatoires
        rng = random.Random(42)
        for _ in range(200):
            x = rng.randint(0, width - 1)
            y = rng.randint(0, height - 1)
            variation = rng.uniform(0.5, 0.7)
            img.setXel(x, y, variation, variation * 0.8, variation * 0.6)
        
        texture = Texture("brick")
        texture.load(img)
        texture.set_magfilter(Texture.FT_nearest)
        texture.set_minfilter(Texture.FT_nearest)
        return texture
    
    @staticmethod
    def create_grass_texture(width: int = 64, height: int = 64) -> Texture:
        """Génère une texture d'herbe procédérale."""
        img = PNMImage(width, height)
        
        # Remplir de vert herbe
        for y in range(height):
            for x in range(width):
                img.setXel(x, y, 0.2, 0.5, 0.1)
        
        # Ajouter des variations d'herbe
        rng = random.Random(123)
        for y in range(height):
            for x in range(width):
                if rng.random() < 0.3:
                    variation = rng.uniform(0.15, 0.25)
                    img.setXel(x, y, variation, 0.4 + variation, variation * 0.5)
        
        texture = Texture("grass")
        texture.load(img)
        texture.set_magfilter(Texture.FT_nearest)
        texture.set_minfilter(Texture.FT_nearest)
        return texture
    
    @staticmethod
    def create_wood_texture(width: int = 64, height: int = 64) -> Texture:
        """Génère une texture de bois procédérale."""
        img = PNMImage(width, height)
        
        # Remplir de marron bois
        for y in range(height):
            for x in range(width):
                img.setXel(x, y, 0.4, 0.2, 0.1)
        
        # Ajouter des lignes de grain
        rng = random.Random(456)
        for y in range(height):
            darkness = rng.uniform(0.3, 0.5)
            for x in range(width):
                img.setXel(x, y, darkness, darkness * 0.6, darkness * 0.3)
        
        texture = Texture("wood")
        texture.load(img)
        texture.set_magfilter(Texture.FT_nearest)
        texture.set_minfilter(Texture.FT_nearest)
        return texture
    
    @staticmethod
    def create_sword_texture(width: int = 32, height: int = 128) -> Texture:
        """Génère une texture d'épée en pixel-art."""
        img = PNMImage(width, height)
        
        # Remplir de transparent (noir)
        for y in range(height):
            for x in range(width):
                img.setXel(x, y, 0, 0, 0)
        
        # Lame (gris acier)
        for y in range(30, 100):
            for x in range(8, 24):
                img.setXel(x, y, 0.7, 0.7, 0.8)
        
        # Point de la lame
        for y in range(95, 120):
            x_center = 16
            width_at_y = max(0, int(3 * (120 - y) / 25))
            for x in range(max(0, x_center - width_at_y), min(32, x_center + width_at_y)):
                img.setXel(x, y, 0.8, 0.8, 0.9)
        
        # Poignée (marron)
        for y in range(0, 30):
            for x in range(10, 22):
                img.setXel(x, y, 0.5, 0.3, 0.2)
        
        # Garde (or)
        for y in range(28, 32):
            for x in range(6, 26):
                img.setXel(x, y, 0.8, 0.7, 0.2)
        
        texture = Texture("sword")
        texture.load(img)
        texture.set_magfilter(Texture.FT_nearest)
        texture.set_minfilter(Texture.FT_nearest)
        return texture


# ============================================================================
# GÉNÉRATION DE NIVEAU
# ============================================================================

def generate_maze(width: int = 20, height: int = 20, seed: int = 42) -> List[List[int]]:
    """
    Génère un labyrinthe simple.
    0 = passage, 1 = mur
    """
    rng = random.Random(seed)
    maze = [[1 for _ in range(width)] for _ in range(height)]
    
    # Marcheur aléatoire
    x, y = width // 2, height // 2
    maze[y][x] = 0
    
    for _ in range(width * height * 2):
        dx, dy = rng.choice([(2, 0), (-2, 0), (0, 2), (0, -2)])
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            maze[y + dy // 2][x + dx // 2] = 0
            maze[ny][nx] = 0
            x, y = nx, ny
    
    return maze


# ============================================================================
# ENTITÉS DE JEU
# ============================================================================

class Wall(Entity):
    """Bloc de mur."""
    def __init__(self, position: Vec3, color_val: tuple = (0.6, 0.4, 0.3)):
        super().__init__(
            model="cube",
            color=color.rgb(int(color_val[0]*255), int(color_val[1]*255), int(color_val[2]*255)),
            collider="box",
            position=position,
            scale=(1, 2, 1),
        )


class Floor(Entity):
    """Sol du niveau."""
    def __init__(self, position: Vec3, color_val: tuple = (0.2, 0.5, 0.1)):
        super().__init__(
            model="cube",
            color=color.rgb(int(color_val[0]*255), int(color_val[1]*255), int(color_val[2]*255)),
            collider="box",
            position=position + Vec3(0, -1, 0),
            scale=(1, 0.1, 1),
        )


class Weapon(Entity):
    """Arme FPS attachée à la caméra avec animation d'attaque."""
    
    def __init__(self, texture: Texture):
        super().__init__(
            model="quad",
            color=color.rgb(200, 150, 100),  # Couleur or/bronze pour l'arme
            scale=(0.3, 1),
            position=Vec3(0.4, -0.3, -0.8),
            parent=camera.ui,
        )
        self.collider = None
        
        self.is_attacking = False
        self.attack_start_time = 0.0
        self.attack_duration = 0.3
        self.base_position = Vec3(0.4, -0.3, -0.8)
        self.swing_positions = [
            Vec3(0.25, 0.2, -0.5),  # Haut
            self.base_position,      # Bas (repos)
        ]
        self.current_swing_index = 0
    
    def attack(self) -> None:
        """Lance une animation d'attaque."""
        if not self.is_attacking:
            self.is_attacking = True
            self.attack_start_time = time.time()
            self.current_swing_index = 0
    
    def update(self) -> None:
        """Met à jour l'animation d'attaque."""
        if self.is_attacking:
            elapsed = time.time() - self.attack_start_time
            
            if elapsed < self.attack_duration:
                # Animation d'attaque
                start_pos = self.base_position
                end_pos = self.swing_positions[0]
                progress = elapsed / self.attack_duration
                self.position = start_pos + (end_pos - start_pos) * progress
            
            elif elapsed < self.attack_duration * 2:
                # Retour
                start_pos = self.swing_positions[0]
                end_pos = self.base_position
                progress = (elapsed - self.attack_duration) / self.attack_duration
                self.position = start_pos + (end_pos - start_pos) * progress
            
            else:
                # Fin de l'attaque
                self.position = self.base_position
                self.is_attacking = False


class Player(Entity):
    """Joueur FPS."""

    def __init__(self, position: Vec3, config: dict = None):
        super().__init__(
            collider="box",
            scale=(0.5, 1.8, 0.5),
            position=position + Vec3(0, 0.9, 0),
        )
        self.model = None

        # Appliquer la configuration du personnage
        if config:
            self.name = config.get("name", "Héros")
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
            self.name = "Héros"
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

        # Camera setup
        camera.parent = self
        camera.position = Vec3(0, 0.7, 0)
        camera.rotation = Vec3(0, 0, 0)
        mouse.locked = True
    
    def handle_input(self) -> None:
        """Traite l'input clavier/souris."""
        # Mouvement
        move = Vec3(0, 0, 0)
        forward = Vec3(
            math.sin(math.radians(self.yaw)),
            0,
            math.cos(math.radians(self.yaw))
        )
        right = Vec3(forward.z, 0, -forward.x)
        
        if held_keys["z"]:
            move += forward
        if held_keys["s"]:
            move -= forward
        if held_keys["q"]:
            move -= right
        if held_keys["d"]:
            move += right
        
        if move.length() > 0:
            move = move.normalized() * self.speed * time.dt
            self.position += move
        
        # Souris
        if mouse.locked:
            self.yaw -= mouse.velocity[0] * 30
            self.pitch -= mouse.velocity[1] * 30
            self.pitch = max(-89, min(89, self.pitch))
            
            self.rotation_y = self.yaw
            camera.rotation_x = self.pitch
    
    def raycast_attack(self, enemies: List[Entity]) -> bool:
        """Lance un raycast pour attaquer."""
        # Récupérer les stats de l'arme
        weapon_stats = WEAPONS.get(self.current_weapon, {"damage": 20, "range": 5})
        attack_range = weapon_stats["range"]
        base_damage = weapon_stats["damage"]

        hit_info = raycast(
            camera.world_position,
            camera.forward,
            distance=attack_range,
            ignore=[self],
        )

        if hit_info.hit and isinstance(hit_info.entity, Enemy):
            # Appliquer le bonus de dégâts de la classe
            final_damage = int(base_damage * self.damage_bonus)
            hit_info.entity.take_damage(final_damage)
            return True
        return False


class Enemy(Entity):
    """Ennemi simple."""
    
    def __init__(self, position: Vec3, color_base=color.red):
        super().__init__(
            model="cube",
            color=color_base,
            scale=(0.6, 1.8, 0.6),
            position=position + Vec3(0, 0.9, 0),
            collider="box",
        )
        self.health = 30
        self.speed = 2.0
        self.detection_range = 15.0
        self.state = "idle"
    
    def take_damage(self, damage: int):
        """Prend des dégâts."""
        self.health -= damage
        self.color = color.rgb(200, 100, 100)
        
        if self.health <= 0:
            destroy(self)
    
    def update_ai(self, player: Player):
        """Met à jour l'IA de l'ennemi."""
        to_player = player.position - self.position
        distance = to_player.length()
        
        if distance < self.detection_range:
            self.state = "chase"
            if distance > 1:
                direction = to_player.normalized()
                self.position += direction * self.speed * time.dt
                self.look_at(player.position)
        else:
            self.state = "idle"


# ============================================================================
# JEU PRINCIPAL
# ============================================================================

class Game:
    """Gestionnaire principal du jeu."""

    def __init__(self):
        # Générateurs
        self.texture_gen = TextureGenerator()
        self.textures = {
            "brick": self.texture_gen.create_brick_texture(),
            "grass": self.texture_gen.create_grass_texture(),
            "wood": self.texture_gen.create_wood_texture(),
            "sword": self.texture_gen.create_sword_texture(),
        }

        # État du jeu
        self.state = "menu"  # "menu", "customization", "playing"
        self.character_config = None

        # Menus
        self.main_menu = None
        self.customization_menu = None

        # Entités de jeu
        self.player = None
        self.weapon = None
        self.enemies: List[Enemy] = []
        self.walls: List[Wall] = []
        self.floors: List[Floor] = []

        # HUD
        self.hud_elements = []

        # Démarrer avec le menu principal
        self._show_main_menu()

    def _show_main_menu(self):
        """Affiche le menu principal."""
        self.state = "menu"
        mouse.locked = False

        if self.customization_menu:
            self.customization_menu.destroy()
            self.customization_menu = None

        self.main_menu = MainMenu(on_start_game=self._show_customization)

    def _show_customization(self):
        """Affiche le menu de personnalisation."""
        self.state = "customization"

        if self.main_menu:
            self.main_menu.destroy()
            self.main_menu = None

        self.customization_menu = CharacterCustomization(
            on_confirm=self._start_game,
            on_back=self._show_main_menu
        )

    def _start_game(self, character_config: dict):
        """Démarre le jeu avec la configuration du personnage."""
        self.state = "playing"
        self.character_config = character_config

        if self.customization_menu:
            self.customization_menu.destroy()
            self.customization_menu = None

        # Construire le monde et le joueur
        self._build_world()
        self._build_player(character_config)
        self._build_weapon(character_config)
        self._spawn_enemies()
        self._build_hud(character_config)

        mouse.locked = True

    def _build_world(self):
        """Construit le monde du jeu."""
        maze = generate_maze(20, 20)

        # Créer le monde 3D
        for y, row in enumerate(maze):
            for x, cell in enumerate(row):
                world_x = x - len(maze[0]) / 2
                world_z = y - len(maze) / 2

                if cell == 1:  # Mur
                    wall = Wall(
                        Vec3(world_x, 0, world_z),
                        (0.6, 0.4, 0.3)  # Couleur brique
                    )
                    self.walls.append(wall)
                else:  # Sol
                    floor = Floor(
                        Vec3(world_x, 0, world_z),
                        (0.2, 0.5, 0.1)  # Couleur herbe
                    )
                    self.floors.append(floor)

    def _build_player(self, config: dict):
        """Crée le joueur avec la configuration."""
        self.player = Player(Vec3(0, 0, 0), config)

    def _build_weapon(self, config: dict):
        """Crée l'arme selon la configuration."""
        self.weapon = Weapon(self.textures["sword"])
        # Ajuster la couleur de l'arme selon la couleur du joueur
        player_color = config.get("color", (1.0, 0.5, 0.3))
        self.weapon.color = color.rgb(
            int(player_color[0] * 200),
            int(player_color[1] * 150),
            int(player_color[2] * 100)
        )

    def _spawn_enemies(self):
        """Fait spawn des ennemis."""
        for _ in range(5):
            x = random.uniform(-8, 8)
            z = random.uniform(-8, 8)
            color_choice = random.choice([color.red, color.rgb(100, 50, 0)])
            enemy = Enemy(Vec3(x, 0, z), color_choice)
            self.enemies.append(enemy)

    def _build_hud(self, config: dict):
        """Crée le HUD avec les informations du personnage."""
        # Nom et classe du personnage
        name = config.get("name", "Héros")
        player_class = config.get("class", "Guerrier")
        player_color = config.get("color", (1.0, 0.2, 0.2))

        self.hud_name = Text(
            text=f"{name} - {player_class}",
            position=Vec2(-0.9, 0.48),
            origin=(0, 0),
            scale=1.2,
            color=color.rgb(
                int(player_color[0] * 255),
                int(player_color[1] * 255),
                int(player_color[2] * 255)
            ),
        )
        self.hud_elements.append(self.hud_name)

        # Barre de vie
        self.hud_health_bar_bg = Entity(
            parent=camera.ui,
            model='quad',
            color=color.dark_gray,
            position=(-0.7, 0.42),
            scale=(0.3, 0.03),
            origin=(-0.5, 0),
        )
        self.hud_elements.append(self.hud_health_bar_bg)

        self.hud_health_bar = Entity(
            parent=camera.ui,
            model='quad',
            color=color.red,
            position=(-0.7, 0.42),
            scale=(0.3, 0.025),
            origin=(-0.5, 0),
        )
        self.hud_elements.append(self.hud_health_bar)

        self.hud_health = Text(
            text=f"PV: {self.player.health}/{self.player.max_health}",
            position=Vec2(-0.9, 0.38),
            origin=(0, 0),
            scale=1.0,
            color=color.white,
        )
        self.hud_elements.append(self.hud_health)

        # Barre de mana (si mana > 0)
        if self.player.mana > 0:
            self.hud_mana_bar_bg = Entity(
                parent=camera.ui,
                model='quad',
                color=color.dark_gray,
                position=(-0.7, 0.34),
                scale=(0.2, 0.02),
                origin=(-0.5, 0),
            )
            self.hud_elements.append(self.hud_mana_bar_bg)

            self.hud_mana_bar = Entity(
                parent=camera.ui,
                model='quad',
                color=color.azure,
                position=(-0.7, 0.34),
                scale=(0.2, 0.015),
                origin=(-0.5, 0),
            )
            self.hud_elements.append(self.hud_mana_bar)

            self.hud_mana = Text(
                text=f"Mana: {self.player.mana}/{self.player.max_mana}",
                position=Vec2(-0.9, 0.30),
                origin=(0, 0),
                scale=0.9,
                color=color.cyan,
            )
            self.hud_elements.append(self.hud_mana)

        # Arme équipée
        weapon_name = WEAPONS.get(self.player.current_weapon, {}).get("name", "Arme")
        self.hud_weapon = Text(
            text=f"Arme: {weapon_name}",
            position=Vec2(-0.9, 0.22),
            origin=(0, 0),
            scale=1.0,
            color=color.yellow,
        )
        self.hud_elements.append(self.hud_weapon)

        # Compteur d'ennemis
        self.hud_enemies = Text(
            text="Ennemis: 5",
            position=Vec2(-0.9, 0.14),
            origin=(0, 0),
            scale=1.0,
            color=color.orange,
        )
        self.hud_elements.append(self.hud_enemies)

    def handle_input(self, key: str):
        """Traite l'input."""
        if self.state != "playing":
            return

        if key == "escape":
            mouse.locked = not mouse.locked

        if key == "left mouse down" and mouse.locked:
            self.weapon.attack()
            self.player.raycast_attack(self.enemies)

    def update(self):
        """Mise à jour du jeu."""
        if self.state != "playing":
            return

        if self.player is None or self.weapon is None:
            return

        # Joueur
        self.player.handle_input()

        # Arme
        self.weapon.update()

        # Ennemis
        for enemy in list(self.enemies):
            if hasattr(enemy, 'health') and hasattr(enemy, 'update_ai'):
                try:
                    enemy.update_ai(self.player)
                except Exception as e:
                    print(f"Erreur mise à jour ennemi: {e}")

        # Nettoyer les ennemis morts
        self.enemies = [e for e in self.enemies if hasattr(e, 'health') and e.health > 0]

        # Mise à jour du HUD
        self._update_hud()

    def _update_hud(self):
        """Met à jour l'affichage du HUD."""
        if not self.player:
            return

        # Barre de vie
        health_ratio = self.player.health / self.player.max_health
        self.hud_health_bar.scale_x = 0.3 * max(0, health_ratio)
        self.hud_health.text = f"PV: {self.player.health}/{self.player.max_health}"

        # Barre de mana
        if hasattr(self, 'hud_mana_bar') and self.player.max_mana > 0:
            mana_ratio = self.player.mana / self.player.max_mana
            self.hud_mana_bar.scale_x = 0.2 * max(0, mana_ratio)
            self.hud_mana.text = f"Mana: {self.player.mana}/{self.player.max_mana}"

        # Compteur d'ennemis
        self.hud_enemies.text = f"Ennemis: {len(self.enemies)}"


# ============================================================================
# LANCEMENT DU JEU
# ============================================================================

if __name__ == "__main__":
    app = Ursina(
        title="TES1: Arena - RPG Rétro",
    )

    game = Game()

    def update():
        game.update()

    def input(key):
        game.handle_input(key)

    app.run()


