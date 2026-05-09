import pygame, math, random, sys, os

# Import Hero and shared components from Level 2 game
from Level_1.game import (
    Hero, Particles, draw_hpbar, Char,
    SW, SH, FPS, GRAVITY, JUMP_VEL, GROUND_Y,
    WHITE, RED, GOLD, DARK_BLU, SNOW, BLOOD,
    ST_IDLE, ST_WALK, ST_JUMP, ST_ATK, ST_HURT, ST_DEAD,
    load_anim, ASSET_DIR, make_sounds, scale_frames_up_then_down,
)

# Level 1 specific — longer world for more travel
WORLD_W_L1 = 6000
LEVEL1_INTRO = [
    "The ice path rises before you.",
    "Climb up through the snowy village.",
    "Enemies guard each ledge — defeat them.",
    "Reach the sign at the end of the path.",
    '"He wanted to survive. Let\'s see if you do."',
]


def safe_color(col):
    return (int(col[0]) & 0xFF, int(col[1]) & 0xFF, int(col[2]) & 0xFF)


# Path to sprite_kit_2d (christmas_game -> up 4 levels -> CosdeAmmar -> sprite_kit_2d/sprites)
_LEVEL1_DIR = os.path.dirname(os.path.abspath(__file__))
_SPRITE_KIT = os.path.normpath(os.path.join(_LEVEL1_DIR, "sprite_kit_2d", "sprites"))


def load_sprite_kit_anim(folder_name, anim_name, scale=(72, 90)):
    """Load animation from sprite_kit_2d folder structure (individual PNGs per frame)."""
    folder = os.path.join(_SPRITE_KIT, folder_name, anim_name)
    frames = []
    if not os.path.exists(folder):
        return frames
    try:
        for fname in sorted(os.listdir(folder)):
            if fname.endswith(".png"):
                path = os.path.join(folder, fname)
                surf = pygame.image.load(path).convert_alpha()
                if scale:
                    surf = pygame.transform.smoothscale(surf, scale)
                frames.append(surf)
    except (OSError, pygame.error):
        pass
    return frames


