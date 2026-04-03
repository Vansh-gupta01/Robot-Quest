import pygame
import random
import json
import os
import math
import sys
import traceback
from dataclasses import dataclass

# pyinstaller compat
if getattr(sys, 'frozen', False):
    ASSET_DIR = sys._MEIPASS
else:
    ASSET_DIR = os.path.dirname(__file__)

MUSIC_DIR = os.path.join(ASSET_DIR, "music")

# game constants 
TILE = 32
MAP_W, MAP_H = 50, 30
SCR_W, SCR_H = 960, 640
FPS = 60

# tile types
FLOOR  = 0
WALL   = 1
SPIKE  = 2
COIN   = 3
KEY    = 4
TURRET = 5
LASER  = 6

# save path - needs to go beside the exe, not inside temp dir
if getattr(sys, 'frozen', False):
    SAVE_FILE = os.path.join(os.path.dirname(sys.executable), "Robot Quest.sav")
else:
    SAVE_FILE = "Robot Quest"

#  Pixel art / sprite generation
#  (all procedural since i dont have actual sprite files

def _noisy_surface(w, h, base_col, noise=20):
    """just fills a surface with a base color + random per-pixel noise"""
    s = pygame.Surface((w, h))
    s.fill(base_col)
    for px in range(w):
        for py in range(h):
            n = random.randint(-noise, noise)
            r = max(0, min(255, base_col[0] + n))
            g = max(0, min(255, base_col[1] + n))
            b = max(0, min(255, base_col[2] + n))
            s.set_at((px, py), (r, g, b))
    return s


def make_wall():
    s = _noisy_surface(TILE, TILE, (40, 40, 50))
    pygame.draw.rect(s, (20, 20, 30), (0, 0, TILE, TILE), 2)
    pygame.draw.line(s, (60, 60, 70), (0, 0), (TILE, TILE), 1)
    return s


def make_floor():
    s = _noisy_surface(TILE, TILE, (20, 20, 30), noise=5)
    pygame.draw.rect(s, (40, 40, 60), (0, 0, TILE, TILE), 1)
    return s


def make_player():
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    # body
    pygame.draw.rect(s, (50, 100, 200), (8, 6, 16, 18))
    # visor
    pygame.draw.rect(s, (150, 200, 255), (10, 8, 12, 6))
    # arms
    pygame.draw.rect(s, (50, 50, 50), (6, 10, 4, 10))
    pygame.draw.rect(s, (50, 50, 50), (22, 10, 4, 10))
    # antenna
    pygame.draw.line(s, (200, 200, 200), (16, 6), (16, 2), 2)
    pygame.draw.circle(s, (255, 0, 0), (16, 2), 2)
    return s


def make_ghost():
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    pygame.draw.circle(s, (220, 220, 220), (16, 12), 10)
    pygame.draw.polygon(s, (220, 220, 220), [(6, 16), (26, 16), (16, 30)])
    # eyes
    pygame.draw.circle(s, (0, 0, 0), (12, 12), 2)
    pygame.draw.circle(s, (0, 0, 0), (20, 12), 2)
    return s


def make_patrol():
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    pygame.draw.rect(s, (255, 200, 0), (6, 6, 20, 20))
    pygame.draw.rect(s, (0, 0, 0), (8, 10, 16, 6))     # face slit
    pygame.draw.rect(s, (255, 0, 0), (12, 12, 4, 2))    # eye
    return s


def make_spike():
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    center = (16, 16)
    pygame.draw.circle(s, (150, 150, 150), center, 12)
    pygame.draw.circle(s, (100, 100, 100), center, 4)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        tip_x = 16 + math.cos(rad) * 14
        tip_y = 16 + math.sin(rad) * 14
        pygame.draw.line(s, (200, 200, 200), center, (tip_x, tip_y), 2)
    return s


def make_turret():
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    pygame.draw.circle(s, (30, 30, 30), (16, 16), 12)
    pygame.draw.circle(s, (0, 0, 0), (16, 16), 6)
    pygame.draw.rect(s, (100, 0, 0), (14, 14, 4, 4))  # red dot in center
    return s


def make_key():
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 255, 100), (10, 8, 12, 16))
    pygame.draw.rect(s, (0, 150, 50), (12, 12, 8, 8))
    return s
#  BSP Dungeon generation
@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)


