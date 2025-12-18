"""
TES1: Arena - RPG FPS Retro
===========================

Lancement: python game.py
Prerequis: pip install ursina

Controles:
- ZQSD/WASD: Se deplacer
- Souris: Regarder
- Clic gauche: Attaquer
- 1/2/3/4: Changer d'arme
- E: Interagir avec PNJ
- TAB: Afficher/Cacher inventaire
- Molette: Changer d'arme
- Echap: Menu pause
"""

from ursina import *
from ursina.shaders import lit_with_shadows_shader
import random
import math

# ============================================================================
# INITIALISATION
# ============================================================================

app = Ursina(title="TES1: Arena", borderless=False, fullscreen=False)
window.color = color.rgb(20, 20, 30)

# Variables globales
game_started = False
player = None
enemies = []
npcs = []
world_entities = []

# ============================================================================
# CLASSES - ARMES
# ============================================================================

class Weapon:
    """Definition d'une arme"""
    def __init__(self, name, damage, cooldown, reach, weapon_color, blade_scale, handle_scale):
        self.name = name
        self.damage = damage
        self.cooldown = cooldown
        self.reach = reach
        self.weapon_color = weapon_color
        self.blade_scale = blade_scale
        self.handle_scale = handle_scale


WEAPONS_DATA = {
    "dague": Weapon("Dague", 12, 0.15, 2.5, color.rgb(180, 180, 190), (0.04, 0.25, 0.02), (0.03, 0.1, 0.03)),
    "epee": Weapon("Epee", 25, 0.35, 3.5, color.rgb(200, 200, 210), (0.05, 0.5, 0.02), (0.04, 0.15, 0.04)),
    "hache": Weapon("Hache", 40, 0.5, 3.0, color.rgb(100, 100, 110), (0.15, 0.2, 0.03), (0.04, 0.35, 0.04)),
    "masse": Weapon("Masse", 55, 0.7, 2.8, color.rgb(80, 70, 60), (0.1, 0.12, 0.1), (0.04, 0.4, 0.04)),
}


# ============================================================================
# CLASSES - ARME EN MAIN (VISUEL FPS)
# ============================================================================

class WeaponModel(Entity):
    """Modele 3D de l'arme en main du joueur"""
    def __init__(self):
        super().__init__(parent=camera)
        self.current_weapon = "dague"
        self.is_attacking = False
        self.base_pos = Vec3(0.35, -0.25, 0.5)
        self.base_rot = Vec3(0, -10, -5)

        # Main du joueur
        self.hand = Entity(
            parent=self,
            model="cube",
            color=color.rgb(220, 180, 150),
            scale=(0.08, 0.12, 0.15),
            position=self.base_pos + Vec3(0, -0.05, 0),
        )

        # Manche de l'arme
        self.handle = Entity(
            parent=self,
            model="cube",
            color=color.rgb(101, 67, 33),
            scale=WEAPONS_DATA[self.current_weapon].handle_scale,
            position=self.base_pos,
        )

        # Lame/tete de l'arme
        self.blade = Entity(
            parent=self,
            model="cube",
            color=WEAPONS_DATA[self.current_weapon].weapon_color,
            scale=WEAPONS_DATA[self.current_weapon].blade_scale,
            position=self.base_pos + Vec3(0, 0.2, 0),
        )

        self.position = Vec3(0, 0, 0)
        self.rotation = self.base_rot

    def set_weapon(self, weapon_name):
        if weapon_name not in WEAPONS_DATA:
            return
        self.current_weapon = weapon_name
        data = WEAPONS_DATA[weapon_name]
        self.blade.color = data.weapon_color
        self.blade.scale = data.blade_scale
        self.handle.scale = data.handle_scale

        # Ajuster position de la lame selon l'arme
        if weapon_name == "hache":
            self.blade.position = self.base_pos + Vec3(0.05, 0.25, 0)
        elif weapon_name == "masse":
            self.blade.position = self.base_pos + Vec3(0, 0.3, 0)
        else:
            self.blade.position = self.base_pos + Vec3(0, 0.2, 0)

    def attack_animation(self):
        if self.is_attacking:
            return
        self.is_attacking = True

        # Animation de frappe
        self.animate_rotation(Vec3(-45, -10, -5), duration=0.1)
        self.animate_position(Vec3(0, 0.1, -0.1), duration=0.1)

        invoke(self.reset_position, delay=0.15)

    def reset_position(self):
        self.animate_rotation(self.base_rot, duration=0.1)
        self.animate_position(Vec3(0, 0, 0), duration=0.1)
        invoke(setattr, self, 'is_attacking', False, delay=0.1)

    def idle_animation(self):
        """Leger mouvement de respiration"""
        if not self.is_attacking:
            offset = math.sin(time.time() * 2) * 0.005
            self.hand.y = self.base_pos.y - 0.05 + offset
            self.handle.y = self.base_pos.y + offset
            self.blade.y = self.blade.position.y + offset * 0.5