# ════════════════════════════════════════════════════════════════
#  LEVEL 1 ENEMIES — from sprite_kit_2d (ice_monster, blue_gnome, red_gnome)
# ════════════════════════════════════════════════════════════════
class SpriteKitEnemy(Char):
    """Enemy using sprite_kit_2d sprites. Subclass with FOLDER, HP, DMG, etc."""

    FOLDER = "ice_monster"
    FW, FH = 72, 90
    BASE_HP = 70
    BASE_SPD = 2.0
    BASE_DMG = 11
    BASE_PAT = 190
    BASE_COOL = 60

    def __init__(self, x, y):
        super().__init__(x, y, 48, 80, self.BASE_HP)
        self.max_hp = self.BASE_HP
        self.hp = self.BASE_HP
        self.speed = self.BASE_SPD
        self.dmg = self.BASE_DMG
        self.pat = self.BASE_PAT
        self.cool = 0
        self.ox = x
        self.facing = -1
        self._asp = 7
        self._load_anims()

    def _load_anims(self):
        p = self.FOLDER
        fw, fh = self.FW, self.FH
        scale = (fw, fh)
        idle = load_sprite_kit_anim(p, "idle", scale)
        walk = load_sprite_kit_anim(p, "walk", scale)
        atk = load_sprite_kit_anim(p, "attack", scale)
        damage = load_sprite_kit_anim(p, "damage", scale)
        faint = load_sprite_kit_anim(p, "faint", scale)
        if not idle:
            idle = walk
        if not walk:
            walk = idle
        hurt_frames = damage if damage else faint
        dead_frames = faint if faint else damage
        if hurt_frames:
            hurt_frames = scale_frames_up_then_down(hurt_frames, fw, fh, 1.5)
        if dead_frames:
            dead_hold = [dead_frames[-1]] if len(dead_frames) > 0 else []
            dead_frames = scale_frames_up_then_down(dead_hold, fw, fh, 1.5)
        self.anims = {
            ST_IDLE: idle or [pygame.Surface((fw, fh))],
            ST_WALK: walk or idle or [pygame.Surface((fw, fh))],
            ST_ATK: atk or walk or idle or [pygame.Surface((fw, fh))],
            ST_HURT: hurt_frames or idle or [pygame.Surface((fw, fh))],
            ST_DEAD: dead_frames or hurt_frames or idle or [pygame.Surface((fw, fh))],
        }
        for k in self.anims:
            if not self.anims[k] and idle:
                self.anims[k] = idle

    def update(self, hero, platforms, particles, sounds, obstacles=None):
        if self.dead:
            self.death_t += 1
            self._ss(ST_DEAD)
            self._tick_anim()
            self.do_gravity()
            self.do_platforms(platforms)
            return
        if self.hurt_t > 0:
            self.hurt_t -= 1
        if self.cool > 0:
            self.cool -= 1

        # Bounds: patrol only within left_bound..right_bound (set by spawn)
        left_b = getattr(self, 'left_bound', self.ox - self.pat)
        right_b = getattr(self, 'right_bound', self.ox + self.pat)

        dx = hero.rect.centerx - self.rect.centerx
        dist = abs(dx)
        same_level = abs(self.rect.centery - hero.rect.centery) < 100

        if dist < 350 and not hero.dead and same_level:
            self.facing = 1 if dx > 0 else -1
            if dist > 60:
                new_x = self.rect.x + self.facing * self.speed
                new_x = max(left_b, min(right_b, new_x))
                self.rect.x = new_x
                self._ss(ST_WALK)
            else:
                self._ss(ST_ATK)
                if self.cool == 0:
                    self.cool = self.BASE_COOL
                    if hero.take_dmg(self.dmg, particles, RED):
                        snd = sounds.get("hurt")
                        if snd:
                            snd.play()
        else:
            # Patrol: turn at bounds, stay within platform
            new_x = self.rect.x + self.facing * self.speed * 0.6
            if new_x <= left_b:
                self.facing = 1
                self.rect.x = left_b
            elif new_x >= right_b:
                self.facing = -1
                self.rect.x = right_b
            else:
                self.rect.x = new_x
            self._ss(ST_WALK)

        if obstacles:
            self.do_obstacles(obstacles, moving=True, jump_when_facing=False)
        self.do_gravity()
        self.do_platforms(platforms)
        if self.hurt_t > 10:
            self._ss(ST_HURT)
        self._tick_anim()


class IceMonster(SpriteKitEnemy):
    FOLDER = "ice_monster"
    BASE_HP = 75
    BASE_SPD = 2.2
    BASE_DMG = 16

    def __init__(self, x, y):
        super().__init__(x, y)
        self.fc = (80, 180, 220)


class BlueGnome(SpriteKitEnemy):
    FOLDER = "blue_gnome"
    BASE_HP = 65
    BASE_SPD = 2.6
    BASE_DMG = 14

    def __init__(self, x, y):
        super().__init__(x, y)
        self.fc = (30, 100, 180)


class RedGnome(SpriteKitEnemy):
    FOLDER = "red_gnome"
    BASE_HP = 80
    BASE_SPD = 2.7
    BASE_DMG = 18

    def __init__(self, x, y):
        super().__init__(x, y)
        self.fc = (180, 50, 50)


class DarkStagBrown(SpriteKitEnemy):
    """Dark stag enemy from sprite_kit_2d — hero kills with sword (Z)."""
    FOLDER = "dark_stag_brown"
    FW, FH = 80, 100
    BASE_HP = 90
    BASE_SPD = 2.2
    BASE_DMG = 14
    BASE_PAT = 200
    BASE_COOL = 70

    def __init__(self, x, y):
        super().__init__(x, y)
        self.fc = (90, 60, 40)