def split_bsp(area, min_size=6, max_depth=5):
    """binary space partition - splits a big area into smaller rooms"""
    rooms = []

    def _split(r, depth):
        # stop splitting if too small or too deep
        if depth >= max_depth or (r.w <= min_size * 2 and r.h <= min_size * 2):
            rooms.append(r)
            return
        if r.h < min_size * 2 + 1 and r.w < min_size * 2 + 1:
            rooms.append(r)
            return

        # decide split direction based on aspect ratio
        horiz = random.choice([True, False])
        if r.w > r.h * 1.5:
            horiz = False
        elif r.h > r.w * 1.5:
            horiz = True

        if horiz:
            low = r.y + min_size
            high = r.y + r.h - min_size
            if low >= high:
                rooms.append(r)
                return
            cut = random.randint(low, high)
            _split(Rect(r.x, r.y, r.w, cut - r.y), depth + 1)
            _split(Rect(r.x, cut, r.w, r.y + r.h - cut), depth + 1)
        else:
            low = r.x + min_size
            high = r.x + r.w - min_size
            if low >= high:
                rooms.append(r)
                return
            cut = random.randint(low, high)
            _split(Rect(r.x, r.y, cut - r.x, r.h), depth + 1)
            _split(Rect(cut, r.y, r.x + r.w - cut, r.h), depth + 1)

    _split(area, 0)

    # shrink rooms a bit so they dont fill the entire partition
    final = []
    for r in rooms:
        max_w = max(min_size, r.w - 2)
        max_h = max(min_size, r.h - 2)
        rw = min_size if min_size > max_w else random.randint(min_size, max_w)
        rh = min_size if min_size > max_h else random.randint(min_size, max_h)
        rx = r.x + (r.w - rw) // 2
        ry = r.y + (r.h - rh) // 2
        final.append(Rect(rx, ry, rw, rh))

    return final


def _is_open_tile(grid, x, y):
    """only allow obstacle placement on tiles with plenty of room around them.
    needs at least 3 open neighbors so the player can always walk around it"""
    neighbors = 0
    if x > 0 and grid[x - 1][y] != WALL:
        neighbors += 1
    if x < MAP_W - 1 and grid[x + 1][y] != WALL:
        neighbors += 1
    if y > 0 and grid[x][y - 1] != WALL:
        neighbors += 1
    if y < MAP_H - 1 and grid[x][y + 1] != WALL:
        neighbors += 1
    return neighbors >= 3


def generate_dungeon(level_num, seed, difficulty_mult, attempt=0):
    """builds a random dungeon. retries with different seeds if something goes wrong"""
    if attempt > 10:
        return generate_dungeon(level_num, 0, difficulty_mult, 0)

    random.seed(seed)
    grid = [[WALL] * MAP_H for _ in range(MAP_W)]

    try:
        rooms = split_bsp(Rect(1, 1, MAP_W - 2, MAP_H - 2), min_size=5, max_depth=5)
    except Exception:
        return generate_dungeon(level_num, seed + 1, difficulty_mult, attempt + 1)

    if not rooms:
        return generate_dungeon(level_num, seed + 1, difficulty_mult, attempt + 1)

    # carve out rooms
    for room in rooms:
        for x in range(room.x, room.x + room.w):
            for y in range(room.y, room.y + room.h):
                if 0 <= x < MAP_W and 0 <= y < MAP_H:
                    grid[x][y] = FLOOR

    # connect rooms with corridors
    centers = [r.center() for r in rooms]
    centers.sort()
    for i in range(len(centers) - 1):
        x1, y1 = centers[i]
        x2, y2 = centers[i + 1]
        # randomly pick L-shaped corridor direction
        if random.choice([True, False]):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                grid[x][y1] = FLOOR
            for y in range(min(y1, y2), max(y1, y2) + 1):
                grid[x2][y] = FLOOR
        else:
            for y in range(min(y1, y2), max(y1, y2) + 1):
                grid[x1][y] = FLOOR
            for x in range(min(x1, x2), max(x1, x2) + 1):
                grid[x][y2] = FLOOR

    if not centers:
        return generate_dungeon(level_num, seed + 1, difficulty_mult, attempt + 1)

    # place player, key, exit
    player_start = centers[0]

    # try to put key far from player
    far_rooms = [c for c in centers
                 if abs(c[0] - player_start[0]) + abs(c[1] - player_start[1]) > 10]
    if not far_rooms:
        far_rooms = [centers[-1]]
    key_pos = random.choice(far_rooms)

    if 0 <= key_pos[0] < MAP_W and 0 <= key_pos[1] < MAP_H:
        grid[key_pos[0]][key_pos[1]] = KEY

    exit_pos = centers[-1]
    if exit_pos == key_pos and len(centers) > 1:
        exit_pos = centers[-2]

    # gather valid floor tiles for obstacle placement
    # (skip player start, exit, key positions)
    excluded = {player_start, exit_pos, key_pos}
    floor_tiles = [
        (x, y) for x in range(MAP_W) for y in range(MAP_H)
        if grid[x][y] == FLOOR and (x, y) not in excluded
    ]
    # filter out narrow corridors so obstacles dont block the path
    floor_tiles = [pos for pos in floor_tiles if _is_open_tile(grid, pos[0], pos[1])]
    random.shuffle(floor_tiles)

    # pop tiles from the list as we place stuff
    def grab_tile():
        return floor_tiles.pop(0) if floor_tiles else None

    spikes = set()
    turrets = []
    lasers = []
    patrol_bots = []
    coins = set()

    # spikes
    num_spikes = int((5 + level_num) * difficulty_mult)
    for _ in range(num_spikes):
        pos = grab_tile()
        if pos:
            grid[pos[0]][pos[1]] = SPIKE
            spikes.add(pos)

    # turrets
    num_turrets = int((3 + level_num * 0.5) * difficulty_mult)
    for _ in range(num_turrets):
        pos = grab_tile()
        if pos:
            grid[pos[0]][pos[1]] = TURRET
            turrets.append(Turret(pos))

    # laser gates
    for _ in range(int(4 * difficulty_mult)):
        pos = grab_tile()
        if pos:
            lasers.append(LaserGate(pos))

    # patrol bots
    num_bots = int((2 + level_num * 0.3) * difficulty_mult)
    for _ in range(num_bots):
        pos = grab_tile()
        if pos:
            patrol_bots.append(PatrolBot(pos, grid))

    # coins (always 10)
    for _ in range(10):
        pos = grab_tile()
        if pos:
            grid[pos[0]][pos[1]] = COIN
            coins.add(pos)

    return {
        "grid": grid,
        "player_start": player_start,
        "exit_pos": exit_pos,
        "key_pos": key_pos,
        "turrets": turrets,
        "lasers": lasers,
        "patrol_bots": patrol_bots,
        "coins": coins,
    }

