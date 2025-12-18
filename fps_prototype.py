"""
Prototype FPS rétro The Elder Scrolls 1 procédural avec Ursina.

Univers : Monde extérieur de fantasy médiévale avec ruines, villages et nature sauvage.

Fonctionnalités :
- Mouvement FPS : ZQSD + souris
- Caméra première personne
- Monde procédural (herbes, arbres, ruines, eau)
- Ciel dynamique avec soleil
- Ennemis (créatures de fantasy)
- Tir + dégâts
- HUD avec inventaire d'armes

Prérequis :
    pip install ursina

Lancement :
    python fps_prototype.py
"""

from __future__ import annotations

import random
import math
from typing import List, Tuple

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
)


# ---------------------------------------------------------------------------
# Paramètres de jeu
# ---------------------------------------------------------------------------

LEVEL_WIDTH = 64
LEVEL_HEIGHT = 64
CELL_SIZE = 2.0  # taille d'une case dans le monde 3D

PLAYER_MOVE_SPEED = 6.0
PLAYER_MOUSE_SENS = 40.0

ENEMY_MOVE_SPEED = 2.5
ENEMY_DETECTION_RANGE = 15.0


# Armes disponibles (style TES1)
WEAPONS = {
    "dagger": {"damage": 12, "ammo": 100, "fire_rate": 0.15, "color": color.rgb(200, 200, 150)},
    "sword": {"damage": 25, "ammo": 100, "fire_rate": 0.4, "color": color.rgb(220, 220, 180)},
    "axe": {"damage": 45, "ammo": 100, "fire_rate": 0.6, "color": color.rgb(150, 100, 50)},
}


# ---------------------------------------------------------------------------
# Génération procédurale de niveau (grille 2D -> murs/floors 3D)
# ---------------------------------------------------------------------------

def generate_level(
    width: int, height: int, rng: random.Random
) -> Tuple[List[List[int]], Tuple[int, int]]:
    """
    Génère une carte extérieure :
    - 0 = herbe (terrain accessible)
    - 1 = pierre/ruine (blocs solides)
    - 2 = eau (terrain bleu)
    - 3 = arbre (végétation dense)
    """
    grid = [[0 for _ in range(width)] for _ in range(height)]

    # Ajouter de l'herbe partout d'abord
    for y in range(height):
        for x in range(width):
            grid[y][x] = 0

    # Ajouter quelques ruines/rochers (carrés de pierre)
    for _ in range(15):
        rw = rng.randint(4, 10)
        rh = rng.randint(4, 10)
        rx = rng.randint(2, width - rw - 2)
        ry = rng.randint(2, height - rh - 2)
        for yy in range(ry, min(ry + rh, height)):
            for xx in range(rx, min(rx + rw, width)):
                grid[yy][xx] = 1

    # Ajouter de l'eau (petits lacs)
    for _ in range(6):
        cx = rng.randint(5, width - 5)
        cy = rng.randint(5, height - 5)
        for yy in range(cy - 2, cy + 3):
            for xx in range(cx - 2, cx + 3):
                if 0 <= xx < width and 0 <= yy < height:
                    grid[yy][xx] = 2

    # Ajouter des arbres (épars)
    for _ in range(40):
        tx = rng.randint(0, width - 1)
        ty = rng.randint(0, height - 1)
        if grid[ty][tx] == 0:  # Seulement sur l'herbe
            grid[ty][tx] = 3

    # Trouver une cellule de départ (herbe)
    start = (width // 2, height // 2)
    for radius in range(1, max(width, height)):
        found = None
        for yy in range(start[1] - radius, start[1] + radius + 1):
            for xx in range(start[0] - radius, start[0] + radius + 1):
                if 0 <= xx < width and 0 <= yy < height and grid[yy][xx] == 0:
                    found = (xx, yy)
                    break
            if found:
                break
        if found:
            start = found
            break

    return grid, start


def grid_to_world(x: int, y: int) -> Vec3:
    """
    Convertit des coordonnées de grille en position 3D (x,z).
    """
    wx = (x - LEVEL_WIDTH / 2) * CELL_SIZE
    wz = (y - LEVEL_HEIGHT / 2) * CELL_SIZE
    return Vec3(wx, 0, wz)


# ---------------------------------------------------------------------------
# Entités de jeu
# ---------------------------------------------------------------------------


class Grass(Entity):
    """Herbe du terrain"""
    def __init__(self, position: Vec3) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(34, 139, 34),  # Vert forêt
            collider=None,
            scale=(CELL_SIZE, 0.05, CELL_SIZE),
            position=position - Vec3(0, 0.475, 0),
        )


