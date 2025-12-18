"""
TES1: Arena - RPG FPS Retro
===========================
Un seul fichier avec:
- Menu de demarrage avec boutons fonctionnels
- Monde unifie: Village au depart + Donjon plus loin
- Combat FPS, ennemis, armes

Controles:
- ZQSD: Se deplacer
- Souris: Regarder
- Clic gauche / Espace: Attaquer
- 1/2/3: Changer d'arme
- Echap: Pause / Liberer souris

Lancement: python game.py
"""

from __future__ import annotations

import random
import math
from typing import List, Tuple, Optional

from ursina import (
    Ursina,
    Entity,
    Button,
    Text,
    camera,
    mouse,
    color,
    Vec3,
    Vec2,
    time,
    held_keys,
    raycast,
    destroy,
    application,
    window,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

WORLD_SIZE = 80  # Taille du monde
CELL_SIZE = 2.0

PLAYER_SPEED = 6.0
PLAYER_MOUSE_SENS = 40.0

ENEMY_SPEED = 2.5
ENEMY_DETECTION = 15.0

# Armes
WEAPONS = {
    "dagger": {"damage": 15, "fire_rate": 0.2, "color": color.rgb(200, 200, 150)},
    "sword": {"damage": 30, "fire_rate": 0.5, "color": color.rgb(220, 220, 180)},
    "axe": {"damage": 50, "fire_rate": 0.7, "color": color.rgb(150, 100, 50)},
}


# ============================================================================
# ENTITES DU JEU
# ============================================================================

class Grass(Entity):
    """Sol d'herbe"""
    def __init__(self, position: Vec3) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(34, 139, 34),
            collider=None,
            scale=(CELL_SIZE, 0.1, CELL_SIZE),
            position=position - Vec3(0, 0.45, 0),
        )


class Stone(Entity):
    """Bloc de pierre/mur"""
    def __init__(self, position: Vec3, height: float = 2.0) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(105, 105, 105),
            collider="box",
            scale=(CELL_SIZE, height, CELL_SIZE),
            position=position + Vec3(0, height / 2, 0),
        )


class DungeonWall(Entity):
    """Mur de donjon sombre"""
    def __init__(self, position: Vec3) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(40, 40, 50),
            collider="box",
            scale=(CELL_SIZE, CELL_SIZE * 1.5, CELL_SIZE),
            position=position + Vec3(0, CELL_SIZE * 0.75, 0),
        )


class DungeonFloor(Entity):
    """Sol de donjon"""
    def __init__(self, position: Vec3) -> None:
        super().__init__(
            model="cube",
            color=color.rgb(30, 30, 35),
            collider=None,
            scale=(CELL_SIZE, 0.1, CELL_SIZE),
            position=position - Vec3(0, 0.45, 0),
        )


class Tree(Entity):
    """Arbre"""
    def __init__(self, position: Vec3) -> None:
        # Tronc
        super().__init__(
            model="cube",
            color=color.rgb(90, 60, 30),
            collider="box",
            scale=(0.8, 3, 0.8),
            position=position + Vec3(0, 1.5, 0),
        )
        # Feuillage
        self.leaves = Entity(
            model="cube",
            color=color.rgb(34, 100, 34),
            collider=None,
            scale=(2.5, 2.5, 2.5),
            position=position + Vec3(0, 4, 0),
        )


class House(Entity):
    """Maison de village"""
    def __init__(self, position: Vec3) -> None:
        # Murs
        super().__init__(
            model="cube",
            color=color.rgb(180, 140, 100),
            collider="box",
            scale=(4, 3, 4),
            position=position + Vec3(0, 1.5, 0),
        )
        # Toit
        self.roof = Entity(
            model="cube",
            color=color.rgb(139, 69, 19),
            collider=None,
            scale=(4.5, 1, 4.5),
            position=position + Vec3(0, 3.5, 0),
        )