#  Game entities
class Projectile:
    def __init__(self, x, y, dx, dy):
        self.rect = pygame.Rect(x, y, 6, 6)
        self.dx = dx
        self.dy = dy
        self.life = 100

    def update(self):
        self.rect.x += self.dx * 5
        self.rect.y += self.dy * 5
        self.life -= 1

    def draw(self, surface, cam_x, cam_y):
        screen_pos = (self.rect.centerx - cam_x, self.rect.centery - cam_y)
        pygame.draw.circle(surface, (255, 50, 50), screen_pos, 4)


class Turret:
    def __init__(self, tile_pos):
        self.rect = pygame.Rect(tile_pos[0] * TILE, tile_pos[1] * TILE, TILE, TILE)
        self.cooldown = random.randint(0, 100)  # offset so they dont all fire at once

    def update(self, projectiles):
        self.cooldown += 1
        if self.cooldown > 120:
            self.cooldown = 0
            cx, cy = self.rect.center
            # shoot in 4 directions
            for direction in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                projectiles.append(Projectile(cx, cy, direction[0], direction[1]))


class LaserGate:
    def __init__(self, tile_pos):
        self.rect = pygame.Rect(tile_pos[0] * TILE, tile_pos[1] * TILE, TILE, TILE)
        self.timer = random.randint(0, 180)
        self.active = False

    def update(self):
        self.timer += 1
        self.active = (self.timer % 180) < 120   # on for 120 frames, off for 60

    def draw(self, surface, cam_x, cam_y):
        rx = self.rect.x - cam_x
        ry = self.rect.y - cam_y
        # two small emitter nodes
        pygame.draw.circle(surface, (50, 50, 50), (rx + 4, ry + 16), 4)
        pygame.draw.circle(surface, (50, 50, 50), (rx + 28, ry + 16), 4)
        if self.active:
            thickness = random.randint(2, 6)  # flicker effect
            pygame.draw.line(surface, (255, 0, 0), (rx + 4, ry + 16), (rx + 28, ry + 16), thickness)


class PatrolBot:
    def __init__(self, tile_pos, grid):
        self.rect = pygame.Rect(tile_pos[0] * TILE + 4, tile_pos[1] * TILE + 4, TILE - 8, TILE - 8)
        self.grid = grid
        # randomly start moving horizontally or vertically
        if random.choice([True, False]):
            self.move_x, self.move_y = 1, 0
        else:
            self.move_x, self.move_y = 0, 1

    def update(self):
        next_pos = self.rect.move(self.move_x * 2, self.move_y * 2)
        tile_x = next_pos.centerx // TILE
        tile_y = next_pos.centery // TILE

        # bounce off walls
        hit_wall = False
        if not (0 <= tile_x < len(self.grid) and 0 <= tile_y < len(self.grid[0])):
            hit_wall = True
        elif self.grid[tile_x][tile_y] == WALL:
            hit_wall = True

        if hit_wall:
            self.move_x *= -1
            self.move_y *= -1
        else:
            self.rect = next_pos

    def draw(self, surface, cam_x, cam_y, sprite):
        surface.blit(sprite, (self.rect.x - cam_x, self.rect.y - cam_y))