# ════════════════════════════════════════════════════════════════
#  LEVEL 1 HERO — no ground floor; falling off platforms = death
# ════════════════════════════════════════════════════════════════
class Level1Hero(Hero):
    """Hero for Level 1: same movement as Level 2, no ground floor, world bounds."""
    HEAL_ON_KILL = 18
    MAX_HP = 70

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_hp = self.MAX_HP
        self.hp = self.MAX_HP

    def do_gravity(self):
        self.vy += GRAVITY
        self.rect.y += int(self.vy)
        self.on_ground = False

    def update(self, keys, enemies, platforms, particles, sounds, obstacles=None):
        super().update(keys, enemies, platforms, particles, sounds, obstacles)
        # World bounds — same feel as Level 2
        self.rect.x = max(0, min(self.rect.x, WORLD_W_L1 - self.rect.w))


# ════════════════════════════════════════════════════════════════
#  ICE PLATFORM — uses surface8/surface9 earth tiles (snow on brown layers)
# ════════════════════════════════════════════════════════════════
def _load_earth_tiles():
    """Load surface8 and surface9 earth tiles. Returns (tile1, tile2) for alternating tiling."""
    t1 = t2 = None
    for name in ('level1_ground_surface8.png', 'level1_ground_surface9.png', 'level1_ground.png'):
        path = os.path.join(ASSET_DIR, name)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                if t1 is None:
                    t1 = img
                elif t2 is None:
                    t2 = img
                    break
                else:
                    break
            except Exception:
                pass
    if t1 and t2 is None:
        t2 = t1
    return (t1, t2)


class IcePlatform:
    """Earth platform using surface8/surface9 tiles — snow on layered brown earth. Fall = death."""

    _tiles = None

    def __init__(self, x, y, w):
        if IcePlatform._tiles is None:
            IcePlatform._tiles = _load_earth_tiles()
        t1, t2 = IcePlatform._tiles
        # Normal platform height (28px) — tile scaled to fit, not oversized
        th = 28
        self.rect = pygame.Rect(x, y, w, th)
        self._surf = pygame.Surface((w, th), pygame.SRCALPHA)
        if t1:
            tw1, th1 = t1.get_width(), max(1, t1.get_height())
            t1_scaled = pygame.transform.smoothscale(t1, (tw1, th)) if th1 != th else t1
            if t2 and t2 != t1:
                tw2, th2 = t2.get_width(), max(1, t2.get_height())
                t2_scaled = pygame.transform.smoothscale(t2, (tw2, th)) if th2 != th else t2
            else:
                t2_scaled = t1_scaled
            tx, col = 0, 0
            while tx < w:
                tile = t2_scaled if (col % 2 == 1 and t2_scaled != t1_scaled) else t1_scaled
                twt = tile.get_width()
                self._surf.blit(tile, (tx, 0), (0, 0, min(twt, w - tx), th))
                tx += twt
                col += 1
        else:
            self._surf.fill((180, 210, 235))
            pygame.draw.rect(self._surf, (140, 170, 200), (0, 0, w, th), 2)

    def draw(self, surf, cam):
        rx = int(self.rect.x - cam)
        w = surf.get_width()
        # Use wide margin so long platforms off-screen left still draw
        if -(self.rect.width + 100) < rx < w + 100:
            surf.blit(self._surf, (rx, self.rect.y))