class Enemy(Entity):
    """Ennemi de base"""
    def __init__(self, position: Vec3, enemy_type: str = "goblin") -> None:
        colors = {
            "goblin": color.rgb(100, 150, 100),
            "orc": color.rgb(150, 60, 60),
            "skeleton": color.rgb(200, 200, 200),
            "troll": color.rgb(120, 80, 40),
        }
        base_color = colors.get(enemy_type, color.red)

        super().__init__(
            model="cube",
            color=base_color,
            collider="box",
            scale=(1, 2, 1),
            position=position + Vec3(0, 1, 0),
        )
        self.enemy_type = enemy_type
        self.hp = 30 if enemy_type != "troll" else 60
        self.max_hp = self.hp
        self.state = "idle"

    def take_damage(self, amount: int) -> None:
        self.hp -= amount
        self.color = color.rgb(255, 100, 100)
        if self.hp <= 0:
            destroy(self)


class Player(Entity):
    """Joueur FPS"""
    def __init__(self, start_pos: Vec3) -> None:
        super().__init__(
            model=None,
            collider="box",
            scale=(0.8, 2.0, 0.8),
            position=start_pos + Vec3(0, 1, 0),
        )
        self.health = 100
        self.yaw = 0.0
        self.pitch = 0.0

        # Armes
        self.current_weapon = "dagger"
        self.last_attack_time = 0.0

        # Arme visible
        self.weapon_model: Optional[Entity] = None

        # Setup camera
        camera.parent = self
        camera.position = Vec3(0, 0.8, 0)
        camera.rotation = Vec3(0, 0, 0)

        self._create_weapon_model()

    def _create_weapon_model(self) -> None:
        if self.weapon_model:
            destroy(self.weapon_model)

        weapon_data = WEAPONS[self.current_weapon]
        self.weapon_model = Entity(
            model="cube",
            color=weapon_data["color"],
            scale=(0.15, 0.6, 0.1),
            position=Vec3(0.35, -0.35, -0.45),
            parent=camera,
        )

    def handle_look(self) -> None:
        if not mouse.locked:
            return
        self.yaw -= mouse.velocity[0] * PLAYER_MOUSE_SENS
        self.pitch -= mouse.velocity[1] * PLAYER_MOUSE_SENS
        self.pitch = max(-89, min(89, self.pitch))

        self.rotation_y = self.yaw
        camera.rotation_x = self.pitch

    def handle_movement(self) -> None:
        move = Vec3(0, 0, 0)
        forward = Vec3(
            math.sin(math.radians(self.yaw)), 0, math.cos(math.radians(self.yaw))
        )
        right = Vec3(forward.z, 0, -forward.x)

        if held_keys["z"] or held_keys["w"]:
            move += forward
        if held_keys["s"]:
            move -= forward
        if held_keys["q"] or held_keys["a"]:
            move -= right
        if held_keys["d"]:
            move += right

        if move.length() > 0:
            move = move.normalized() * PLAYER_SPEED * time.dt
            self.position += move

    def attack(self, enemies: List[Enemy]) -> None:
        weapon_data = WEAPONS[self.current_weapon]
        time_since_last = time.time() - self.last_attack_time

        if time_since_last < weapon_data["fire_rate"]:
            return

        self.last_attack_time = time.time()

        # Animation simple
        if self.weapon_model:
            self.weapon_model.animate_position(
                Vec3(0.35, -0.1, -0.3), duration=0.1
            )
            self.weapon_model.animate_position(
                Vec3(0.35, -0.35, -0.45), duration=0.1, delay=0.1
            )

        # Raycast
        hit = raycast(
            camera.world_position,
            camera.forward,
            distance=5,
            ignore=[self],
        )
        if hit.hit and isinstance(hit.entity, Enemy):
            hit.entity.take_damage(weapon_data["damage"])

    def change_weapon(self, weapon_name: str) -> None:
        if weapon_name in WEAPONS:
            self.current_weapon = weapon_name
            self._create_weapon_model()


# ============================================================================
# GENERATION DU MONDE
# ============================================================================