# ============================================================================
# CLASSES - PNJ
# ============================================================================

class NPC(Entity):
    """Personnage non-joueur"""
    def __init__(self, pos, npc_name, dialogue):
        super().__init__(
            model="cube",
            color=color.rgb(200, 160, 120),
            position=pos + Vec3(0, 1, 0),
            scale=(0.8, 1.8, 0.5),
            collider="box",
        )
        self.npc_name = npc_name
        self.dialogue = dialogue
        self.is_talking = False

        # Tete
        self.head = Entity(
            parent=self,
            model="cube",
            color=color.rgb(220, 180, 150),
            scale=(0.6, 0.5, 0.5),
            position=(0, 0.7, 0),
        )

        # Cheveux
        hair_color = random.choice([
            color.rgb(60, 40, 20),
            color.rgb(180, 140, 80),
            color.rgb(40, 30, 20),
            color.rgb(150, 80, 50),
        ])
        self.hair = Entity(
            parent=self,
            model="cube",
            color=hair_color,
            scale=(0.65, 0.25, 0.55),
            position=(0, 1, 0),
        )

        # Nom au-dessus
        self.name_tag = Text(
            text=npc_name,
            parent=self,
            y=1.5,
            scale=8,
            origin=(0, 0),
            billboard=True,
            color=color.white,
        )

    def interact(self):
        return self.dialogue


# ============================================================================
# CLASSES - MAISON AVEC INTERIEUR
# ============================================================================