# ════════════════════════════════════════════════════════════════
#  JUMP PLATFORM — moving striped pads (orange/white), enemies on them
# ════════════════════════════════════════════════════════════════
class JumpPlatform:
    """Moving jump pad — brown frame, orange/white stripes. Carries entities."""

    _tile = None

    def __init__(self, x, y, w, left_bound=None, right_bound=None, speed=2.0):
        th = 28
        self.rect = pygame.Rect(x, y, w, th)
        self.left_bound = left_bound if left_bound is not None else x - 60
        self.right_bound = right_bound if right_bound is not None else x + 60
        self.speed = speed
        self.direction = 1
        self.dx = 0
        if JumpPlatform._tile is None:
            path = os.path.join(ASSET_DIR, 'level1_jump_platform.png')
            if os.path.exists(path):
                try:
                    JumpPlatform._tile = pygame.image.load(path).convert_alpha()
                except Exception:
                    pass
        self._surf = pygame.Surface((w, th), pygame.SRCALPHA)
        if JumpPlatform._tile:
            tile = JumpPlatform._tile
            tw, tht = tile.get_width(), max(1, tile.get_height())
            if tht != th:
                tile = pygame.transform.smoothscale(tile, (tw, th))
            tx = 0
            while tx < w:
                self._surf.blit(tile, (tx, 0), (0, 0, min(tw, w - tx), th))
                tx += tw
        else:
            self._surf.fill((255, 180, 80))
            pygame.draw.rect(self._surf, (140, 90, 50), (0, 0, w, th), 2)
        # Solid border so platform reads as one piece on screen
        pygame.draw.rect(self._surf, (120, 75, 40), (0, 0, w, th), 2)

    def update(self):
        """Move platform horizontally; store dx for carrying entities."""
        old_x = self.rect.x
        self.rect.x += int(self.speed * self.direction)
        if self.rect.right >= self.right_bound:
            self.rect.right = self.right_bound
            self.direction = -1
        elif self.rect.left <= self.left_bound:
            self.rect.left = self.left_bound
            self.direction = 1
        self.dx = self.rect.x - old_x

    def draw(self, surf, cam):
        rx = int(self.rect.x - cam)
        w = surf.get_width()
        if -150 < rx < w + 150:
            surf.blit(self._surf, (rx, self.rect.y))


# ════════════════════════════════════════════════════════════════
#  SNOW MOUND — Level 1 obstacle (decorative; not blocking path)
# ════════════════════════════════════════════════════════════════
class SnowMound:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.surf = pygame.Surface((w, h))
        self.surf.fill((230, 240, 255))
        pygame.draw.ellipse(self.surf, (200, 220, 240), (0, 0, w, h))
        pygame.draw.ellipse(self.surf, (255, 255, 255), (2, 2, w - 4, h - 4), 1)

    def draw(self, surf, cam):
        rx = int(self.rect.x - cam)
        w = surf.get_width()
        if -100 < rx < w + 100:
            surf.blit(self.surf, (rx, self.rect.y))


# ════════════════════════════════════════════════════════════════
#  CLUE — restores HP
# ════════════════════════════════════════════════════════════════
class Clue:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 12, y - 12, 24, 24)
        self.collected = False

    def draw(self, surf, cam):
        if self.collected:
            return
        rx = int(self.rect.centerx - cam)
        w = surf.get_width()
        if -50 < rx < w + 50:
            pygame.draw.circle(surf, (255, 220, 100), (rx, self.rect.centery), 10)
            pygame.draw.circle(surf, (255, 180, 50), (rx, self.rect.centery), 7)


# ════════════════════════════════════════════════════════════════
#  GOAL POINTER — warning sign at end of level, on the land
# ════════════════════════════════════════════════════════════════
class GoalPointer:
    """Pointer/warning sign marking the end of the level — stands on the earth platform."""

    def __init__(self, x, y):
        # Sign on pole — hitbox for collision
        self.rect = pygame.Rect(x - 20, y - 70, 40, 80)
        self.surf = None
        path = os.path.join(ASSET_DIR, 'level1_pointer.png')
        if os.path.exists(path):
            try:
                raw = pygame.image.load(path).convert_alpha()
                self.surf = pygame.transform.smoothscale(raw, (50, 90))
            except Exception:
                pass
        if not self.surf:
            self.surf = pygame.Surface((50, 90), pygame.SRCALPHA)
            pygame.draw.polygon(self.surf, (255, 220, 0), [(25, 0), (50, 70), (0, 70)])
            pygame.draw.polygon(self.surf, (40, 30, 20), [(25, 0), (50, 70), (0, 70)], 2)
            pygame.draw.rect(self.surf, (120, 80, 50), (22, 65, 6, 25))

    def draw(self, surf, cam):
        rx = int(self.rect.x - cam)
        w = surf.get_width()
        if -80 < rx < w + 80:
            draw_x = rx + (self.rect.w - self.surf.get_width()) // 2
            draw_y = self.rect.bottom - self.surf.get_height()
            surf.blit(self.surf, (draw_x, draw_y))