def generate_unified_world(seed: int = 42) -> Tuple[List[List[int]], Tuple[int, int], Tuple[int, int]]:
    """
    Genere un monde unifie avec:
    - Zone de village au centre (spawn)
    - Zone de donjon plus loin (nord-est)

    Retourne: (grille, position_spawn, position_donjon)

    Legende:
    0 = herbe
    1 = mur/pierre
    2 = arbre
    3 = maison
    4 = mur donjon
    5 = sol donjon
    """
    rng = random.Random(seed)
    size = WORLD_SIZE
    grid = [[0 for _ in range(size)] for _ in range(size)]

    # === ZONE VILLAGE (centre) ===
    village_x, village_y = size // 2, size // 2
    village_radius = 12

    # Placer quelques maisons
    house_positions = []
    for _ in range(6):
        hx = village_x + rng.randint(-village_radius + 3, village_radius - 3)
        hy = village_y + rng.randint(-village_radius + 3, village_radius - 3)
        # Eviter le centre exact (spawn)
        if abs(hx - village_x) > 3 or abs(hy - village_y) > 3:
            house_positions.append((hx, hy))
            # Maison = bloc 3x3
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = hx + dx, hy + dy
                    if 0 <= nx < size and 0 <= ny < size:
                        grid[ny][nx] = 3

    # Arbres autour du village
    for _ in range(30):
        tx = village_x + rng.randint(-village_radius - 5, village_radius + 5)
        ty = village_y + rng.randint(-village_radius - 5, village_radius + 5)
        if 0 <= tx < size and 0 <= ty < size and grid[ty][tx] == 0:
            # Pas trop proche du spawn
            if abs(tx - village_x) > 4 or abs(ty - village_y) > 4:
                grid[ty][tx] = 2

    # === CHEMIN VERS LE DONJON ===
    dungeon_x, dungeon_y = size - 20, 20  # Nord-est

    # Tracer un chemin (nettoyer les obstacles)
    path_x, path_y = village_x, village_y
    while abs(path_x - dungeon_x) > 1 or abs(path_y - dungeon_y) > 1:
        if path_x < dungeon_x:
            path_x += 1
        elif path_x > dungeon_x:
            path_x -= 1
        if path_y > dungeon_y:
            path_y -= 1
        elif path_y < dungeon_y:
            path_y += 1

        # Nettoyer le chemin (largeur 3)
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = path_x + dx, path_y + dy
                if 0 <= nx < size and 0 <= ny < size:
                    if grid[ny][nx] in (1, 2):  # pierre ou arbre
                        grid[ny][nx] = 0

    # Obstacles naturels le long du chemin (rochers, arbres)
    for _ in range(50):
        ox = rng.randint(village_x, dungeon_x)
        oy = rng.randint(min(village_y, dungeon_y), max(village_y, dungeon_y))
        if 0 <= ox < size and 0 <= oy < size and grid[oy][ox] == 0:
            # Pas sur le chemin principal
            dist_to_path = min(abs(ox - village_x), abs(oy - village_y))
            if dist_to_path > 5:
                grid[oy][ox] = rng.choice([1, 2])  # pierre ou arbre

    # === ZONE DONJON ===
    dungeon_size = 20
    dungeon_rooms = generate_dungeon_layout(dungeon_size, dungeon_size, rng)

    # Integrer le donjon dans le monde
    for dy in range(dungeon_size):
        for dx in range(dungeon_size):
            world_x = dungeon_x - dungeon_size // 2 + dx
            world_y = dungeon_y - dungeon_size // 2 + dy
            if 0 <= world_x < size and 0 <= world_y < size:
                if dungeon_rooms[dy][dx] == 1:  # mur donjon
                    grid[world_y][world_x] = 4
                elif dungeon_rooms[dy][dx] == 0:  # sol donjon
                    grid[world_y][world_x] = 5

    # Entree du donjon (garantir l'acces)
    entry_x = dungeon_x - dungeon_size // 2
    entry_y = dungeon_y
    for i in range(3):
        if 0 <= entry_x - i < size and 0 <= entry_y < size:
            grid[entry_y][entry_x - i] = 0  # chemin vers l'entree

    return grid, (village_x, village_y), (dungeon_x, dungeon_y)