class House:
    """Maison avec interieur accessible"""
    def __init__(self, pos, size=6, has_npc=True):
        self.pos = pos
        self.size = size
        self.entities = []
        self.npc = None

        wall_height = 3
        wall_thickness = 0.3
        wall_color = color.rgb(160, 120, 80)
        floor_color = color.rgb(120, 80, 50)
        roof_color = color.rgb(100, 50, 25)

        # Sol interieur
        floor = Entity(
            model="cube",
            color=floor_color,
            position=pos + Vec3(0, 0.05, 0),
            scale=(size, 0.1, size),
        )
        self.entities.append(floor)

        # Mur arriere
        back_wall = Entity(
            model="cube",
            color=wall_color,
            position=pos + Vec3(0, wall_height/2, -size/2 + wall_thickness/2),
            scale=(size, wall_height, wall_thickness),
            collider="box",
        )
        self.entities.append(back_wall)

        # Mur gauche
        left_wall = Entity(
            model="cube",
            color=wall_color,
            position=pos + Vec3(-size/2 + wall_thickness/2, wall_height/2, 0),
            scale=(wall_thickness, wall_height, size),
            collider="box",
        )
        self.entities.append(left_wall)

        # Mur droit
        right_wall = Entity(
            model="cube",
            color=wall_color,
            position=pos + Vec3(size/2 - wall_thickness/2, wall_height/2, 0),
            scale=(wall_thickness, wall_height, size),
            collider="box",
        )
        self.entities.append(right_wall)

        # Mur avant avec porte (2 parties)
        door_width = 1.5
        side_width = (size - door_width) / 2

        # Partie gauche du mur avant
        front_left = Entity(
            model="cube",
            color=wall_color,
            position=pos + Vec3(-size/4 - door_width/4, wall_height/2, size/2 - wall_thickness/2),
            scale=(side_width, wall_height, wall_thickness),
            collider="box",
        )
        self.entities.append(front_left)

        # Partie droite du mur avant
        front_right = Entity(
            model="cube",
            color=wall_color,
            position=pos + Vec3(size/4 + door_width/4, wall_height/2, size/2 - wall_thickness/2),
            scale=(side_width, wall_height, wall_thickness),
            collider="box",
        )
        self.entities.append(front_right)

        # Dessus de porte
        door_top = Entity(
            model="cube",
            color=wall_color,
            position=pos + Vec3(0, wall_height - 0.3, size/2 - wall_thickness/2),
            scale=(door_width, 0.6, wall_thickness),
            collider="box",
        )
        self.entities.append(door_top)

        # Toit
        roof = Entity(
            model="cube",
            color=roof_color,
            position=pos + Vec3(0, wall_height + 0.4, 0),
            scale=(size + 1, 0.8, size + 1),
        )
        self.entities.append(roof)

        # Mobilier interieur - Table
        table = Entity(
            model="cube",
            color=color.rgb(101, 67, 33),
            position=pos + Vec3(0, 0.4, -1),
            scale=(1.5, 0.1, 1),
            collider="box",
        )
        self.entities.append(table)

        # Pieds de table
        for tx, tz in [(-0.6, -0.4), (0.6, -0.4), (-0.6, 0.4), (0.6, 0.4)]:
            leg = Entity(
                model="cube",
                color=color.rgb(80, 50, 25),
                position=pos + Vec3(tx, 0.2, -1 + tz),
                scale=(0.1, 0.4, 0.1),
            )
            self.entities.append(leg)

        # PNJ dans la maison
        if has_npc:
            npc_names = ["Marcel", "Jeanne", "Pierre", "Marie", "Henri", "Louise"]
            dialogues = [
                "Bienvenue voyageur! Le donjon est au nord-est, faites attention!",
                "Avez-vous vu ces creatures? Elles sont de plus en plus agressives...",
                "Je vends des potions... enfin, quand j'en ai.",
                "Le forgeron a ferme boutique depuis l'attaque des gobelins.",
                "On dit qu'un tresor se cache au fond du donjon!",
                "Reposez-vous avant de partir a l'aventure.",
            ]
            self.npc = NPC(
                pos + Vec3(random.uniform(-1, 1), 0, random.uniform(-1.5, 0)),
                random.choice(npc_names),
                random.choice(dialogues)
            )
            npcs.append(self.npc)


# ============================================================================
# CLASSES - JOUEUR
# ============================================================================

class Player(Entity):
    """Joueur FPS avec inventaire"""
    def __init__(self, pos):
        super().__init__(
            position=pos + Vec3(0, 1, 0),
            collider="box",
            scale=(0.6, 1.8, 0.6),
        )
        self.speed = 5
        self.sprint_speed = 8
        self.health = 100
        self.max_health = 100
        self.yaw = 0
        self.pitch = 0

        # Inventaire d'armes
        self.inventory = ["dague", "epee", "hache", "masse"]
        self.current_weapon_index = 0
        self.current_weapon = self.inventory[0]
        self.last_attack = 0

        # Camera
        camera.parent = self
        camera.position = (0, 0.7, 0)
        camera.rotation = (0, 0, 0)
        camera.fov = 90

        # Modele d'arme
        self.weapon_model = WeaponModel()

    def update(self):
        if not game_started:
            return

        # Souris
        if mouse.locked:
            self.yaw -= mouse.velocity[0] * 50
            self.pitch -= mouse.velocity[1] * 50
            self.pitch = clamp(self.pitch, -80, 80)
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

        # Sprint
        current_speed = self.sprint_speed if held_keys["shift"] else self.speed

        if direction.length() > 0:
            direction = direction.normalized()
            new_pos = self.position + direction * current_speed * time.dt

            # Simple collision check
            hit = raycast(self.position + Vec3(0, 0.5, 0), direction, distance=0.5, ignore=[self])
            if not hit.hit:
                self.position = new_pos

        # Animation idle de l'arme
        self.weapon_model.idle_animation()

    def attack(self):
        weapon_data = WEAPONS_DATA[self.current_weapon]
        if time.time() - self.last_attack < weapon_data.cooldown:
            return

        self.last_attack = time.time()
        self.weapon_model.attack_animation()

        # Raycast pour toucher
        hit = raycast(camera.world_position, camera.forward, distance=weapon_data.reach, ignore=[self])
        if hit.hit and hasattr(hit.entity, "take_damage"):
            hit.entity.take_damage(weapon_data.damage)

    def change_weapon(self, index):
        if 0 <= index < len(self.inventory):
            self.current_weapon_index = index
            self.current_weapon = self.inventory[index]
            self.weapon_model.set_weapon(self.current_weapon)
            update_hud()

    def next_weapon(self):
        new_index = (self.current_weapon_index + 1) % len(self.inventory)
        self.change_weapon(new_index)

    def prev_weapon(self):
        new_index = (self.current_weapon_index - 1) % len(self.inventory)
        self.change_weapon(new_index)

    def take_damage(self, amount):
        self.health -= amount
        self.health = max(0, self.health)
        update_hud()

        # Flash rouge
        damage_flash.color = color.rgba(255, 0, 0, 100)
        damage_flash.animate_color(color.rgba(255, 0, 0, 0), duration=0.3)


