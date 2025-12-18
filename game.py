"""
TES1: Arena - RPG FPS Retro
===========================

Lancement: python game.py
Prerequis: pip install ursina

Controles:
- ZQSD ou WASD: Se deplacer
- Souris: Regarder
- Clic gauche: Attaquer
- 1/2/3: Changer d'arme
- Echap: Liberer/Bloquer souris
"""

from ursina import *
import random
import math

# ============================================================================
# JEU
# ============================================================================

app = Ursina(title="TES1: Arena", borderless=False)

# Variables globales
game_started = False
player = None
enemies = []
hud_elements = []

# ============================================================================
# MENU PRINCIPAL
# ============================================================================

menu_bg = Entity(
    parent=camera.ui,
    model="quad",
    color=color.rgb(20, 20, 35),
    scale=(2, 1),
    z=0.1,
)

menu_title = Text(
    text="TES1: ARENA",
    parent=camera.ui,
    position=(0, 0.35),
    origin=(0, 0),
    scale=3,
    color=color.gold,
)

menu_subtitle = Text(
    text="RPG FPS Retro - Village & Donjon",
    parent=camera.ui,
    position=(0, 0.25),
    origin=(0, 0),
    scale=1.2,
    color=color.light_gray,
)

btn_play = Button(
    text="JOUER",
    parent=camera.ui,
    position=(0, 0.05),
    scale=(0.25, 0.07),
    color=color.rgb(40, 100, 40),
    highlight_color=color.rgb(60, 140, 60),
)

btn_quit = Button(
    text="QUITTER",
    parent=camera.ui,
    position=(0, -0.05),
    scale=(0.25, 0.07),
    color=color.rgb(100, 40, 40),
    highlight_color=color.rgb(140, 60, 60),
)

menu_controls = Text(
    text="ZQSD/WASD: Bouger | Souris: Regarder | Clic: Attaquer | 1-2-3: Armes",
    parent=camera.ui,
    position=(0, -0.2),
    origin=(0, 0),
    scale=0.8,
    color=color.gray,
)

menu_elements = [menu_bg, menu_title, menu_subtitle, btn_play, btn_quit, menu_controls]


def hide_menu():
    for elem in menu_elements:
        elem.enabled = False


def show_menu():
    for elem in menu_elements:
        elem.enabled = True


# ============================================================================
# CLASSES DU JEU
# ============================================================================

class Player(Entity):
    def __init__(self, pos):
        super().__init__(
            position=pos + Vec3(0, 1, 0),
            collider="box",
            scale=(0.8, 2, 0.8),
        )
        self.speed = 6
        self.health = 100
        self.yaw = 0
        self.pitch = 0
        self.weapon = "dague"
        self.weapons = {
            "dague": {"damage": 15, "cooldown": 0.2, "color": color.rgb(200, 200, 150)},
            "epee": {"damage": 30, "cooldown": 0.4, "color": color.rgb(180, 180, 200)},
            "hache": {"damage": 50, "cooldown": 0.6, "color": color.rgb(150, 100, 50)},
        }
        self.last_attack = 0

        camera.parent = self
        camera.position = (0, 0.8, 0)
        camera.rotation = (0, 0, 0)

        # Arme visible
        self.weapon_model = Entity(
            parent=camera,
            model="cube",
            color=self.weapons[self.weapon]["color"],
            scale=(0.1, 0.5, 0.1),
            position=(0.3, -0.3, 0.5),
        )

    def update(self):
        if not game_started:
            return

        # Souris
        if mouse.locked:
            self.yaw -= mouse.velocity[0] * 40
            self.pitch -= mouse.velocity[1] * 40
            self.pitch = clamp(self.pitch, -89, 89)
            self.rotation_y = self.yaw
            camera.rotation_x = self.pitch

        # Deplacement
        direction = Vec3(0, 0, 0)
        forward = Vec3(math.sin(math.radians(self.yaw)), 0, math.cos(math.radians(self.yaw)))
        right = Vec3(forward.z, 0, -forward.x)

        if held_keys["z"] or held_keys["w"]:
            direction += forward
        if held_keys["s"]:
            direction -= forward
        if held_keys["q"] or held_keys["a"]:
            direction -= right
        if held_keys["d"]:
            direction += right

        if direction.length() > 0:
            direction = direction.normalized()
            self.position += direction * self.speed * time.dt

    def attack(self):
        weapon_data = self.weapons[self.weapon]
        if time.time() - self.last_attack < weapon_data["cooldown"]:
            return

        self.last_attack = time.time()

        # Animation
        self.weapon_model.animate_position((0.3, 0, 0.3), duration=0.1)
        self.weapon_model.animate_position((0.3, -0.3, 0.5), duration=0.1, delay=0.1)

        # Raycast
        hit = raycast(camera.world_position, camera.forward, distance=4, ignore=[self])
        if hit.hit and hasattr(hit.entity, "take_damage"):
            hit.entity.take_damage(weapon_data["damage"])

    def change_weapon(self, name):
        if name in self.weapons:
            self.weapon = name
            self.weapon_model.color = self.weapons[name]["color"]