class Ghost:
    """chases the player through walls... kinda terrifying ngl"""

    def __init__(self, start_tile, level, speed_mult):
        self.rect = pygame.Rect(
            start_tile[0] * TILE + 4,
            start_tile[1] * TILE + 4,
            TILE - 8, TILE - 8
        )
        self.level = level
        self.speed_mult = max(0.3, float(speed_mult))  # dont let it be too slow
        self.base_speed = 80
        self.bob_timer = 0  # for the floating animation

    def update(self, dt, player_rect, grid):
        self.bob_timer += dt * 3

        player_x, player_y = player_rect.center
        ghost_x, ghost_y = self.rect.center

        dx = player_x - ghost_x
        dy = player_y - ghost_y
        dist = math.hypot(dx, dy)

        if dist < 1:
            return  # close enough, dont jitter

        speed = self.base_speed * self.speed_mult

        # normalize direction
        dx /= dist
        dy /= dist

        step_x = dx * speed * dt
        step_y = dy * speed * dt

        # check walls before moving (each axis separately)
        def tile_is_free(r):
            tx = r.centerx // TILE
            ty = r.centery // TILE
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                return grid[tx][ty] not in (WALL, TURRET)
            return False

        test_x = self.rect.move(step_x, 0)
        if tile_is_free(test_x):
            self.rect = test_x

        test_y = self.rect.move(0, step_y)
        if tile_is_free(test_y):
            self.rect = test_y

    def draw(self, surface, cam_x, cam_y, sprite):
        # little floating bob
        offset_y = math.sin(self.bob_timer) * 5
        surface.blit(sprite, (self.rect.x - cam_x, self.rect.y - cam_y + offset_y))

#  Main Game