class Stone(Entity):
    """Pierre/Ruine (terrain solide)"""
    def __init__(self, position: Vec3) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(105, 105, 105),  # Gris pierre
            collider="box",
            scale=(CELL_SIZE, CELL_SIZE, CELL_SIZE),
            position=position + Vec3(0, CELL_SIZE / 2, 0),
        )


class Water(Entity):
    """Eau/Lacs"""
    def __init__(self, position: Vec3) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(64, 164, 223),  # Bleu eau
            collider="box",
            scale=(CELL_SIZE, 0.5, CELL_SIZE),
            position=position - Vec3(0, 0.25, 0),
        )


class Tree(Entity):
    """Arbre/Végétation"""
    def __init__(self, position: Vec3) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(34, 100, 34),  # Vert foncé (feuillage)
            collider="box",
            scale=(1.5, 4, 1.5),
            position=position + Vec3(0, 2, 0),
        )


class Hands(Entity):
    """Mains du joueur visibles en première personne"""
    def __init__(self, parent_camera) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(200, 170, 130),  # Couleur de peau
            collider=None,
            scale=(0.3, 0.4, 0.2),
            position=Vec3(0.25, -0.45, -0.5),  # Main droite
            parent=parent_camera,
        )
        
        # Seconde main (gauche)
        self.left_hand = Entity(
            model="cube",
            color=color.rgb(200, 170, 130),
            collider=None,
            scale=(0.3, 0.4, 0.2),
            position=Vec3(-0.25, -0.45, -0.5),  # Main gauche
            parent=parent_camera,
        )


class Wall(Entity):
    def __init__(self, position: Vec3) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(40, 40, 50),
            collider="box",
            scale=(CELL_SIZE, CELL_SIZE, CELL_SIZE),
            position=position + Vec3(0, CELL_SIZE / 2, 0),
        )


class Floor(Entity):
    def __init__(self, position: Vec3) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(20, 20, 25),
            collider=None,
            scale=(CELL_SIZE, 0.1, CELL_SIZE),
            position=position - Vec3(0, 0.45, 0),
        )


class Enemy(Entity):
    def __init__(self, position: Vec3, color_override=None, **kwargs) -> None:
        base_color = color_override if color_override is not None else color.red
        super().__init__(
            model="cube",
            color=base_color,
            collider="box",
            scale=(1, 2, 1),
            position=position + Vec3(0, 1, 0),
            **kwargs,
        )
        self.max_hp = 30
        self.hp = self.max_hp
        self.state = "idle"  # "idle" / "chase"

    def take_damage(self, amount: int) -> None:
        self.hp -= amount
        self.color = color.rgb(200, 80, 80)
        if self.hp <= 0:
            destroy(self)


