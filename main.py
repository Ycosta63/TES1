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
)


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
    
    def __init__(self, position: Vec3):
        super().__init__(
            collider="box",
            scale=(0.5, 1.8, 0.5),
            position=position + Vec3(0, 0.9, 0),
        )
        self.model = None
        
        self.health = 100
        self.speed = 6.0
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
        hit_info = raycast(
            camera.world_position,
            camera.forward,
            distance=5,
            ignore=[self],
        )
        
        if hit_info.hit and isinstance(hit_info.entity, Enemy):
            hit_info.entity.take_damage(20)
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
        
        # Entités
        self.player = None
        self.weapon = None
        self.enemies: List[Enemy] = []
        self.walls: List[Wall] = []
        self.floors: List[Floor] = []
        
        # HUD
        self.hud_health = None
        self.hud_enemies = None
        
        # Initialisation
        self._build_world()
        self._build_player()
        self._build_weapon()
        self._spawn_enemies()
        self._build_hud()
    
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
    
    def _build_player(self):
        """Crée le joueur."""
        self.player = Player(Vec3(0, 0, 0))
    
    def _build_weapon(self):
        """Crée l'arme."""
        self.weapon = Weapon(self.textures["sword"])
    
    def _spawn_enemies(self):
        """Fait spawn des ennemis."""
        for _ in range(5):
            x = random.uniform(-8, 8)
            z = random.uniform(-8, 8)
            color_choice = random.choice([color.red, color.rgb(100, 50, 0)])
            enemy = Enemy(Vec3(x, 0, z), color_choice)
            self.enemies.append(enemy)
    
    def _build_hud(self):
        """Crée le HUD."""
        self.hud_health = Text(
            text="HP: 100",
            position=Vec2(-0.9, 0.45),
            origin=(0, 0),
            scale=1.1,
            color=color.red,
        )
        self.hud_enemies = Text(
            text="Ennemis: 5",
            position=Vec2(-0.9, 0.35),
            origin=(0, 0),
            scale=1.0,
            color=color.orange,
        )
    
    def handle_input(self, key: str):
        """Traite l'input."""
        if key == "escape":
            mouse.locked = not mouse.locked
        
        if key == "left mouse down":
            self.weapon.attack()
            self.player.raycast_attack(self.enemies)
    
    def update(self):
        """Mise à jour du jeu."""
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
        
        # HUD
        if self.hud_health:
            self.hud_health.text = f"HP: {self.player.health}"
        if self.hud_enemies:
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
    
    def input_handler(key):
        game.handle_input(key)
    
    app.run()