class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            print("couldn't init audio mixer, continuing without sound")

        self.screen = pygame.display.set_mode((SCR_W, SCR_H))
        pygame.display.set_caption("Robot Quest")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)
        self.title_font = pygame.font.SysFont("comicsansms", 40)

        # load all sprites
        self.sprites = {
            "wall":   make_wall(),
            "floor":  make_floor(),
            "player": make_player(),
            "key":    make_key(),
            "turret": make_turret(),
            "ghost":  make_ghost(),
            "patrol": make_patrol(),
            "spike":  make_spike(),
        }

        # audio setup
        self.menu_music_path = None
        self.game_music_path = None
        self.current_music = None
        self._init_audio()

        # menu stuff
        self.menu_options = ["NEW GAME", "LEVEL SELECT", "CONTINUE", "CONTROLS", "CREDITS", "EXIT"]
        self.state = "MENU_MAIN"
        self.menu_idx = 0
        self.level_sel = 1
        self.save_msg_timer = 0
        self.preview_surf = None
        self._last_preview_lvl = -1

        # game state
        self.difficulty = "MEDIUM"
        self.level = 1
        self.xp = 0
        self.hp = 5
        self.seed = 0
        self.max_level = 1
        self.ghost = None

        self._load_save()
        self._play_music("menu")

    # audio 

    def _init_audio(self):
        self.sfx = {
            "menu_move": None, "menu_select": None,
            "coin": None, "key": None, "hit": None,
            "levelup": None, "save": None, "gameover": None,
        }

        if not pygame.mixer.get_init():
            print("no mixer available, sounds disabled")
            return

        def _load(filename, vol=1.0):
            filepath = os.path.join(MUSIC_DIR, filename)
            if not os.path.exists(filepath):
                print(f"missing: {filepath}")
                return None
            try:
                sound = pygame.mixer.Sound(filepath)
                sound.set_volume(vol)
                return sound
            except Exception as err:
                print(f"failed to load {filepath}: {err}")
                return None

        self.sfx["menu_move"]   = _load("Blip11.wav", 0.4)
        self.sfx["menu_select"] = _load("Blip11.wav", 0.5)
        self.sfx["coin"]        = _load("Pickup35.wav", 0.5)
        self.sfx["key"]         = _load("Pickup35.wav", 0.5)
        self.sfx["hit"]         = _load("Hit1.wav", 0.5)
        self.sfx["levelup"]     = _load("levelup.wav", 0.6)
        self.sfx["save"]        = _load("Shoot3.wav", 0.5)
        self.sfx["gameover"]    = _load("gameover.wav", 0.7)

        # TODO: use different tracks for menu vs gameplay
        self.menu_music_path = os.path.join(MUSIC_DIR, "mmusic.wav")
        self.game_music_path = os.path.join(MUSIC_DIR, "mmusic.wav")

    def _play_music(self, which):
        if not pygame.mixer.get_init():
            return

        path = self.menu_music_path if which == "menu" else self.game_music_path
        if not path or not os.path.exists(path):
            return
        if self.current_music == path:
            return  # already playing

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(0)
            self.current_music = path
        except Exception as err:
            print(f"music playback error: {err}")

    def _sfx(self, name):
        snd = self.sfx.get(name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    # difficulty 

    def _diff_stats(self):
        """returns (hp, trap_multiplier, enemy_speed) based on difficulty"""
        if self.difficulty == "EASY":
            return 10, 0.5, 0.6
        elif self.difficulty == "HARD":
            return 3, 1.5, 1.4
        return 5, 1.0, 1.0  # medium / default

    # save/load 

    def _load_save(self):
        if not os.path.exists(SAVE_FILE):
            return None
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
            self.max_level = data.get("max_level", 1)
            return data
        except Exception:
            return None

    def _save(self):
        if self.level > self.max_level:
            self.max_level = self.level

        data = {
            "level": self.level,
            "xp": self.xp,
            "hp": self.hp,
            "seed": self.seed,
            "difficulty": self.difficulty,
            "max_level": self.max_level,
        }
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump(data, f)
            self.save_msg_timer = 120
            self._sfx("save")
        except Exception as err:
            print(f"save failed: {err}")

    # game flow

    def _new_game(self, start_lvl=1):
        hp, _, _ = self._diff_stats()
        self.level = start_lvl
        self.xp = 0
        self.hp = hp
        self.seed = random.randint(0, 9999)
        self._init_level()
        self.state = "PLAYING"

    def _continue_game(self):
        data = self._load_save()
        if data:
            self.level = data.get("level", 1)
            self.xp = data.get("xp", 0)
            self.hp = data.get("hp", 5)
            self.seed = data.get("seed", 0)

            # handle renamed difficulties from old save files
            diff = data.get("difficulty", "MEDIUM")
            if diff in ("BABY", "TEENAGE"):
                diff = "MEDIUM"
            elif diff == "LEGEND":
                diff = "HARD"
            self.difficulty = diff

            self._init_level()
            self.state = "PLAYING"
        else:
            self._new_game(1)

    def _init_level(self):
        self.has_key = False
        self.projectiles = []
        _, trap_mult, enemy_speed = self._diff_stats()
        self.dungeon = generate_dungeon(self.level, self.seed, trap_mult)

        px, py = self.dungeon["player_start"]
        self.player_rect = pygame.Rect(px * TILE + 4, py * TILE + 4, TILE - 8, TILE - 8)

        # ghost only appears on medium and hard
        if self.difficulty == "EASY":
            self.ghost = None
        else:
            self.ghost = Ghost(self.dungeon["exit_pos"], self.level, enemy_speed)

        # pre-render the background so we dont redraw every tile each frame
        self.bg = pygame.Surface((MAP_W * TILE, MAP_H * TILE))
        for x in range(MAP_W):
            for y in range(MAP_H):
                dest = (x * TILE, y * TILE)
                tile = self.dungeon["grid"][x][y]
                if tile == WALL:
                    self.bg.blit(self.sprites["wall"], dest)
                else:
                    self.bg.blit(self.sprites["floor"], dest)
                if tile == SPIKE:
                    self.bg.blit(self.sprites["spike"], dest)

    def _make_preview(self):
        """renders a tiny minimap for level select"""
        if self.level_sel == self._last_preview_lvl:
            return

        try:
            data = generate_dungeon(self.level_sel, random.randint(0, 9999), 1.0)
            scale = 6
            self.preview_surf = pygame.Surface((MAP_W * scale, MAP_H * scale))
            self.preview_surf.fill((0, 0, 0))

            g = data["grid"]
            for x in range(MAP_W):
                for y in range(MAP_H):
                    r = (x * scale, y * scale, scale, scale)
                    if g[x][y] == WALL:
                        pygame.draw.rect(self.preview_surf, (50, 50, 60), r)
                    elif g[x][y] == FLOOR:
                        pygame.draw.rect(self.preview_surf, (30, 30, 40), r)
                    elif g[x][y] == SPIKE:
                        pygame.draw.rect(self.preview_surf, (100, 30, 30), r)

            # mark key and exit
            kx, ky = data["key_pos"]
            pygame.draw.circle(self.preview_surf, (255, 215, 0),
                               (kx * scale + scale // 2, ky * scale + scale // 2), scale)
            ex, ey = data["exit_pos"]
            pygame.draw.rect(self.preview_surf, (0, 255, 0),
                             (ex * scale, ey * scale, scale, scale), 2)

            self._last_preview_lvl = self.level_sel

        except Exception:
            self.preview_surf = pygame.Surface((300, 200))
            self.preview_surf.fill((30, 0, 0))
            msg = self.font.render("Preview Unavailable", True, (255, 255, 255))
            self.preview_surf.blit(msg, (20, 90))

    # main loop 

    def run(self):
        try:
            while True:
                dt = self.clock.tick(FPS) / 1000.0
                self._handle_events()

                if "MENU" in self.state:
                    self._draw_menu()
                elif self.state == "PLAYING":
                    self._update(dt)
                    self._draw()
                elif self.state == "GAMEOVER":
                    self._draw_gameover()

                pygame.display.flip()
        except Exception:
            traceback.print_exc()
            pygame.quit()
            sys.exit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            if event.type != pygame.KEYDOWN:
                continue

            key = event.key

            # main menu 
            if self.state == "MENU_MAIN":
                if key == pygame.K_UP:
                    self.menu_idx = (self.menu_idx - 1) % len(self.menu_options)
                    self._sfx("menu_move")
                elif key == pygame.K_DOWN:
                    self.menu_idx = (self.menu_idx + 1) % len(self.menu_options)
                    self._sfx("menu_move")
                elif key == pygame.K_RETURN:
                    self._sfx("menu_select")
                    choice = self.menu_options[self.menu_idx]
                    if choice == "NEW GAME":
                        self.state = "MENU_DIFFICULTY"
                        self.menu_idx = 0
                        self.level = 1
                    elif choice == "LEVEL SELECT":
                        self.state = "MENU_LEVEL_SELECT"
                        self.menu_idx = 0
                        self._make_preview()
                    elif choice == "CONTINUE":
                        self._continue_game()
                    elif choice == "CONTROLS":
                        self.state = "MENU_CONTROLS"
                        self.menu_idx = 0
                    elif choice == "CREDITS":
                        self.state = "MENU_CREDITS"
                        self.menu_idx = 0
                    elif choice == "EXIT":
                        sys.exit()

            #  difficulty select 
            elif self.state == "MENU_DIFFICULTY":
                if key == pygame.K_UP:
                    self.menu_idx = (self.menu_idx - 1) % 3
                    self._sfx("menu_move")
                elif key == pygame.K_DOWN:
                    self.menu_idx = (self.menu_idx + 1) % 3
                    self._sfx("menu_move")
                elif key == pygame.K_RETURN:
                    self._sfx("menu_select")
                    self.difficulty = ["EASY", "MEDIUM", "HARD"][self.menu_idx]
                    self._new_game(self.level)
                elif key == pygame.K_ESCAPE:
                    self.state = "MENU_MAIN"

            # level select 
            elif self.state == "MENU_LEVEL_SELECT":
                if key == pygame.K_RIGHT:
                    self.level_sel = min(self.max_level, self.level_sel + 1)
                    self._make_preview()
                    self._sfx("menu_move")
                elif key == pygame.K_LEFT:
                    self.level_sel = max(1, self.level_sel - 1)
                    self._make_preview()
                    self._sfx("menu_move")
                elif key == pygame.K_RETURN:
                    self._sfx("menu_select")
                    self.level = self.level_sel
                    self.state = "MENU_DIFFICULTY"
                elif key == pygame.K_ESCAPE:
                    self.state = "MENU_MAIN"

            # controls / credits (just go back) 
            elif self.state in ("MENU_CONTROLS", "MENU_CREDITS"):
                if key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    self._sfx("menu_select")
                    self.state = "MENU_MAIN"

            # playing 
            elif self.state == "PLAYING":
                if key == pygame.K_k:
                    self._save()
                elif key == pygame.K_ESCAPE:
                    self.state = "MENU_MAIN"
                elif key == pygame.K_l:
                    # skip level (debug cheat, might remove later)
                    self.level += 1
                    if self.level > self.max_level:
                        self.max_level = self.level
                    self.seed = random.randint(0, 9999)
                    self._save()
                    self._init_level()
                    self._sfx("levelup")

            # game over
            elif self.state == "GAMEOVER":
                if key == pygame.K_RETURN:
                    self._sfx("menu_select")
                    self.state = "MENU_MAIN"

    def _update(self, dt):
        keys = pygame.key.get_pressed()
        move_x = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        move_y = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])

        speed = 150
        if move_x and move_y:
            speed *= 0.707  # diagonal normalization

        def walkable(rect):
            tx = rect.centerx // TILE
            ty = rect.centery // TILE
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                return self.dungeon["grid"][tx][ty] not in (WALL, TURRET)
            return True

        # try x then y separately for wall sliding
        new_pos = self.player_rect.move(move_x * speed * dt, 0)
        if walkable(new_pos):
            self.player_rect = new_pos
        new_pos = self.player_rect.move(0, move_y * speed * dt)
        if walkable(new_pos):
            self.player_rect = new_pos

        # which tile is the player standing on?
        tile = (self.player_rect.centerx // TILE, self.player_rect.centery // TILE)

        # pick up key
        if tile == self.dungeon["key_pos"] and not self.has_key:
            self.has_key = True
            self.dungeon["grid"][tile[0]][tile[1]] = FLOOR
            self._sfx("key")

        # pick up coins
        if tile in self.dungeon["coins"]:
            self.dungeon["coins"].remove(tile)
            self.xp += 10
            self._sfx("coin")

        # reached exit with key?
        if tile == self.dungeon["exit_pos"] and self.has_key:
            self.level += 1
            if self.level > self.max_level:
                self.max_level = self.level
            self.seed = random.randint(0, 9999)
            self._save()
            self._init_level()
            self._sfx("levelup")

        # damage checks
        got_hit = False

        # spikes
        if self.dungeon["grid"][tile[0]][tile[1]] == SPIKE:
            got_hit = True

        # turrets fire projectiles
        for turret in self.dungeon["turrets"]:
            turret.update(self.projectiles)

        # lasers
        for laser in self.dungeon["lasers"]:
            laser.update()
            if laser.active and self.player_rect.colliderect(laser.rect):
                got_hit = True

        # patrol bots
        for bot in self.dungeon["patrol_bots"]:
            bot.update()
            if self.player_rect.colliderect(bot.rect):
                got_hit = True

        # projectiles
        for proj in self.projectiles[:]:
            proj.update()
            if self.player_rect.colliderect(proj.rect):
                got_hit = True
                self.projectiles.remove(proj)
            elif proj.life <= 0:
                self.projectiles.remove(proj)
            elif self.dungeon["grid"][proj.rect.centerx // TILE][proj.rect.centery // TILE] == WALL:
                self.projectiles.remove(proj)

        # ghost
        if self.ghost:
            self.ghost.update(dt, self.player_rect, self.dungeon["grid"])
            if self.player_rect.colliderect(self.ghost.rect):
                got_hit = True

        if got_hit:
            self._sfx("hit")
            self.hp -= 1
            # respawn at start
            sx, sy = self.dungeon["player_start"]
            self.player_rect.topleft = (sx * TILE + 4, sy * TILE + 4)
            if self.hp <= 0:
                self._sfx("gameover")
                self.state = "GAMEOVER"

        if self.save_msg_timer > 0:
            self.save_msg_timer -= 1

    # rendering 

    def _draw(self):
        self._play_music("game")
        self.screen.fill((10, 10, 20))

        # camera follows player
        cam_x = max(0, min(MAP_W * TILE - SCR_W, self.player_rect.centerx - SCR_W // 2))
        cam_y = max(0, min(MAP_H * TILE - SCR_H, self.player_rect.centery - SCR_H // 2))

        self.screen.blit(self.bg, (-cam_x, -cam_y))

        # lasers
        for laser in self.dungeon["lasers"]:
            laser.draw(self.screen, cam_x, cam_y)

        # key (if not picked up yet)
        if not self.has_key:
            kx, ky = self.dungeon["key_pos"]
            self.screen.blit(self.sprites["key"], (kx * TILE - cam_x, ky * TILE - cam_y))

        # exit door
        ex, ey = self.dungeon["exit_pos"]
        door_color = (0, 255, 100) if self.has_key else (255, 50, 50)
        pygame.draw.rect(self.screen, door_color, (ex * TILE - cam_x, ey * TILE - cam_y, TILE, TILE), 2)

        # turrets
        for t in self.dungeon["turrets"]:
            self.screen.blit(self.sprites["turret"], (t.rect.x - cam_x, t.rect.y - cam_y))

        # patrol bots
        for bot in self.dungeon["patrol_bots"]:
            bot.draw(self.screen, cam_x, cam_y, self.sprites["patrol"])

        # bullets
        for proj in self.projectiles:
            proj.draw(self.screen, cam_x, cam_y)

        # ghost
        if self.ghost:
            self.ghost.draw(self.screen, cam_x, cam_y, self.sprites["ghost"])

        # player on top
        self.screen.blit(self.sprites["player"],
                         (self.player_rect.x - cam_x, self.player_rect.y - cam_y))

        # HUD bar at bottom
        pygame.draw.rect(self.screen, (0, 0, 0), (0, SCR_H - 40, SCR_W, 40))
        hint = "FIND THE CHIP!" if not self.has_key else "EXIT UNLOCKED!"
        hint_text = self.font.render(f"MODE: {self.difficulty} | {hint}", True, (255, 255, 0))
        self.screen.blit(hint_text, (SCR_W // 2 - hint_text.get_width() // 2, SCR_H - 30))

        # top-left stats
        stats = self.font.render(f"LVL:{self.level} HP:{self.hp} XP:{self.xp}", True, (255, 255, 255))
        self.screen.blit(stats, (10, 10))

        # save confirmation
        if self.save_msg_timer > 0:
            self.screen.blit(self.font.render("SAVED!", True, (0, 255, 0)), (SCR_W - 100, 10))

    def _draw_menu(self):
        self.screen.fill((20, 15, 30))

        if self.state == "MENU_MAIN":
            title = self.title_font.render("ROBOT QUEST", True, (100, 200, 255))
            opts = self.menu_options

        elif self.state == "MENU_LEVEL_SELECT":
            title = self.title_font.render(f"LEVEL: < {self.level_sel} >", True, (100, 255, 100))
            if self.level_sel == self.max_level:
                opts = ["PRESS ENTER TO PLAY", f"(MAX UNLOCKED: {self.max_level})"]
            else:
                opts = ["PRESS ENTER TO PLAY", "ARROWS TO CHANGE"]

            if self.preview_surf:
                pw = self.preview_surf.get_width()
                ph = self.preview_surf.get_height()
                dest = (SCR_W // 2 - pw // 2, 350)
                pygame.draw.rect(self.screen, (200, 200, 200),
                                 (dest[0] - 4, dest[1] - 4, pw + 8, ph + 8), 2)
                self.screen.blit(self.preview_surf, dest)

        elif self.state == "MENU_CONTROLS":
            title = self.title_font.render("CONTROLS", True, (200, 200, 255))
            opts = [
                "Move: WASD / Arrow Keys",
                "Save: K",

                "Cheat Level Up: L",
                "Pause/Back to Menu: ESC",
                "",
                "Press ESC or ENTER to return",
            ]

        elif self.state == "MENU_CREDITS":
            title = self.title_font.render("CREDITS", True, (200, 200, 255))
            opts = [
                "Game Design & Code: Vansh Kumar",
                "Procedural Art: Pygame Pixel Generator",
                "Tiles & Sprites: Vansh Kumar",
                "Game Music: yt_Atmosphera, bfxr, mixkit",
                "",
                "Thanks for playing!",
                "",
                "Press ESC or ENTER to return",
            ]

        else:  # difficulty
            title = self.title_font.render("SELECT DIFFICULTY", True, (255, 100, 100))
            opts = ["EASY", "MEDIUM", "HARD"]

        # draw title centered
        self.screen.blit(title, (SCR_W // 2 - title.get_width() // 2, 100))

        # where to start drawing options
        y_start = 200
        if self.state == "MENU_LEVEL_SELECT":
            y_start = 250
        elif self.state in ("MENU_CONTROLS", "MENU_CREDITS"):
            y_start = 180

        for i, opt in enumerate(opts):
            color = (150, 150, 150)  # default grey

            if self.state in ("MENU_MAIN", "MENU_DIFFICULTY") and i == self.menu_idx:
                color = (255, 255, 0)  # highlight selected

            if self.state == "MENU_LEVEL_SELECT":
                color = (255, 255, 255)

            # grey out CONTINUE if no save exists
            if self.state == "MENU_MAIN" and opt == "CONTINUE" and not os.path.exists(SAVE_FILE):
                color = (60, 60, 60)
                if i == self.menu_idx:
                    color = (100, 100, 0)

            # little arrow for selected option
            text = f"> {opt}" if (self.state == "MENU_MAIN" and i == self.menu_idx) else opt
            rendered = self.font.render(text, True, color)
            self.screen.blit(rendered, (SCR_W // 2 - rendered.get_width() // 2, y_start + i * 36))

    def _draw_gameover(self):
        self.screen.fill((50, 0, 0))
        title = self.title_font.render("Game Over", True, (0, 0, 0))
        subtitle = self.font.render("Press ENTER to Return to Menu", True, (200, 200, 200))
        self.screen.blit(title, (SCR_W // 2 - title.get_width() // 2, 250))
        self.screen.blit(subtitle, (SCR_W // 2 - subtitle.get_width() // 2, 320))


if __name__ == "__main__":
    Game().run()