# ============================================================================
# CLASSES - ENNEMIS
# ============================================================================

class Enemy(Entity):
    """Ennemi avec IA basique"""
    def __init__(self, pos, enemy_type="goblin"):
        types = {
            "goblin": {"color": color.rgb(80, 120, 80), "hp": 30, "damage": 5, "speed": 3},
            "orc": {"color": color.rgb(120, 80, 80), "hp": 50, "damage": 10, "speed": 2.5},
            "squelette": {"color": color.rgb(220, 220, 210), "hp": 25, "damage": 8, "speed": 3.5},
            "troll": {"color": color.rgb(90, 70, 50), "hp": 100, "damage": 20, "speed": 1.5},
        }
        data = types.get(enemy_type, types["goblin"])

        super().__init__(
            model="cube",
            color=data["color"],
            position=pos + Vec3(0, 1, 0),
            scale=(0.9, 1.8, 0.6),
            collider="box",
        )
        self.hp = data["hp"]
        self.max_hp = data["hp"]
        self.damage = data["damage"]
        self.speed = data["speed"]
        self.enemy_type = enemy_type
        self.last_attack = 0
        self.original_color = data["color"]

        # Yeux
        self.eye_left = Entity(
            parent=self,
            model="cube",
            color=color.red if enemy_type == "squelette" else color.black,
            scale=(0.15, 0.1, 0.05),
            position=(-0.15, 0.35, 0.3),
        )
        self.eye_right = Entity(
            parent=self,
            model="cube",
            color=color.red if enemy_type == "squelette" else color.black,
            scale=(0.15, 0.1, 0.05),
            position=(0.15, 0.35, 0.3),
        )

        # Barre de vie
        self.health_bar_bg = Entity(
            parent=self,
            model="cube",
            color=color.black,
            scale=(1, 0.1, 0.05),
            position=(0, 1.2, 0),
            billboard=True,
        )
        self.health_bar = Entity(
            parent=self,
            model="cube",
            color=color.red,
            scale=(1, 0.08, 0.05),
            position=(0, 1.2, 0.01),
            billboard=True,
        )

    def update(self):
        if not game_started or not player:
            return

        to_player = player.position - self.position
        dist = to_player.length()

        # IA simple
        if dist < 20:
            # Regarder le joueur
            self.look_at_2d(player.position)

            if dist > 1.8:
                # Se deplacer vers le joueur
                direction = Vec3(to_player.x, 0, to_player.z).normalized()
                new_pos = self.position + direction * self.speed * time.dt
                self.position = new_pos
            else:
                # Attaquer
                if time.time() - self.last_attack > 1.0:
                    self.last_attack = time.time()
                    player.take_damage(self.damage)

    def take_damage(self, amount):
        self.hp -= amount
        self.color = color.white
        invoke(self.reset_color, delay=0.1)

        # Update health bar
        health_percent = self.hp / self.max_hp
        self.health_bar.scale_x = max(0, health_percent)

        if self.hp <= 0:
            self.die()

    def reset_color(self):
        if self.enabled:
            self.color = self.original_color

    def die(self):
        if self in enemies:
            enemies.remove(self)
        destroy(self)
        update_hud()