# ════════════════════════════════════════════════════════════════
#  LEVEL 1 BACKGROUND — System B: World Background (scrolls with camera)
#  One large image (WORLD_W_L1 x SH), moves with camera, integer cam, single blit.
# ════════════════════════════════════════════════════════════════
def _load_bg(fname):
    path = os.path.join(ASSET_DIR, fname)
    if not os.path.exists(path):
        return None
    try:
        return pygame.image.load(path).convert()
    except Exception:
        return None


def _load_level1_bg(fname):
    """Load background image from assets."""
    path = os.path.join(ASSET_DIR, fname)
    if not os.path.exists(path):
        # Try workspace assets
        _ws_assets = os.path.normpath(os.path.join(_LEVEL1_DIR, '..', '..', '..', '..', 'assets'))
        if os.path.isdir(_ws_assets):
            for f in os.listdir(_ws_assets):
                if 'winter' in f.lower() and f.endswith('.png'):
                    try:
                        return pygame.image.load(os.path.join(_ws_assets, f)).convert()
                    except Exception:
                        pass
        return None
    try:
        return pygame.image.load(path).convert()
    except Exception:
        return None


class Level1Background:
    """Background — scale to 2×SW so seamless parallax scroll with no visible seam."""

    def __init__(self):
        raw = _load_level1_bg('level1_bg.png') or _load_level1_bg('level1_bg.jpg') or _load_level1_bg('winter_village_background.png')
        # Scale image to exactly 2× screen width so tiling wraps invisibly
        if raw:
            self.img = pygame.transform.scale(raw, (SW * 2, SH))
        else:
            self.img = None

    def draw(self, surf, cam):
        if self.img:
            iw = self.img.get_width()          # = SW * 2
            # Slow parallax: background moves at 30% of camera speed
            off = int(cam * 0.3) % iw
            # Two blits are always enough to cover SW pixels
            surf.blit(self.img, (-off, 0))
            if off > 0:
                surf.blit(self.img, (iw - off, 0))
        else:
            surf.fill(DARK_BLU)
            for i in range(60):
                sx = (i * 137 + int(cam)) % SW
                sy = (i * 97) % (SH // 2)
                pygame.draw.circle(surf, WHITE, (sx, sy), 2)


# ════════════════════════════════════════════════════════════════
#  LEVEL 1 GAME
# ════════════════════════════════════════════════════════════════
class Level1Game:
    S_INTRO = 0
    S_PLAY = 1
    S_WIN = 2
    S_OVER = 3

    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        self.screen = pygame.display.set_mode((SW, SH))
        pygame.display.set_caption('Christmas Rescue — Level 1: The Snowy Village')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 22, bold=True)
        self.bfont = pygame.font.SysFont('Arial', 52, bold=True)
        self.sfont = pygame.font.SysFont('Arial', 16)
        self.sounds = make_sounds()
        self._new_game()

    def _new_game(self):
        self.state = self.S_INTRO
        self.cam = 0.0
        self.itimer = 0
        self.score = 0
        self._scored = set()
        # Restart background music
        pygame.mixer.music.play(-1)
        self.bg = Level1Background()
        self.particles = Particles()

        # PROFESSIONAL STATIC PLATFORMS — no shaking, close gaps for easy movement
        low_y = GROUND_Y - 60      # Low platforms
        mid_y = GROUND_Y - 110     # Medium platforms  
        high_y = GROUND_Y - 160    # High platforms

        # All static platforms — smooth, professional, easy jumps (70-90px gaps)
        self.platforms = [
            IcePlatform(  50, low_y,  300),    # Start platform (wide)
            IcePlatform( 420, mid_y,  180),    # Step up
            IcePlatform( 680, low_y,  200),    # Step down
            IcePlatform( 960, mid_y,  180),    # Step up
            IcePlatform(1220, high_y, 160),    # Higher
            IcePlatform(1460, mid_y,  180),    # Step down
            IcePlatform(1720, low_y,  200),    # Lower
            IcePlatform(1990, mid_y,  180),    # Step up
            IcePlatform(2250, low_y,  200),    # Step down
            IcePlatform(2530, mid_y,  180),    # Step up
            IcePlatform(2790, high_y, 160),    # Higher
            IcePlatform(3030, mid_y,  200),    # Step down
            IcePlatform(3310, low_y,  800),    # Final wide platform
        ]

        self.hero = Level1Hero(100, low_y - 100)
        self.obstacles = []

        # Enemies on platforms — spread evenly
        self.enemies = [
            IceMonster(500, mid_y - 80),
            BlueGnome(1040, mid_y - 80),
            RedGnome(1540, mid_y - 80),
            IceMonster(2070, mid_y - 80),
            BlueGnome(2610, mid_y - 80),
            RedGnome(3110, mid_y - 80),
        ]
        # Set patrol bounds for each enemy
        for e in self.enemies:
            e.left_bound = e.rect.x - 80
            e.right_bound = e.rect.x + 80

        # Clues on higher platforms (rewards)
        self.clues = [
            Clue(1300, high_y - 40),
            Clue(2870, high_y - 40),
        ]

        # Goal at end
        self.goal = GoalPointer(3800, low_y - 10)

    def _update_camera(self):
        target = self.hero.rect.centerx - SW // 3
        self.cam += (target - self.cam) * 0.12
        self.cam = max(0.0, min(self.cam, float(WORLD_W_L1 - SW)))

    def update(self):
        keys = pygame.key.get_pressed()
        # Snow in current view (follows camera)
        cam_i = int(self.cam)
        if random.random() < 0.5:
            self.particles.snow(2, cam_i)
        else:
            self.particles.snow(1, cam_i)

        if self.state == self.S_INTRO:
            self.itimer += 1
            key_pressed = any(keys[k] for k in (
                pygame.K_SPACE, pygame.K_RETURN, pygame.K_UP, pygame.K_DOWN,
                pygame.K_LEFT, pygame.K_RIGHT, pygame.K_w, pygame.K_a,
                pygame.K_s, pygame.K_d, pygame.K_z, pygame.K_r
            ))
            if self.itimer > 180 or key_pressed:
                self.state = self.S_PLAY
            return

        if self.state == self.S_WIN:
            self._win_timer = getattr(self, '_win_timer', 0) + 1
            return

        if self.state == self.S_OVER:
            self._death_timer = getattr(self, '_death_timer', 0) + 1
            if self._death_timer >= 90:  # ~1.5 sec death display, then auto-restart
                self._new_game()
            return

        # Update hero (all platforms are static — no shaking)
        self.hero.update(keys, self.enemies, self.platforms, self.particles, self.sounds, self.obstacles)

        # Fall death — no ground floor; falling off platforms kills the player
        if self.hero.rect.top > SH + 50:
            self.hero.dead = True
            self.hero.death_t = 0
            self.hero._ss(ST_DEAD)

        for e in self.enemies:
            e.update(self.hero, self.platforms, self.particles, self.sounds, self.obstacles)
            if e.dead and id(e) not in self._scored:
                self._scored.add(id(e))
                self.score += 80
                self.hero.heal(type(self.hero).HEAL_ON_KILL)
                snd = self.sounds.get('heal')
                if snd:
                    snd.play()

        self.enemies = [e for e in self.enemies if not e.dead or e.death_t < 50]

        for c in self.clues:
            if not c.collected and self.hero.rect.colliderect(c.rect):
                c.collected = True
                self.hero.heal(22)
                self.particles.burst(c.rect.centerx, c.rect.centery,
                                    (255, 220, 100), n=12, spd=5, life=25)
                snd = self.sounds.get('heal')
                if snd:
                    snd.play()

        if self.hero.rect.colliderect(self.goal.rect):
            self.state = self.S_WIN
            self._win_timer = 0
            pygame.mixer.music.stop()
            snd = self.sounds.get('win')
            if snd:
                snd.play()

        if self.hero.dead:
            self.state = self.S_OVER
            self._death_timer = 0
            # Stop background music and play death sound
            pygame.mixer.music.stop()
            snd = self.sounds.get('death')
            if snd:
                snd.play()

        self._update_camera()

    def draw(self):
        cam = int(self.cam)
        # Single background scrolls with camera — no tiling
        self.bg.draw(self.screen, cam)
        for p in self.platforms:
            p.draw(self.screen, cam)
        for obs in self.obstacles:
            obs.draw(self.screen, cam)
        for c in self.clues:
            c.draw(self.screen, cam)
        self.goal.draw(self.screen, cam)
        for e in self.enemies:
            e.draw(self.screen, cam)
        self.hero.draw(self.screen, cam)
        self.particles.update_draw(self.screen, cam)

        # HUD
        panel = pygame.Surface((320, 65), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        self.screen.blit(panel, (8, 8))
        draw_hpbar(self.screen, 18, 16, 180, 16, self.hero.hp, self.hero.max_hp)
        hp_col = (100, 220, 100) if self.hero.hp > self.hero.max_hp // 2 else (255, 200, 0) if self.hero.hp > self.hero.max_hp // 4 else RED
        self.screen.blit(self.sfont.render(f'HP  {self.hero.hp}/{self.hero.max_hp}', True, hp_col), (210, 18))
        self.screen.blit(self.sfont.render('Level 1 — Snowy Village', True, SNOW), (18, 40))
        self.screen.blit(self.sfont.render(f'Score: {self.score}', True, GOLD), (220, 42))
        ctrl = self.sfont.render('Arrows/WASD Move   SPACE Jump   Z Sword   Defeat enemies, reach the sign', True, (180, 180, 180))
        self.screen.blit(ctrl, (SW // 2 - ctrl.get_width() // 2, SH - 24))

        if self.state == self.S_INTRO:
            overlay = pygame.Surface((SW, SH))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(min(255, 280 - self.itimer))
            self.screen.blit(overlay, (0, 0))
            for i, line in enumerate(LEVEL1_INTRO):
                y = 110 + i * 50
                t = self.sfont.render(line, True, (220, 220, 230))
                self.screen.blit(t, (SW // 2 - t.get_width() // 2, y))
            if self.itimer > 60:
                t = self.sfont.render('Press any key to begin', True, GOLD)
                self.screen.blit(t, (SW // 2 - t.get_width() // 2, 440))

        elif self.state == self.S_WIN:
            wt = getattr(self, '_win_timer', 0)
            alpha = min(200, wt * 3)
            overlay = pygame.Surface((SW, SH))
            overlay.set_alpha(alpha)
            overlay.fill((10, 15, 35))
            self.screen.blit(overlay, (0, 0))
            # Simple, clear win message
            title = self.bfont.render('YOU WIN LEVEL ONE', True, GOLD)
            self.screen.blit(title, (SW // 2 - title.get_width() // 2, 240))
            score_txt = self.font.render(f'Score: {self.score}', True, WHITE)
            self.screen.blit(score_txt, (SW // 2 - score_txt.get_width() // 2, 320))
            hint = self.sfont.render('Press ENTER for Level 2   |   ESC to quit', True, (200, 200, 210))
            self.screen.blit(hint, (SW // 2 - hint.get_width() // 2, 380))

        elif self.state == self.S_OVER:
            overlay = pygame.Surface((SW, SH))
            overlay.set_alpha(200)
            overlay.fill((50, 0, 0))
            self.screen.blit(overlay, (0, 0))
            self.screen.blit(self.bfont.render('The snow covers those who fall.', True, RED), (SW // 2 - 260, 250))
            self.screen.blit(self.sfont.render('Restarting...  |  ESC to quit', True, WHITE), (SW // 2 - 140, 350))

    def run(self):
        while True:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_r and self.state == self.S_OVER:
                        self._new_game()
                    if event.key == pygame.K_RETURN and self.state == self.S_WIN:
                        return True
            self.update()
            self.draw()
            pygame.display.flip()


if __name__ == '__main__':
    Level1Game().run()