class Enemy(Entity):
    def __init__(self, pos, enemy_type="goblin"):
        types = {
            "goblin": {"color": color.rgb(80, 140, 80), "hp": 30},
            "orc": {"color": color.rgb(140, 60, 60), "hp": 40},
            "squelette": {"color": color.rgb(200, 200, 190), "hp": 25},
            "troll": {"color": color.rgb(100, 70, 50), "hp": 70},
        }
        data = types.get(enemy_type, types["goblin"])

        super().__init__(
            model="cube",
            color=data["color"],
            position=pos + Vec3(0, 1, 0),
            scale=(1, 2, 1),
            collider="box",
        )
        self.hp = data["hp"]
        self.speed = 2.5
        self.enemy_type = enemy_type

    def update(self):
        if not game_started or not player:
            return

        to_player = player.position - self.position
        dist = to_player.length()

        if dist < 15 and dist > 1.5:
            direction = Vec3(to_player.x, 0, to_player.z).normalized()
            self.position += direction * self.speed * time.dt
            self.look_at(player.position)

    def take_damage(self, amount):
        self.hp -= amount
        self.color = color.white
        invoke(self.reset_color, delay=0.1)

        if self.hp <= 0:
            if self in enemies:
                enemies.remove(self)
            destroy(self)

    def reset_color(self):
        types = {
            "goblin": color.rgb(80, 140, 80),
            "orc": color.rgb(140, 60, 60),
            "squelette": color.rgb(200, 200, 190),
            "troll": color.rgb(100, 70, 50),
        }
        if hasattr(self, "color"):
            self.color = types.get(self.enemy_type, color.red)


# ============================================================================
# GENERATION DU MONDE
# ============================================================================