# ============================================================================
# HUD MODERNE
# ============================================================================

# Crosshair (viseur)
crosshair_size = 0.015
crosshair_thickness = 0.003
crosshair_gap = 0.008
crosshair_color = color.rgba(255, 255, 255, 200)

crosshair_top = Entity(parent=camera.ui, model="quad", color=crosshair_color,
    scale=(crosshair_thickness, crosshair_size), position=(0, crosshair_gap + crosshair_size/2), enabled=False)
crosshair_bottom = Entity(parent=camera.ui, model="quad", color=crosshair_color,
    scale=(crosshair_thickness, crosshair_size), position=(0, -crosshair_gap - crosshair_size/2), enabled=False)
crosshair_left = Entity(parent=camera.ui, model="quad", color=crosshair_color,
    scale=(crosshair_size, crosshair_thickness), position=(-crosshair_gap - crosshair_size/2, 0), enabled=False)
crosshair_right = Entity(parent=camera.ui, model="quad", color=crosshair_color,
    scale=(crosshair_size, crosshair_thickness), position=(crosshair_gap + crosshair_size/2, 0), enabled=False)
crosshair_elements = [crosshair_top, crosshair_bottom, crosshair_left, crosshair_right]

# Barre de vie
health_bar_bg = Entity(parent=camera.ui, model="quad", color=color.rgb(40, 40, 40),
    scale=(0.3, 0.025), position=(-0.65, 0.45), origin=(-0.5, 0), enabled=False)
health_bar_fill = Entity(parent=camera.ui, model="quad", color=color.rgb(200, 50, 50),
    scale=(0.3, 0.02), position=(-0.65, 0.45), origin=(-0.5, 0), enabled=False)
health_bar_border = Entity(parent=camera.ui, model="quad", color=color.white,
    scale=(0.305, 0.03), position=(-0.652, 0.45), origin=(-0.5, 0), enabled=False)

health_text = Text(text="100", parent=camera.ui, position=(-0.5, 0.45),
    origin=(-0.5, 0), scale=1.2, color=color.white, enabled=False)
health_icon = Text(text="+", parent=camera.ui, position=(-0.82, 0.45),
    origin=(0, 0), scale=2, color=color.rgb(200, 50, 50), enabled=False)

# Inventaire d'armes (bas de l'ecran)
inventory_slots = []
inventory_texts = []
slot_size = 0.06
slot_spacing = 0.08
inventory_y = -0.42

for i in range(4):
    slot_x = -0.12 + i * slot_spacing

    # Fond du slot
    slot_bg = Entity(parent=camera.ui, model="quad", color=color.rgba(30, 30, 30, 180),
        scale=(slot_size, slot_size), position=(slot_x, inventory_y), enabled=False)
    inventory_slots.append(slot_bg)

    # Numero du slot
    slot_num = Text(text=str(i+1), parent=camera.ui, position=(slot_x - 0.02, inventory_y + 0.035),
        scale=0.8, color=color.gray, enabled=False)
    inventory_texts.append(slot_num)

# Selection d'arme actuelle
weapon_selector = Entity(parent=camera.ui, model="quad", color=color.rgba(255, 200, 50, 100),
    scale=(slot_size + 0.01, slot_size + 0.01), position=(-0.12, inventory_y), enabled=False)

# Nom de l'arme
weapon_name_text = Text(text="Dague", parent=camera.ui, position=(0, -0.35),
    origin=(0, 0), scale=1.2, color=color.white, enabled=False)

# Compteur d'ennemis
enemies_text = Text(text="Ennemis: 0", parent=camera.ui, position=(0.65, 0.45),
    origin=(0, 0), scale=1, color=color.orange, enabled=False)