def generate_dungeon_layout(width: int, height: int, rng: random.Random) -> List[List[int]]:
    """
    Genere un layout de donjon simple (salles + couloirs).
    0 = sol, 1 = mur
    """
    # Tout en mur par defaut
    dungeon = [[1 for _ in range(width)] for _ in range(height)]

    # Creer des salles
    rooms = []
    for _ in range(8):
        rw = rng.randint(3, 6)
        rh = rng.randint(3, 5)
        rx = rng.randint(1, width - rw - 1)
        ry = rng.randint(1, height - rh - 1)

        # Verifier pas de chevauchement
        overlap = False
        for room in rooms:
            if (rx < room[0] + room[2] + 1 and rx + rw + 1 > room[0] and
                ry < room[1] + room[3] + 1 and ry + rh + 1 > room[1]):
                overlap = True
                break

        if not overlap:
            rooms.append((rx, ry, rw, rh))
            # Creuser la salle
            for y in range(ry, ry + rh):
                for x in range(rx, rx + rw):
                    dungeon[y][x] = 0

    # Connecter les salles
    for i in range(len(rooms) - 1):
        r1 = rooms[i]
        r2 = rooms[i + 1]
        c1x, c1y = r1[0] + r1[2] // 2, r1[1] + r1[3] // 2
        c2x, c2y = r2[0] + r2[2] // 2, r2[1] + r2[3] // 2

        # Couloir horizontal puis vertical
        x = c1x
        while x != c2x:
            if 0 <= x < width:
                dungeon[c1y][x] = 0
            x += 1 if c2x > c1x else -1

        y = c1y
        while y != c2y:
            if 0 <= y < height:
                dungeon[y][c2x] = 0
            y += 1 if c2y > c1y else -1

    return dungeon


def grid_to_world(x: int, y: int) -> Vec3:
    """Convertit coordonnees grille en position 3D"""
    wx = (x - WORLD_SIZE / 2) * CELL_SIZE
    wz = (y - WORLD_SIZE / 2) * CELL_SIZE
    return Vec3(wx, 0, wz)


# ============================================================================
# MENU PRINCIPAL
# ============================================================================

class MainMenu:
    """Menu principal avec boutons fonctionnels"""

    def __init__(self, on_start_game, on_quit):
        self.on_start_game = on_start_game
        self.on_quit = on_quit
        self.elements = []
        self._create_menu()

    def _create_menu(self):
        # Fond sombre
        self.bg = Entity(
            parent=camera.ui,
            model="quad",
            color=color.rgb(20, 20, 30),
            scale=(2, 1),
            z=1,
        )
        self.elements.append(self.bg)

        # Titre
        self.title = Text(
            text="TES1: ARENA",
            parent=camera.ui,
            position=(0, 0.35),
            origin=(0, 0),
            scale=3,
            color=color.gold,
        )
        self.elements.append(self.title)

        # Sous-titre
        self.subtitle = Text(
            text="RPG FPS Retro",
            parent=camera.ui,
            position=(0, 0.25),
            origin=(0, 0),
            scale=1.5,
            color=color.rgb(150, 150, 150),
        )
        self.elements.append(self.subtitle)

        # Bouton JOUER
        self.btn_play = Button(
            text="JOUER",
            parent=camera.ui,
            position=(0, 0.05),
            scale=(0.3, 0.08),
            color=color.rgb(50, 120, 50),
            highlight_color=color.rgb(70, 150, 70),
            pressed_color=color.rgb(30, 90, 30),
        )
        self.btn_play.on_click = self._on_play_click
        self.elements.append(self.btn_play)

        # Bouton QUITTER
        self.btn_quit = Button(
            text="QUITTER",
            parent=camera.ui,
            position=(0, -0.08),
            scale=(0.3, 0.08),
            color=color.rgb(120, 50, 50),
            highlight_color=color.rgb(150, 70, 70),
            pressed_color=color.rgb(90, 30, 30),
        )
        self.btn_quit.on_click = self._on_quit_click
        self.elements.append(self.btn_quit)

        # Instructions
        self.instructions = Text(
            text="Controles: ZQSD/WASD + Souris | Clic: Attaquer | 1/2/3: Armes",
            parent=camera.ui,
            position=(0, -0.25),
            origin=(0, 0),
            scale=0.8,
            color=color.rgb(100, 100, 100),
        )
        self.elements.append(self.instructions)

    def _on_play_click(self):
        self.hide()
        self.on_start_game()

    def _on_quit_click(self):
        self.on_quit()

    def hide(self):
        for elem in self.elements:
            destroy(elem)
        self.elements.clear()

    def show(self):
        if not self.elements:
            self._create_menu()