def create_world():
    global player, enemies

    rng = random.Random(42)
    world_size = 60

    # Ciel
    Entity(model="sphere", scale=400, color=color.rgb(100, 180, 255), double_sided=True)

    # Sol principal (herbe)
    Entity(
        model="cube",
        scale=(world_size * 2, 0.1, world_size * 2),
        color=color.rgb(40, 120, 40),
        position=(0, -0.05, 0),
        collider="box",
    )

    # === VILLAGE AU CENTRE ===
    village_x, village_z = 0, 0

    # Maisons du village
    house_positions = [(-8, -5), (-8, 5), (8, -5), (8, 5), (0, 10), (0, -10)]
    for hx, hz in house_positions:
        # Murs maison
        Entity(
            model="cube",
            color=color.rgb(160, 120, 80),
            position=(village_x + hx, 1.5, village_z + hz),
            scale=(4, 3, 4),
            collider="box",
        )
        # Toit
        Entity(
            model="cube",
            color=color.rgb(120, 60, 30),
            position=(village_x + hx, 3.2, village_z + hz),
            scale=(4.5, 0.8, 4.5),
        )

    # Arbres autour du village
    for _ in range(25):
        tx = rng.randint(-25, 25)
        tz = rng.randint(-25, 25)
        if abs(tx) > 12 or abs(tz) > 12:  # Pas dans le village
            # Tronc
            Entity(
                model="cube",
                color=color.rgb(80, 50, 30),
                position=(tx, 1.5, tz),
                scale=(0.8, 3, 0.8),
                collider="box",
            )
            # Feuillage
            Entity(
                model="cube",
                color=color.rgb(30, 90, 30),
                position=(tx, 4, tz),
                scale=(2.5, 2.5, 2.5),
            )

    # === DONJON AU NORD-EST ===
    donjon_x, donjon_z = 40, -35
    donjon_size = 20

    # Sol du donjon (sombre)
    Entity(
        model="cube",
        scale=(donjon_size, 0.2, donjon_size),
        color=color.rgb(30, 30, 40),
        position=(donjon_x, 0, donjon_z),
    )

    # Murs du donjon (contour)
    wall_color = color.rgb(50, 50, 60)
    for i in range(donjon_size // 2 + 1):
        offset = i * 2 - donjon_size // 2
        # Mur nord
        Entity(model="cube", color=wall_color, position=(donjon_x + offset, 1.5, donjon_z - donjon_size//2), scale=(2, 3, 2), collider="box")
        # Mur sud
        Entity(model="cube", color=wall_color, position=(donjon_x + offset, 1.5, donjon_z + donjon_size//2), scale=(2, 3, 2), collider="box")
        # Mur est
        Entity(model="cube", color=wall_color, position=(donjon_x + donjon_size//2, 1.5, donjon_z + offset), scale=(2, 3, 2), collider="box")
        # Mur ouest (avec ouverture au centre pour entree)
        if abs(offset) > 2:
            Entity(model="cube", color=wall_color, position=(donjon_x - donjon_size//2, 1.5, donjon_z + offset), scale=(2, 3, 2), collider="box")

    # Piliers interieurs du donjon
    for px, pz in [(35, -40), (45, -40), (35, -30), (45, -30)]:
        Entity(model="cube", color=color.rgb(60, 60, 70), position=(px, 2, pz), scale=(1.5, 4, 1.5), collider="box")

    # === CHEMIN VILLAGE -> DONJON ===
    # Rochers le long du chemin
    for i in range(8):
        rx = 5 + i * 5
        rz = -5 - i * 4
        if rng.random() > 0.3:
            Entity(
                model="cube",
                color=color.rgb(90, 90, 90),
                position=(rx + rng.randint(-3, 3), 0.5, rz + rng.randint(-3, 3)),
                scale=(rng.uniform(1, 2), rng.uniform(1, 2), rng.uniform(1, 2)),
                collider="box",
            )

    # === JOUEUR ===
    player = Player(Vec3(0, 0, 0))

    # === ENNEMIS ===
    enemies.clear()

    # Ennemis dans la nature
    nature_enemies = [
        (15, 15, "goblin"), (-15, 20, "goblin"), (20, -10, "orc"),
        (-20, -15, "orc"), (25, 5, "goblin"), (-10, 25, "goblin"),
    ]
    for ex, ez, etype in nature_enemies:
        e = Enemy(Vec3(ex, 0, ez), etype)
        enemies.append(e)

    # Ennemis dans le donjon
    donjon_enemies = [
        (35, -35, "squelette"), (45, -35, "squelette"),
        (40, -40, "squelette"), (40, -30, "troll"),
    ]
    for ex, ez, etype in donjon_enemies:
        e = Enemy(Vec3(ex, 0, ez), etype)
        enemies.append(e)

    # === HUD ===
    global hud_hp, hud_weapon, hud_enemies, hud_hint

    hud_hp = Text(text="HP: 100", position=(-0.85, 0.45), scale=1.5, color=color.red)
    hud_weapon = Text(text="Arme: Dague (1/2/3)", position=(-0.85, 0.38), scale=1, color=color.rgb(200, 200, 150))
    hud_enemies = Text(text="Ennemis: 10", position=(-0.85, 0.31), scale=1, color=color.orange)
    hud_hint = Text(text="Donjon: Nord-Est -->", position=(0, -0.45), origin=(0, 0), scale=1, color=color.rgb(100, 150, 200))


# ============================================================================
# FONCTIONS DU JEU
# ============================================================================

def start_game():
    global game_started
    hide_menu()
    create_world()
    mouse.locked = True
    game_started = True


def quit_game():
    application.quit()


btn_play.on_click = start_game
btn_quit.on_click = quit_game


def update():
    if not game_started:
        return

    # Update HUD
    if player:
        hud_hp.text = f"HP: {player.health}"
        weapon_names = {"dague": "Dague", "epee": "Epee", "hache": "Hache"}
        hud_weapon.text = f"Arme: {weapon_names[player.weapon]} (1/2/3)"

    hud_enemies.text = f"Ennemis: {len(enemies)}"


def input(key):
    global game_started

    if not game_started:
        return

    if key == "escape":
        mouse.locked = not mouse.locked

    if key == "left mouse down":
        if player:
            player.attack()

    if key == "1" and player:
        player.change_weapon("dague")
    if key == "2" and player:
        player.change_weapon("epee")
    if key == "3" and player:
        player.change_weapon("hache")


# ============================================================================
# LANCEMENT
# ============================================================================

mouse.locked = False
app.run()