# Indication interaction
interact_text = Text(text="[E] Parler", parent=camera.ui, position=(0, -0.15),
    origin=(0, 0), scale=1.2, color=color.yellow, enabled=False)

# Dialogue PNJ
dialogue_bg = Entity(parent=camera.ui, model="quad", color=color.rgba(0, 0, 0, 200),
    scale=(0.8, 0.15), position=(0, -0.25), enabled=False)
dialogue_text = Text(text="", parent=camera.ui, position=(0, -0.25),
    origin=(0, 0), scale=1, color=color.white, enabled=False, wordwrap=60)
dialogue_name = Text(text="", parent=camera.ui, position=(-0.35, -0.19),
    origin=(0, 0), scale=1.2, color=color.gold, enabled=False)

# Flash de degats
damage_flash = Entity(parent=camera.ui, model="quad", color=color.rgba(255, 0, 0, 0),
    scale=(2, 1), z=-0.1, enabled=False)

# Liste de tous les elements HUD
hud_elements = [
    health_bar_bg, health_bar_fill, health_bar_border, health_text, health_icon,
    weapon_selector, weapon_name_text, enemies_text, damage_flash
] + crosshair_elements + inventory_slots + inventory_texts


def show_hud():
    for elem in hud_elements:
        elem.enabled = True


def hide_hud():
    for elem in hud_elements:
        elem.enabled = False


def update_hud():
    if not player:
        return

    # Barre de vie
    health_percent = player.health / player.max_health
    health_bar_fill.scale_x = 0.3 * health_percent
    health_text.text = str(int(player.health))

    # Couleur selon vie
    if health_percent > 0.6:
        health_bar_fill.color = color.rgb(50, 200, 50)
    elif health_percent > 0.3:
        health_bar_fill.color = color.rgb(200, 200, 50)
    else:
        health_bar_fill.color = color.rgb(200, 50, 50)

    # Selection d'arme
    slot_x = -0.12 + player.current_weapon_index * slot_spacing
    weapon_selector.x = slot_x

    # Nom de l'arme
    weapon_names = {"dague": "Dague", "epee": "Epee", "hache": "Hache", "masse": "Masse"}
    weapon_name_text.text = weapon_names.get(player.current_weapon, "")

    # Compteur ennemis
    enemies_text.text = f"Ennemis: {len(enemies)}"


# ============================================================================
# MENU PRINCIPAL
# ============================================================================

menu_bg = Entity(parent=camera.ui, model="quad", color=color.rgb(15, 15, 25),
    scale=(2, 1), z=0.1)

menu_title = Text(text="TES1: ARENA", parent=camera.ui, position=(0, 0.32),
    origin=(0, 0), scale=4, color=color.gold)

menu_subtitle = Text(text="Village & Donjon", parent=camera.ui, position=(0, 0.22),
    origin=(0, 0), scale=1.5, color=color.light_gray)

btn_play = Button(text="NOUVELLE PARTIE", parent=camera.ui, position=(0, 0.05),
    scale=(0.35, 0.07), color=color.rgb(40, 90, 40), highlight_color=color.rgb(60, 120, 60))

btn_quit = Button(text="QUITTER", parent=camera.ui, position=(0, -0.05),
    scale=(0.35, 0.07), color=color.rgb(90, 40, 40), highlight_color=color.rgb(120, 60, 60))

menu_controls = Text(
    text="ZQSD: Bouger | Souris: Viser | Clic: Attaquer | 1-4: Armes | E: Parler | Shift: Sprint",
    parent=camera.ui, position=(0, -0.22), origin=(0, 0), scale=0.7, color=color.gray)

menu_elements = [menu_bg, menu_title, menu_subtitle, btn_play, btn_quit, menu_controls]


def hide_menu():
    for elem in menu_elements:
        elem.enabled = False


def show_menu():
    for elem in menu_elements:
        elem.enabled = True


# ============================================================================
# CREATION DU MONDE
# ============================================================================