class Player(Entity):
    def __init__(self, start_pos: Vec3) -> None:
        super().__init__(
            model=None,
            collider="box",
            scale=(0.8, 2.0, 0.8),
            position=start_pos + Vec3(0, 1, 0),
        )
        self.health = 100
        self.mana = 50
        self.yaw = 0.0
        self.pitch = 0.0

        # Inventaire et armes
        self.inventory = {
            "dagger": WEAPONS["dagger"]["ammo"],
            "sword": WEAPONS["sword"]["ammo"],
            "axe": WEAPONS["axe"]["ammo"],
        }
        self.current_weapon = "dagger"
        self.last_shot_time = 0.0
        
        # Mains visibles
        self.hands: Hands | None = None
        
        # Arme affichée en main
        self.weapon_model: Entity | None = None

        camera.parent = self
        camera.position = Vec3(0, 0.8, 0)
        camera.rotation = Vec3(0, 0, 0)

        mouse.locked = True
        
        # Créer les mains et l'arme après le setup de la caméra
        self._create_hands()
        self._create_weapon_model()

    def _create_hands(self) -> None:
        """Crée les mains visibles du joueur"""
        if self.hands is not None:
            destroy(self.hands)
            destroy(self.hands.left_hand)
        self.hands = Hands(camera)

    def _create_weapon_model(self) -> None:
        """Crée un modèle d'arme tenue en main."""
        if self.weapon_model is not None:
            destroy(self.weapon_model)
        
        weapon_data = WEAPONS[self.current_weapon]
        weapon_name = self.current_weapon.capitalize()
        
        # Arme tenue par la main droite
        self.weapon_model = Entity(
            model="cube",
            color=weapon_data["color"],
            scale=(0.15, 0.6, 0.1),  # Arme plus fine et allongée
            position=Vec3(0.35, -0.35, -0.45),  # Tenue dans la main droite
            parent=camera,
        )
        self.weapon_model.collider = None

    def handle_mouse_look(self) -> None:
        if not mouse.locked:
            return
        dx = mouse.velocity[0]
        dy = mouse.velocity[1]
        self.yaw -= dx * PLAYER_MOUSE_SENS
        self.pitch -= dy * PLAYER_MOUSE_SENS
        self.pitch = max(-89, min(89, self.pitch))

        self.rotation_y = self.yaw
        camera.rotation_x = self.pitch

    def handle_movement(self) -> None:
        # ZQSD en relatif à la direction de la caméra (XZ)
        move = Vec3(0, 0, 0)
        forward = Vec3(
            math.sin(math.radians(self.yaw)), 0, math.cos(math.radians(self.yaw))
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
            move = move.normalized() * PLAYER_MOVE_SPEED * time.dt
            self.position += move

    def shoot(self, enemies: List[Enemy]) -> None:
        current_ammo = self.inventory[self.current_weapon]
        if current_ammo <= 0:
            return
        
        # Vérifier le délai de tir
        time_since_last = time.time() - self.last_shot_time
        fire_rate = WEAPONS[self.current_weapon]["fire_rate"]
        if time_since_last < fire_rate:
            return
        
        self.last_shot_time = time.time()
        self.inventory[self.current_weapon] -= 1
        
        damage = WEAPONS[self.current_weapon]["damage"]
        
        # Raycast droit devant la caméra
        hit_info = raycast(
            camera.world_position,
            camera.forward,
            distance=30,
            ignore=[self],
        )
        if hit_info.hit:
            target = hit_info.entity
            if isinstance(target, Enemy):
                target.take_damage(damage)
    
    def change_weapon(self, weapon_name: str) -> None:
        """Change l'arme actuelle."""
        if weapon_name in WEAPONS and self.inventory[weapon_name] > 0:
            self.current_weapon = weapon_name
            self._create_weapon_model()


# ---------------------------------------------------------------------------
# Jeu principal (sans sous-classe d'Ursina : Ursina est un singleton)
# ---------------------------------------------------------------------------


class Game:
    def __init__(self, seed: int = 1337) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

        self.player: Player
        self.enemies: List[Enemy] = []

        self.hud_health: Text
        self.hud_mana: Text
        self.hud_ammo: Text
        self.hud_weapon: Text

        self._build_level()
        self._spawn_enemies()
        self._build_hud()

    # ----- Construction ---------------------------------------------------

    def _build_level(self) -> None:
        grid, start_cell = generate_level(LEVEL_WIDTH, LEVEL_HEIGHT, self.rng)

        # Ajouter un ciel
        sky = Entity(
            model="sphere",
            color=color.rgb(135, 206, 235),  # Bleu ciel
            scale=1000,
            double_sided=True,
        )

        # Ajouter un soleil lointain
        sun = Entity(
            model="sphere",
            color=color.rgb(255, 220, 0),  # Jaune doré
            scale=2,  # Soleil petit et lointain
            position=Vec3(200, 300, 200),
        )

        # Construire le terrain
        for y in range(LEVEL_HEIGHT):
            for x in range(LEVEL_WIDTH):
                pos = grid_to_world(x, y)
                terrain_type = grid[y][x]
                
                if terrain_type == 1:  # Pierre/Ruine
                    Stone(position=pos)
                elif terrain_type == 2:  # Eau
                    Water(position=pos)
                elif terrain_type == 3:  # Arbre
                    Tree(position=pos)
                else:  # Herbe (terrain par défaut)
                    Grass(position=pos)

        start_pos = grid_to_world(*start_cell)
        self.player = Player(start_pos=start_pos)

        # Marquer les cellules d'herbe pour placer des ennemis
        self.free_cells: List[Tuple[int, int]] = [
            (x, y) for y in range(LEVEL_HEIGHT) for x in range(LEVEL_WIDTH) if grid[y][x] == 0
        ]

    def _spawn_enemies(self) -> None:
        enemy_count = 12
        for _ in range(enemy_count):
            if not self.free_cells:
                break
            cx, cy = self.rng.choice(self.free_cells)
            pos = grid_to_world(cx, cy)
            # éviter spawn trop proche du joueur
            if (pos - self.player.position).length() < 10:
                continue
            
            # Ennemis de fantasy : gobelin (vert), orc (rouge), troll (brun)
            enemy_types = [
                ("Goblin", color.rgb(100, 150, 100)),
                ("Orc", color.rgb(150, 60, 60)),
                ("Troll", color.rgb(120, 80, 40)),
            ]
            enemy_name, enemy_color = self.rng.choice(enemy_types)
            
            e = Enemy(position=pos, color_override=enemy_color)
            self.enemies.append(e)

    def _build_hud(self) -> None:
        self.hud_health = Text(
            text="HP: 100",
            position=Vec2(-0.85, 0.45),
            origin=(0, 0),
            scale=1.1,
            color=color.red,
        )
        self.hud_mana = Text(
            text="Mana: 50",
            position=Vec2(-0.85, 0.38),
            origin=(0, 0),
            scale=0.9,
            color=color.azure,
        )
        self.hud_ammo = Text(
            text="Ammo: 60",
            position=Vec2(-0.85, 0.31),
            origin=(0, 0),
            scale=0.9,
            color=color.yellow,
        )
        self.hud_weapon = Text(
            text="Weapon: Dagger (1/2/3)",
            position=Vec2(-0.85, 0.24),
            origin=(0, 0),
            scale=0.9,
            color=color.rgb(200, 200, 150),
        )

    # ----- Boucles de jeu -------------------------------------------------

    def input(self, key: str) -> None:
        # Souris relâchée / re-lock
        if key == "escape":
            mouse.locked = not mouse.locked

        # Tir (clic gauche ou touche espace)
        if key == "left mouse down" or key == "space":
            self.player.shoot(self.enemies)
        
        # Changement d'armes (style TES)
        if key == "1":
            self.player.change_weapon("dagger")
        elif key == "2":
            self.player.change_weapon("sword")
        elif key == "3":
            self.player.change_weapon("axe")

    def update(self) -> None:
        # Caméra + mouvement
        self.player.handle_mouse_look()
        self.player.handle_movement()

        # IA ennemis
        self._update_enemies()

        # Mise à jour HUD
        self._update_hud()

    def _update_enemies(self) -> None:
        for e in list(self.enemies):
            # Si l'ennemi a été détruit, ignorer (hp n'existe plus)
            if not hasattr(e, "hp") or e.hp <= 0:
                continue

            to_player = self.player.position - e.position
            dist = to_player.length()
            if dist < ENEMY_DETECTION_RANGE:
                e.state = "chase"
            else:
                e.state = "idle"

            if e.state == "chase" and dist > 0.5:
                direction = to_player.normalized()
                e.position += direction * ENEMY_MOVE_SPEED * time.dt
                e.look_at(self.player.position)

    def _update_hud(self) -> None:
        self.hud_health.text = f"HP: {self.player.health}"
        self.hud_mana.text = f"Mana: {self.player.mana}"
        
        weapon_name = self.player.current_weapon.capitalize()
        weapon_ammo = self.player.inventory[self.player.current_weapon]
        self.hud_ammo.text = f"Ammo: {weapon_ammo}"
        self.hud_weapon.text = f"Weapon: {weapon_name} (1/2/3)"

if __name__ == "__main__":
    # Ursina est un singleton : on crée l'instance globale ici
    app = Ursina()

    # Instance de jeu qui contient toute la logique
    game = Game(seed=1337)

    # Fonctions globales que l'engine va appeler chaque frame / input
    def update() -> None:  # type: ignore[override]
        game.update()

    def input(key: str) -> None:  # type: ignore[override]
        game.input(key)

    app.run()