# ============================================================================
# JEU PRINCIPAL
# ============================================================================

class Game:
    """Gestionnaire principal du jeu"""

    def __init__(self):
        self.state = "menu"  # "menu", "playing", "paused"
        self.player: Optional[Player] = None
        self.enemies: List[Enemy] = []
        self.world_entities: List[Entity] = []
        self.hud_elements: List[Text] = []

        # Menu
        self.menu = MainMenu(
            on_start_game=self.start_game,
            on_quit=self.quit_game
        )

        mouse.locked = False

    def start_game(self):
        """Demarre une nouvelle partie"""
        self.state = "playing"
        mouse.locked = True

        # Generer le monde
        self._build_world()
        self._spawn_enemies()
        self._build_hud()

    def _build_world(self):
        """Construit le monde 3D"""
        grid, spawn_pos, dungeon_pos = generate_unified_world(seed=42)

        # Ciel
        sky = Entity(
            model="sphere",
            color=color.rgb(135, 206, 235),
            scale=500,
            double_sided=True,
        )
        self.world_entities.append(sky)

        # Soleil
        sun = Entity(
            model="sphere",
            color=color.rgb(255, 220, 100),
            scale=3,
            position=Vec3(100, 200, 100),
        )
        self.world_entities.append(sun)

        # Construire le terrain
        for y in range(WORLD_SIZE):
            for x in range(WORLD_SIZE):
                pos = grid_to_world(x, y)
                cell = grid[y][x]

                if cell == 0:  # Herbe
                    e = Grass(pos)
                    self.world_entities.append(e)
                elif cell == 1:  # Pierre
                    e = Stone(pos)
                    self.world_entities.append(e)
                elif cell == 2:  # Arbre
                    e = Grass(pos)  # Sol sous l'arbre
                    self.world_entities.append(e)
                    t = Tree(pos)
                    self.world_entities.append(t)
                    self.world_entities.append(t.leaves)
                elif cell == 3:  # Maison
                    h = House(pos)
                    self.world_entities.append(h)
                    self.world_entities.append(h.roof)
                elif cell == 4:  # Mur donjon
                    e = DungeonWall(pos)
                    self.world_entities.append(e)
                elif cell == 5:  # Sol donjon
                    e = DungeonFloor(pos)
                    self.world_entities.append(e)

        # Creer le joueur au spawn (village)
        spawn_world = grid_to_world(*spawn_pos)
        self.player = Player(spawn_world)

        # Stocker positions pour spawn ennemis
        self.free_cells = [
            (x, y) for y in range(WORLD_SIZE) for x in range(WORLD_SIZE)
            if grid[y][x] in (0, 5)  # herbe ou sol donjon
        ]
        self.grid = grid
        self.dungeon_pos = dungeon_pos

    def _spawn_enemies(self):
        """Fait apparaitre les ennemis"""
        rng = random.Random(123)

        # Ennemis dans la nature (goblins, orcs)
        for _ in range(8):
            if not self.free_cells:
                break
            cx, cy = rng.choice(self.free_cells)
            pos = grid_to_world(cx, cy)

            # Pas trop proche du spawn
            if self.player and (pos - self.player.position).length() < 15:
                continue

            enemy_type = rng.choice(["goblin", "orc"])
            e = Enemy(pos, enemy_type)
            self.enemies.append(e)

        # Ennemis dans le donjon (skeletons, trolls)
        dungeon_x, dungeon_y = self.dungeon_pos
        for _ in range(6):
            # Chercher une cellule dans le donjon
            for cx, cy in self.free_cells:
                if self.grid[cy][cx] == 5:  # sol donjon
                    pos = grid_to_world(cx, cy)
                    enemy_type = rng.choice(["skeleton", "troll"])
                    e = Enemy(pos, enemy_type)
                    self.enemies.append(e)
                    break

    def _build_hud(self):
        """Construit l'interface"""
        self.hud_health = Text(
            text="HP: 100",
            position=Vec2(-0.85, 0.45),
            origin=(0, 0),
            scale=1.2,
            color=color.red,
        )
        self.hud_elements.append(self.hud_health)

        self.hud_weapon = Text(
            text="Arme: Dague",
            position=Vec2(-0.85, 0.38),
            origin=(0, 0),
            scale=1.0,
            color=color.rgb(200, 200, 150),
        )
        self.hud_elements.append(self.hud_weapon)

        self.hud_enemies = Text(
            text="Ennemis: 0",
            position=Vec2(-0.85, 0.31),
            origin=(0, 0),
            scale=1.0,
            color=color.orange,
        )
        self.hud_elements.append(self.hud_enemies)

        self.hud_hint = Text(
            text="Direction du donjon: Nord-Est -->",
            position=Vec2(0, -0.45),
            origin=(0, 0),
            scale=0.9,
            color=color.rgb(100, 150, 200),
        )
        self.hud_elements.append(self.hud_hint)

    def handle_input(self, key: str):
        """Gere les entrees clavier"""
        if self.state == "menu":
            return

        if key == "escape":
            mouse.locked = not mouse.locked

        if key == "left mouse down" or key == "space":
            if self.player:
                self.player.attack(self.enemies)

        if key == "1":
            if self.player:
                self.player.change_weapon("dagger")
        elif key == "2":
            if self.player:
                self.player.change_weapon("sword")
        elif key == "3":
            if self.player:
                self.player.change_weapon("axe")

    def update(self):
        """Mise a jour du jeu"""
        if self.state != "playing" or not self.player:
            return

        # Joueur
        self.player.handle_look()
        self.player.handle_movement()

        # Ennemis IA
        for enemy in list(self.enemies):
            if not hasattr(enemy, "hp") or enemy.hp <= 0:
                continue

            to_player = self.player.position - enemy.position
            dist = to_player.length()

            if dist < ENEMY_DETECTION:
                enemy.state = "chase"
                if dist > 1.5:
                    direction = to_player.normalized()
                    enemy.position += direction * ENEMY_SPEED * time.dt
                    enemy.look_at(self.player.position)
            else:
                enemy.state = "idle"

        # Nettoyer ennemis morts
        self.enemies = [e for e in self.enemies if hasattr(e, "hp") and e.hp > 0]

        # Mettre a jour HUD
        self._update_hud()

    def _update_hud(self):
        """Met a jour l'interface"""
        if not self.player:
            return

        self.hud_health.text = f"HP: {self.player.health}"

        weapon_names = {"dagger": "Dague", "sword": "Epee", "axe": "Hache"}
        self.hud_weapon.text = f"Arme: {weapon_names[self.player.current_weapon]} (1/2/3)"

        self.hud_enemies.text = f"Ennemis: {len(self.enemies)}"

    def quit_game(self):
        """Quitte le jeu"""
        application.quit()


# ============================================================================
# POINT D'ENTREE
# ============================================================================

if __name__ == "__main__":
    app = Ursina(
        title="TES1: Arena - RPG Retro",
        borderless=False,
    )

    game = Game()

    def update():
        game.update()

    def input(key):
        game.handle_input(key)

    app.run()