def create_world():
    global player, enemies, npcs, world_entities

    enemies.clear()
    npcs.clear()
    world_entities.clear()

    rng = random.Random(42)

    # Ciel
    sky = Entity(model="sphere", scale=500, color=color.rgb(135, 190, 255), double_sided=True)
    world_entities.append(sky)

    # Soleil
    sun = Entity(model="sphere", scale=8, color=color.rgb(255, 240, 200),
        position=(150, 200, 100))
    world_entities.append(sun)

    # Sol principal
    ground = Entity(model="cube", scale=(150, 0.1, 150), color=color.rgb(50, 130, 50),
        position=(0, -0.05, 0), collider="box")
    world_entities.append(ground)

    # Chemin de terre vers le donjon
    path = Entity(model="cube", scale=(60, 0.12, 4), color=color.rgb(120, 90, 60),
        position=(25, 0, -15), rotation=(0, 35, 0))
    world_entities.append(path)

    # === VILLAGE ===
    # Place centrale
    plaza = Entity(model="cube", scale=(12, 0.12, 12), color=color.rgb(140, 120, 100),
        position=(0, 0, 0))
    world_entities.append(plaza)

    # Fontaine au centre
    fountain_base = Entity(model="cube", scale=(2, 0.5, 2), color=color.rgb(100, 100, 110),
        position=(0, 0.25, 0), collider="box")
    fountain_water = Entity(model="cube", scale=(1.5, 0.1, 1.5), color=color.rgb(100, 150, 200),
        position=(0, 0.55, 0))
    world_entities.extend([fountain_base, fountain_water])

    # Maisons du village (avec interieur)
    house_positions = [
        (Vec3(-12, 0, -8), True),
        (Vec3(-12, 0, 8), True),
        (Vec3(12, 0, -8), True),
        (Vec3(12, 0, 8), True),
        (Vec3(0, 0, 15), True),
        (Vec3(-18, 0, 0), False),
    ]

    for pos, has_npc in house_positions:
        house = House(pos, size=6, has_npc=has_npc)
        world_entities.extend(house.entities)

    # Arbres autour
    for _ in range(40):
        tx = rng.randint(-60, 60)
        tz = rng.randint(-60, 60)
        # Pas dans le village ou sur le chemin
        if (abs(tx) > 20 or abs(tz) > 20) and not (-5 < tz < 5 and tx > 0):
            # Tronc
            trunk = Entity(model="cube", color=color.rgb(80, 50, 30),
                position=(tx, 2, tz), scale=(1, 4, 1), collider="box")
            # Feuillage
            leaves = Entity(model="cube", color=color.rgb(30, 100, 30),
                position=(tx, 5, tz), scale=(3, 3, 3))
            world_entities.extend([trunk, leaves])

    # === DONJON ===
    donjon_x, donjon_z = 55, -35
    donjon_size = 25

    # Sol du donjon
    dungeon_floor = Entity(model="cube", scale=(donjon_size, 0.15, donjon_size),
        color=color.rgb(35, 35, 45), position=(donjon_x, 0, donjon_z))
    world_entities.append(dungeon_floor)

    # Murs du donjon
    wall_color = color.rgb(50, 50, 65)
    wall_height = 4

    # Murs perimetriques avec ouverture
    for i in range(-donjon_size//2, donjon_size//2 + 1, 3):
        # Nord
        Entity(model="cube", color=wall_color, collider="box",
            position=(donjon_x + i, wall_height/2, donjon_z - donjon_size/2),
            scale=(3, wall_height, 1))
        # Sud
        Entity(model="cube", color=wall_color, collider="box",
            position=(donjon_x + i, wall_height/2, donjon_z + donjon_size/2),
            scale=(3, wall_height, 1))
        # Est
        Entity(model="cube", color=wall_color, collider="box",
            position=(donjon_x + donjon_size/2, wall_height/2, donjon_z + i),
            scale=(1, wall_height, 3))
        # Ouest (avec ouverture)
        if abs(i) > 3:
            Entity(model="cube", color=wall_color, collider="box",
                position=(donjon_x - donjon_size/2, wall_height/2, donjon_z + i),
                scale=(1, wall_height, 3))

    # Piliers interieurs
    pillar_positions = [
        (donjon_x - 6, donjon_z - 6), (donjon_x + 6, donjon_z - 6),
        (donjon_x - 6, donjon_z + 6), (donjon_x + 6, donjon_z + 6),
    ]
    for px, pz in pillar_positions:
        pillar = Entity(model="cube", color=color.rgb(60, 60, 75),
            position=(px, 2.5, pz), scale=(2, 5, 2), collider="box")
        world_entities.append(pillar)

    # === JOUEUR ===
    player = Player(Vec3(0, 0, 5))

    # === ENNEMIS ===
    # Gobelins et Orcs dans la nature
    nature_spawns = [
        (25, 20, "goblin"), (-25, 25, "goblin"), (30, -5, "orc"),
        (-30, -20, "orc"), (35, 15, "goblin"), (-20, 30, "goblin"),
        (20, -25, "orc"), (-35, 10, "goblin"),
    ]
    for ex, ez, etype in nature_spawns:
        e = Enemy(Vec3(ex, 0, ez), etype)
        enemies.append(e)

    # Squelettes et Trolls dans le donjon
    dungeon_spawns = [
        (donjon_x - 5, donjon_z - 5, "squelette"),
        (donjon_x + 5, donjon_z - 5, "squelette"),
        (donjon_x, donjon_z + 5, "squelette"),
        (donjon_x - 8, donjon_z, "squelette"),
        (donjon_x + 8, donjon_z, "squelette"),
        (donjon_x, donjon_z, "troll"),
    ]
    for ex, ez, etype in dungeon_spawns:
        e = Enemy(Vec3(ex, 0, ez), etype)
        enemies.append(e)


# ============================================================================
# FONCTIONS DU JEU
# ============================================================================

current_dialogue = None
dialogue_timer = 0


def start_game():
    global game_started
    hide_menu()
    create_world()
    show_hud()
    update_hud()
    mouse.locked = True
    game_started = True


def quit_game():
    application.quit()


def check_npc_interaction():
    """Verifie si un PNJ est proche pour interaction"""
    global current_dialogue

    if not player or current_dialogue:
        return None

    for npc in npcs:
        if not npc.enabled:
            continue
        dist = (npc.position - player.position).length()
        if dist < 3:
            return npc
    return None


def show_dialogue(npc):
    global current_dialogue, dialogue_timer
    current_dialogue = npc
    dialogue_timer = time.time()

    dialogue_bg.enabled = True
    dialogue_text.enabled = True
    dialogue_name.enabled = True

    dialogue_name.text = npc.npc_name
    dialogue_text.text = npc.dialogue


def hide_dialogue():
    global current_dialogue
    current_dialogue = None

    dialogue_bg.enabled = False
    dialogue_text.enabled = False
    dialogue_name.enabled = False


btn_play.on_click = start_game
btn_quit.on_click = quit_game


# ============================================================================
# BOUCLE PRINCIPALE
# ============================================================================

def update():
    global dialogue_timer

    if not game_started:
        return

    # Update HUD
    update_hud()

    # Check interaction PNJ
    nearby_npc = check_npc_interaction()
    interact_text.enabled = nearby_npc is not None and current_dialogue is None

    # Auto-hide dialogue apres 4 secondes
    if current_dialogue and time.time() - dialogue_timer > 4:
        hide_dialogue()


def input(key):
    global game_started

    if not game_started:
        return

    if key == "escape":
        mouse.locked = not mouse.locked

    if key == "left mouse down" and player:
        player.attack()

    # Changement d'arme par touches
    if key == "1" and player:
        player.change_weapon(0)
    elif key == "2" and player:
        player.change_weapon(1)
    elif key == "3" and player:
        player.change_weapon(2)
    elif key == "4" and player:
        player.change_weapon(3)

    # Molette pour changer d'arme
    if key == "scroll up" and player:
        player.prev_weapon()
    elif key == "scroll down" and player:
        player.next_weapon()

    # Interaction PNJ
    if key == "e":
        if current_dialogue:
            hide_dialogue()
        else:
            npc = check_npc_interaction()
            if npc:
                show_dialogue(npc)


# ============================================================================
# LANCEMENT
# ============================================================================

mouse.locked = False
app.run()
