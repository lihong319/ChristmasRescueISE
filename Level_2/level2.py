"""
CHRISTMAS RESCUE — LEVEL 2: THE DARK FOREST (Extended Edition)
ISE Assignment CT029-3-2

Controls
--------
Move        : Arrow Keys / WASD
Jump        : SPACE / W / UP
Attack      : Z   (combo)
Dash        : LSHIFT (short burst; cooldown)
Interact    : E   (read signs / checkpoints)
Pause       : P
Restart     : R   (after WIN / GAME OVER)
Quit        : ESC

Assets (place inside ./assets)
------------------------------
background.jpg

hero_idle.png   hero_walk.png   hero_run.png   hero_jump.png
hero_attack.png hero_hurt.png

gnome_green_idle.png   gnome_green_walk.png   gnome_green_attack.png
gnome_green_hurt.png   gnome_green_dead.png

gnome_red_idle.png     gnome_red_walk.png     gnome_red_attack.png
gnome_red_hurt.png     gnome_red_dead.png

biscuit: Biscuit_stand.png  Biscuit_Walking.png  Biscuit_Attacking.png
Biscuit_Taking_Damage.png  Biscuit_Fainting.png  Biscuit_Swimming.png (optional)

darksanta_idle.png     darksanta_walk.png     darksanta_run.png
darksanta_attack.png   darksanta_attack .png  (some projects contain a space)
darksanta_hurt.png     darksanta_dead.png

child.png
obstacle.png

Audio (optional)
----------------
edr-8-bit-jump-001-171817.mp3
freesound_community-punch-2-37333.mp3
magiaz-baby-crying-327495.mp3
u_9vcmnl4trh-ready-to-fight-474973.mp3
u_fmwa6xhlx8-fight-2923... (any additional tracks will be auto-detected)

Notes
-----
• The game is intentionally self‑contained in ONE file for printing.
• If assets are missing, the game falls back to coloured shapes & synthesized tones.
• This "Extended Edition" adds: coins, checkpoints, gates, dark zones, traps,
  dash/combo, achievements, pause/options, and a longer level.

"""
from __future__ import annotations

import os
import sys
import math
import json
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Set

import pygame

# Optional story import
try:
    from story import (
        INTRO_NARRATION, BOSS_MONOLOGUE, VICTORY_SPEECH,
        GAME_OVER_LINE1, GAME_OVER_LINE2,
        LORE_GREEN_GNOMES, LORE_RED_GNOMES, LORE_EVIL_BISCUIT, LORE_DARK_SANTA,
    )
except Exception:
    INTRO_NARRATION = [
        "The Dark Forest awaits.",
        "Children have been taken.",
        "Rescue them before the last bell fades.",
        "Press any key to begin.",
    ]
    BOSS_MONOLOGUE = [
        "You should not have come here...",
        "This forest belongs to ME.",
        "The children will NEVER be freed!",
    ]
    VICTORY_SPEECH = [
        "The children are free.",
        "The forest can heal.",
        "No one else will be taken.",
        "Not while I draw breath.",
    ]
    GAME_OVER_LINE1 = "The snow covers those who fall."
    GAME_OVER_LINE2 = "The children still wait."
    LORE_GREEN_GNOMES = (
        "Green gnomes are woodland scavengers. They fight in packs, "
        "using quick jabs and dirty tricks to protect their burrows."
    )
    LORE_RED_GNOMES = (
        "Red gnomes are enforcers. Stronger, faster, and far more aggressive, "
        "they chase intruders deep into the pines."
    )
    LORE_EVIL_BISCUIT = (
        "The Evil Biscuit is not a snack — it is a curse. Baked from bitterness, "
        "it sprints with surprising rage and hits like a brick."
    )
    LORE_DARK_SANTA = (
        "Dark Santa is the shadow of a joyful legend — a spirit of winter without warmth. "
        "He hoards laughter and locks away children’s hope."
    )

# Config
SW, SH = 1280, 640
FPS = 60

GRAVITY = 0.55
JUMP_VEL = -14.0
GROUND_Y = SH - 110

# Bigger world to feel like a "level"
WORLD_W = 9000

# Colours
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

RED = (220, 30, 30)
BLOOD = (180, 15, 25)

DARK_BLU = (12, 18, 45)
GOLD = (255, 195, 0)
ORANGE = (255, 130, 0)
CYAN = (80, 220, 255)
SNOW = (220, 235, 255)
PURPLE = (150, 120, 255)
GREEN = (50, 220, 90)

# States
ST_IDLE = "idle"
ST_WALK = "walk"
ST_RUN = "run"
ST_JUMP = "jump"
ST_ATK = "attack"
ST_HURT = "hurt"
ST_DEAD = "dead"

# Knockout special move cooldown (frames)
KO_COOLDOWN = 600   # 10 seconds at 60 FPS

# Assets
ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save_dark_forest.json")

def clamp(v: float, a: float, b: float) -> float:
    return a if v < a else b if v > b else v

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def safe_color(c) -> Tuple[int, int, int]:
    return (int(c[0]) & 255, int(c[1]) & 255, int(c[2]) & 255)

def play_sfx(sfx, name: str):
    snd = sfx.get(name)
    if snd: snd.play()

def try_path(*names: str) -> Optional[str]:
    """Return first existing path inside ASSET_DIR for any filename in names."""
    for n in names:
        p = os.path.join(ASSET_DIR, n)
        if os.path.exists(p):
            return p
    return None

def find_by_contains(substrs: List[str], exts: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".mp3", ".wav", ".ogg")) -> Optional[str]:
    """Search assets directory for any file that contains all substrings (case-insensitive)."""
    if not os.path.isdir(ASSET_DIR):
        return None
    want = [s.lower() for s in substrs]
    for fn in os.listdir(ASSET_DIR):
        low = fn.lower()
        if low.endswith(exts) and all(s in low for s in want):
            return os.path.join(ASSET_DIR, fn)
    return None

def load_image(fname: str, alpha: bool = True, scale: Optional[Tuple[int, int]] = None) -> Optional[pygame.Surface]:
    """Load image from assets; supports small filename mistakes and case-insensitive match."""
    path = try_path(fname, fname.replace(" .", "."), fname.replace(".png", " .png"))
    if not path and os.path.isdir(ASSET_DIR):
        low = fname.lower()
        for fn in os.listdir(ASSET_DIR):
            if fn.lower() == low or fn.lower() == low.replace(" ", ""):
                path = os.path.join(ASSET_DIR, fn)
                break
    if not path:
        return None
    try:
        img = pygame.image.load(path)
        img = img.convert_alpha() if alpha else img.convert()
        if scale:
            img = pygame.transform.smoothscale(img, scale)
        return img
    except Exception:
        return None

def slice_sheet_grid(sheet: pygame.Surface, cols: int, rows: int) -> List[pygame.Surface]:
    w, h = sheet.get_width(), sheet.get_height()
    cw, ch = max(1, w // cols), max(1, h // rows)
    out: List[pygame.Surface] = []
    for r in range(rows):
        for c in range(cols):
            f = pygame.Surface((cw, ch), pygame.SRCALPHA)
            f.blit(sheet, (0, 0), (c * cw, r * ch, cw, ch))
            out.append(f)
    return out

def load_strip(fname: str, num_frames: int, tgt_h: int, inset_clear: bool = True, crop: bool = True) -> List[pygame.Surface]:
    img = load_image(fname, alpha=True)
    if img is None:
        return []
    w, h = img.get_width(), img.get_height()
    fw = max(1, w // num_frames)
    frames: List[pygame.Surface] = []
    for i in range(num_frames):
        sx = i * fw
        if sx + fw > w:
            break
        f = pygame.Surface((fw, h), pygame.SRCALPHA)
        f.blit(img, (0, 0), (sx, 0, fw, h))
        if inset_clear:
            inset = max(2, fw // 16)
            for ix in range(inset):
                for iy in range(h):
                    f.set_at((ix, iy), (0, 0, 0, 0))
                    f.set_at((fw - 1 - ix, iy), (0, 0, 0, 0))
        if crop:
            mask = pygame.mask.from_surface(f, 10)
            bboxes = mask.get_bounding_rects()
            if bboxes:
                r = bboxes[0]
                for br in bboxes[1:]:
                    r.union_ip(br)
                cropped = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                cropped.blit(f, (0, 0), r)
                f = cropped
        cw, ch = f.get_size()
        if ch > 0:
            scale = tgt_h / ch
            nw = max(8, int(cw * scale))
            f = pygame.transform.smoothscale(f, (nw, tgt_h))
        frames.append(f)
    return frames

# Save / options
@dataclass
class Options:
    music_vol: float = 0.45
    sfx_vol: float = 0.65
    fullscreen: bool = False
    show_fps: bool = False

@dataclass
class SaveData:
    highscore: int = 0
    options: Options = field(default_factory=Options)


def load_save() -> SaveData:
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        opt = data.get("options", {})
        return SaveData(
            highscore=int(data.get("highscore", 0)),
            options=Options(
                music_vol=float(opt.get("music_vol", 0.45)),
                sfx_vol=float(opt.get("sfx_vol", 0.65)),
                fullscreen=bool(opt.get("fullscreen", False)),
                show_fps=bool(opt.get("show_fps", False)),
            )
        )
    except Exception:
        return SaveData()

def save_save(sd: SaveData) -> None:
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "highscore": int(sd.highscore),
                "options": {
                    "music_vol": float(sd.options.music_vol),
                    "sfx_vol": float(sd.options.sfx_vol),
                    "fullscreen": bool(sd.options.fullscreen),
                    "show_fps": bool(sd.options.show_fps),
                }
            }, f, indent=2)
    except Exception:
        pass

# Input helper
class Input:
    """Track held keys (pygame.key.get_pressed) AND just-pressed keys per frame."""
    def __init__(self):
        self.just_pressed: Set[int] = set()

    def begin_frame(self):
        self.just_pressed.clear()

    def feed_event(self, e: pygame.event.Event):
        if e.type == pygame.KEYDOWN:
            self.just_pressed.add(e.key)

    def pressed(self, key: int) -> bool:
        return key in self.just_pressed

# Camera with shake
class Camera:
    def __init__(self):
        self.x = 0.0
        self.shake_t = 0
        self.shake_mag = 0.0
        self.shake_dx = 0.0
        self.shake_dy = 0.0

    def add_shake(self, mag: float, frames: int = 14):
        self.shake_mag = max(self.shake_mag, mag)
        self.shake_t = max(self.shake_t, frames)

    def update(self):
        if self.shake_t > 0:
            self.shake_t -= 1
            self.shake_dx = random.uniform(-self.shake_mag, self.shake_mag)
            self.shake_dy = random.uniform(-self.shake_mag, self.shake_mag)
            self.shake_mag *= 0.92
        else:
            self.shake_dx = 0.0
            self.shake_dy = 0.0
            self.shake_mag = 0.0

    def world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        return int(x - self.x + self.shake_dx), int(y + self.shake_dy)

# Particle system
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    col: Tuple[int, int, int]
    life: int
    max_life: int
    r: int

class Particles:
    MAX_PARTICLES = 900

    def __init__(self):
        self.p: List[Particle] = []

    def _budget(self, n: int) -> int:
        return max(0, min(n, self.MAX_PARTICLES - len(self.p)))

    def burst(self, x, y, col, n=12, spd=5, life=28, r=4, vy_bias=-1.5):
        col = safe_color(col)
        for _ in range(self._budget(n)):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(1.0, float(spd))
            self.p.append(Particle(float(x), float(y), math.cos(a) * s, math.sin(a) * s + vy_bias, col, int(life), int(life), int(r)))

    def blood(self, x, y, n=22):
        for _ in range(self._budget(n)):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(2.0, 7.5)
            r = random.randint(120, 220)
            g = random.randint(5, 30)
            b = random.randint(10, 40)
            self.p.append(Particle(float(x), float(y), math.cos(a) * s, math.sin(a) * s - 1.2, (r, g, b), 24, 24, random.randint(2, 4)))

    def snow(self, cam_x: float, n=3):
        for _ in range(self._budget(n)):
            wx = cam_x + random.uniform(-20, SW + 20)
            self.p.append(Particle(wx, -6.0, random.uniform(-0.3, 0.3), random.uniform(0.3, 0.8), SNOW, random.randint(300, 500), random.randint(300, 500), random.randint(2, 3)))

    def embers(self, x, y, n=10):
        for _ in range(self._budget(n)):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(0.8, 3.5)
            self.p.append(Particle(float(x), float(y), math.cos(a) * s, math.sin(a) * s - 2.5, ORANGE, random.randint(26, 46), random.randint(26, 46), random.randint(2, 3)))

    def update(self):
        live: List[Particle] = []
        for pt in self.p:
            pt.x += pt.vx
            pt.y += pt.vy
            if pt.col == SNOW:
                pt.vy += 0.02
                if pt.y >= GROUND_Y:
                    pt.life = 0
            else:
                pt.vy += 0.18
            pt.life -= 1
            if pt.life > 0:
                live.append(pt)
        self.p = live[-self.MAX_PARTICLES:]

    def draw(self, surf: pygame.Surface, cam: Camera):
        for pt in self.p:
            sx = int(pt.x - cam.x + cam.shake_dx)
            sy = int(pt.y + cam.shake_dy)
            if -10 <= sx <= SW + 10:
                a = max(0.0, min(1.0, pt.life / max(1, pt.max_life)))
                col = (min(255, int(pt.col[0] * a)), min(255, int(pt.col[1] * a)), min(255, int(pt.col[2] * a)))
                pygame.draw.circle(surf, col, (sx, sy), pt.r)

# Float texts and toasts (achievements)
class FloatText:
    def __init__(self, x, y, text, col, font):
        self.x = float(x)
        self.y = float(y)
        self.text = str(text)
        self.col = safe_color(col)
        self.font = font
        self.life = 70

    def update(self) -> bool:
        self.y -= 0.9
        self.life -= 1
        return self.life > 0

    def draw(self, surf: pygame.Surface, cam: Camera):
        a = max(0, int(255 * self.life / 70))
        s = self.font.render(self.text, True, self.col)
        s.set_alpha(a)
        sx, sy = cam.world_to_screen(self.x, self.y)
        surf.blit(s, (sx - s.get_width() // 2, sy))

class Toast:
    def __init__(self, title: str, body: str, col: Tuple[int, int, int], font_big, font_small, life: int = 220):
        self.title = title
        self.body = body
        self.col = safe_color(col)
        self.font_big = font_big
        self.font_small = font_small
        self.life = life
        self.max_life = life

    def update(self) -> bool:
        self.life -= 1
        return self.life > 0

    def draw(self, surf: pygame.Surface, x: int, y: int):
        # Slide in/out
        t = 1.0 - self.life / max(1, self.max_life)
        slide = 0
        if t < 0.12:
            slide = int(lerp(-380, 0, t / 0.12))
        elif self.life < 40:
            slide = int(lerp(0, -380, (40 - self.life) / 40))
        px = x + slide
        w, h = 360, 68
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 190), (0, 0, w, h), border_radius=12)
        pygame.draw.rect(panel, (*self.col, 220), (0, 0, w, h), 2, border_radius=12)

        tt = self.font_big.render(self.title, True, self.col)
        bt = self.font_small.render(self.body, True, (230, 230, 240))
        panel.blit(tt, (12, 8))
        panel.blit(bt, (12, 36))
        surf.blit(panel, (px, y))


class EnemyEncounterPopup:
    """Horizontal bar in the ground area shown once per enemy type.
    Left: enemy sprite + name/lore.  Right: hero reply."""

    LORE_MAP = {
        "green_gnome": ("GREEN GNOME", LORE_GREEN_GNOMES, (100, 220, 120),
                        "Small but many... I've seen packs like this before. "
                        "Stay sharp — they bite harder than they look and they never fight alone."),
        "red_gnome":   ("RED GNOME",   LORE_RED_GNOMES,   (220, 100, 100),
                        "Rage burns in their eyes — these aren't like the green ones. "
                        "I need to watch my step. One wrong move and they'll overwhelm me."),
        "evil_biscuit":("EVIL BISCUIT", LORE_EVIL_BISCUIT, (200, 150, 80),
                        "A cursed gingerbread walking on its own... this forest keeps getting darker. "
                        "Whatever magic twisted it, I can feel the anger radiating from it."),
        "dark_santa":  ("DARK SANTA",  LORE_DARK_SANTA,   (180, 50, 50),
                        "So you're the one who stole the children and buried their laughter in ice. "
                        "I've fought through your forest and your monsters. It ends here, tonight."),
    }

    def __init__(self, enemy_key: str, sprite: Optional[pygame.Surface],
                 hero_sprite: Optional[pygame.Surface],
                 font_big, font_small, life: int = 300):
        info = self.LORE_MAP.get(enemy_key, ("UNKNOWN", "", (200, 200, 200), "..."))
        self.name = info[0]
        self.lore = info[1]
        self.col = safe_color(info[2])
        self.hero_reply = info[3]
        self.sprite = sprite
        self.hero_sprite = hero_sprite
        self.font_big = font_big
        self.font_small = font_small
        self.life = life
        self.max_life = life

    def update(self) -> bool:
        self.life -= 1
        return self.life > 0

    def draw(self, surf: pygame.Surface):
        progress = 1.0 - self.life / max(1, self.max_life)
        alpha = 255
        if progress < 0.08:
            alpha = int(255 * progress / 0.08)
        elif self.life < 50:
            alpha = int(255 * self.life / 50)

        pw, ph = SW - 40, 94
        px = 20
        py = GROUND_Y + 6

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (8, 8, 20, min(230, alpha)), (0, 0, pw, ph), border_radius=10)
        pygame.draw.rect(panel, (*self.col, min(220, alpha)), (0, 0, pw, ph), 2, border_radius=10)

        sp_w_used = 0
        if self.sprite:
            sp = self.sprite
            sp_h = ph - 12
            sp_w = max(1, int(sp.get_width() * sp_h / max(1, sp.get_height())))
            sp_scaled = pygame.transform.smoothscale(sp, (sp_w, sp_h))
            if alpha < 255:
                sp_scaled.set_alpha(alpha)
            panel.blit(sp_scaled, (8, 6))
            sp_w_used = sp_w + 14

        text_x = 8 + sp_w_used
        half_w = pw // 2
        name_surf = self.font_big.render(self.name, True, self.col)
        if alpha < 255:
            name_surf.set_alpha(alpha)
        panel.blit(name_surf, (text_x, 6))

        max_tw = half_w - text_x - 10
        words = self.lore.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.font_small.size(test)[0] <= max_tw:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        ly = 30
        for ln in lines[:3]:
            t = self.font_small.render(ln, True, (210, 210, 225))
            if alpha < 255:
                t.set_alpha(alpha)
            panel.blit(t, (text_x, ly))
            ly += 16

        sep_x = half_w
        pygame.draw.line(panel, (*self.col, min(120, alpha)), (sep_x, 8), (sep_x, ph - 8), 1)

        reply_delay = 0.15
        if progress > reply_delay:
            rx = sep_x + 12
            hero_sp_w = 0
            if self.hero_sprite:
                hsp = self.hero_sprite
                hsp_h = ph - 16
                hsp_w = max(1, int(hsp.get_width() * hsp_h / max(1, hsp.get_height())))
                hsp_scaled = pygame.transform.smoothscale(hsp, (hsp_w, hsp_h))
                if alpha < 255:
                    hsp_scaled.set_alpha(alpha)
                panel.blit(hsp_scaled, (pw - hsp_w - 10, 8))
                hero_sp_w = hsp_w + 14

            hero_label = self.font_big.render("HERO", True, GOLD)
            if alpha < 255:
                hero_label.set_alpha(alpha)
            panel.blit(hero_label, (rx, 6))

            max_reply_w = pw - rx - hero_sp_w - 16
            rwords = self.hero_reply.split()
            rlines, rcur = [], ""
            for rw in rwords:
                rtest = (rcur + " " + rw).strip()
                if self.font_small.size(rtest)[0] <= max_reply_w:
                    rcur = rtest
                else:
                    if rcur:
                        rlines.append(rcur)
                    rcur = rw
            if rcur:
                rlines.append(rcur)
            rly = 30
            for rl in rlines[:3]:
                rt = self.font_small.render(rl, True, (230, 230, 200))
                if alpha < 255:
                    rt.set_alpha(alpha)
                panel.blit(rt, (rx, rly))
                rly += 16

        surf.blit(panel, (px, py))


# Environment
class Platform:
    def __init__(self, x, y, w, h=18):
        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))

    def draw(self, surf: pygame.Surface, cam: Camera):
        rx = self.rect.x - int(cam.x + cam.shake_dx)
        if rx > SW or rx + self.rect.w < 0:
            return
        pygame.draw.rect(surf, (80, 50, 25), (rx, self.rect.y, self.rect.w, self.rect.h), border_radius=4)
        pygame.draw.rect(surf, SNOW, (rx, self.rect.y, self.rect.w, 5), border_radius=4)
        pygame.draw.rect(surf, (255, 255, 255, 90), (rx, self.rect.y, self.rect.w, self.rect.h), 2, border_radius=4)

OBSTACLE_W, OBSTACLE_H = 72, 110  # collision hitbox

class Obstacle:
    _sheet: Optional[List[pygame.Surface]] = None
    TOUCH_DMG = 8       # damage per hit when player walks into it
    TOUCH_COOL = 28     # frames of invincibility between hits

    def __init__(self, x, y, frame_index=0):
        self.rect = pygame.Rect(int(x), int(y), OBSTACLE_W, OBSTACLE_H)
        self.frame_index = int(frame_index)
        self.cooldown = 0

    def update(self, hero, particles, sfx):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.rect.colliderect(hero.rect) and self.cooldown == 0:
            if hero.take_dmg(self.TOUCH_DMG, particles, ORANGE):
                self.cooldown = self.TOUCH_COOL
                play_sfx(sfx, "hurt")

    @classmethod
    def ensure_sheet(cls):
        if cls._sheet is not None:
            return
        # Load individual obstacle images (Obstacle1.png through Obstacle9.png)
        frames = []
        for i in range(1, 10):
            img = load_image(f"Obstacle{i}.png", alpha=True)
            if img is not None:
                frames.append(img)
        if not frames:
            # Fallback: try old sheet
            img = load_image("obstacle.png", alpha=True)
            if img is None:
                cls._sheet = []
                return
            frames = slice_sheet_grid(img, cols=5, rows=2)
        # pre-scale each frame to fit OBSTACLE_H while keeping aspect ratio
        scaled = []
        for f in frames:
            fw, fh = f.get_size()
            if fh < 1:
                scaled.append(f)
                continue
            s = OBSTACLE_H / fh
            nw, nh = max(8, int(fw * s)), OBSTACLE_H
            scaled.append(pygame.transform.smoothscale(f, (nw, nh)))
        cls._sheet = scaled

    def draw(self, surf: pygame.Surface, cam: Camera):
        Obstacle.ensure_sheet()
        rx = self.rect.x - int(cam.x + cam.shake_dx)
        if rx > SW or rx + self.rect.w < 0:
            return
        if not Obstacle._sheet:
            pygame.draw.rect(surf, (110, 70, 45), (rx, self.rect.y, self.rect.w, self.rect.h), border_radius=6)
            pygame.draw.rect(surf, (255, 255, 255), (rx, self.rect.y, self.rect.w, self.rect.h), 2, border_radius=6)
            return
        idx = self.frame_index % len(Obstacle._sheet)
        img = Obstacle._sheet[idx]
        iw, ih = img.get_size()
        by = self.rect.bottom - ih
        surf.blit(img, (rx + (OBSTACLE_W - iw) // 2, by))

# Hazards
class SpikeTrap:
    def __init__(self, x: int, count: int = 4):
        self.x = int(x)
        self.count = int(count)
        self.w = self.count * 22
        self.h = 24
        self.rect = pygame.Rect(self.x, GROUND_Y - self.h, self.w, self.h)
        self.cooldown = 0

    def update(self, hero, particles, sfx):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.rect.colliderect(hero.rect) and self.cooldown == 0:
            if hero.take_dmg(7, particles, CYAN):
                self.cooldown = 22
                play_sfx(sfx, "hurt")

    def draw(self, surf: pygame.Surface, cam: Camera):
        rx = self.x - int(cam.x + cam.shake_dx)
        if rx > SW or rx + self.w < 0:
            return
        for i in range(self.count):
            cx = rx + i * 22 + 11
            pts = [(cx - 9, GROUND_Y), (cx + 9, GROUND_Y), (cx, GROUND_Y - 22)]
            pygame.draw.polygon(surf, (170, 170, 210), pts)
            pygame.draw.polygon(surf, (255, 255, 255), pts, 1)

class PendulumHazard:
    def __init__(self, x, y=50, length=160, speed=1.8):
        self.px = float(x)
        self.py = float(y)
        self.len = float(length)
        self.speed = float(speed)
        self.angle = 0.0

    def ball_pos(self) -> Tuple[float, float]:
        return (self.px + math.sin(self.angle) * self.len,
                self.py + math.cos(self.angle) * self.len)

    def rect(self) -> pygame.Rect:
        bx, by = self.ball_pos()
        return pygame.Rect(int(bx - 16), int(by - 16), 32, 32)

    def update(self, hero, particles, sfx):
        self.angle += self.speed * math.pi / 180.0
        if self.rect().colliderect(hero.rect):
            if hero.take_dmg(16, particles, ORANGE):
                play_sfx(sfx, "hurt")

    def draw(self, surf: pygame.Surface, cam: Camera):
        bx, by = self.ball_pos()
        px = int(self.px - cam.x + cam.shake_dx)
        py = int(self.py + cam.shake_dy)
        sx = int(bx - cam.x + cam.shake_dx)
        sy = int(by + cam.shake_dy)
        # cull by pivot x (the fixed anchor point) so pendulums don't appear from far away
        if px < -80 or px > SW + 80:
            return
        pygame.draw.line(surf, (120, 100, 80), (px, py), (sx, sy), 4)
        # glowing Christmas ornament instead of plain circle
        glow = pygame.Surface((48, 48), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 180, 60, 50), (24, 24), 22)
        surf.blit(glow, (sx - 24, sy - 24))
        pygame.draw.circle(surf, (180, 50, 40), (sx, sy), 12)
        pygame.draw.circle(surf, (220, 80, 50), (sx, sy - 3), 6)
        pygame.draw.circle(surf, (255, 220, 100, 180), (sx - 3, sy - 5), 3)
        pygame.draw.rect(surf, (160, 140, 100), (sx - 4, sy - 16, 8, 6))
        pygame.draw.circle(surf, (200, 160, 120), (sx, sy), 12, 2)

class RollingSnowball:
    def __init__(self, x, vx=-3.7):
        self.x = float(x)
        self.y = float(GROUND_Y - 30)
        self.r = 30
        self.vx = float(vx)
        self.alive = True
        self.spin = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.r), int(self.y - self.r), self.r * 2, self.r * 2)

    def update(self, hero, particles, sfx):
        if not self.alive:
            return
        self.x += self.vx
        self.spin += 0.25
        if self.x < -200 or self.x > WORLD_W + 200:
            self.alive = False
            return
        if self.rect.colliderect(hero.rect):
            if hero.take_dmg(12, particles, SNOW):
                play_sfx(sfx, "hurt")

    def draw(self, surf: pygame.Surface, cam: Camera):
        if not self.alive:
            return
        sx = int(self.x - cam.x + cam.shake_dx)
        sy = int(self.y + cam.shake_dy)
        if sx < -80 or sx > SW + 80:
            return
        pygame.draw.circle(surf, (200, 225, 255), (sx, sy), self.r)
        pygame.draw.circle(surf, (255, 255, 255), (sx, sy), self.r, 2)
        # simple spokes
        for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
            ang = a + self.spin
            ex = sx + int(math.cos(ang) * self.r * 0.7)
            ey = sy + int(math.sin(ang) * self.r * 0.7)
            pygame.draw.line(surf, (160, 195, 230), (sx, sy), (ex, ey), 2)

# Pickups & gameplay objects
class Coin:
    def __init__(self, x, y):
        self.x = float(x)
        self.base_y = float(y)
        self.y = float(y)
        self.t = random.uniform(0, 60)
        self.alive = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 12), int(self.y - 12), 24, 24)

    def update(self, hero, score_ref: Dict[str, int], floats: List[FloatText], particles: Particles, font, sfx):
        """Only the hero can collect coins; NPCs run over them and cannot collect."""
        if not self.alive:
            return
        self.t += 1.0
        self.y = self.base_y + math.sin(self.t * 0.07) * 5
        # Only the hero collects - NPCs run over coins but cannot collect
        if hero is not None and self.rect.colliderect(hero.rect):
            self.alive = False
            score_ref["score"] += 25
            floats.append(FloatText(self.x, self.y - 20, "+25", GOLD, font))
            particles.burst(self.x, self.y, GOLD, n=10, spd=3, life=20, r=3)
            play_sfx(sfx, "coin")

    def draw(self, surf: pygame.Surface, cam: Camera):
        if not self.alive:
            return
        sx = int(self.x - cam.x + cam.shake_dx)
        sy = int(self.y + cam.shake_dy)
        if sx < -50 or sx > SW + 50:
            return
        pygame.draw.circle(surf, GOLD, (sx, sy), 11)
        pygame.draw.circle(surf, (255, 235, 120), (sx, sy), 11, 2)
        pygame.draw.circle(surf, (255, 250, 180), (sx - 3, sy - 3), 4)

class Potion:
    def __init__(self, x, y, heal=40):
        self.x = float(x)
        self.y = float(y)
        self.heal = int(heal)
        self.alive = True
        self.bob = random.uniform(0, 60)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 14), int(self.y - 20), 28, 40)

    def update(self, hero, floats, particles, font, sfx):
        if not self.alive:
            return
        self.bob += 1.0
        yy = self.y + math.sin(self.bob * 0.07) * 3
        if pygame.Rect(int(self.x - 14), int(yy - 20), 28, 40).colliderect(hero.rect):
            self.alive = False
            hero.heal(self.heal)
            floats.append(FloatText(self.x, yy - 20, f"+{self.heal} HP", GREEN, font))
            particles.burst(self.x, yy, GREEN, n=10, spd=3, life=20, r=3)
            play_sfx(sfx, "heal")

    def draw(self, surf: pygame.Surface, cam: Camera):
        if not self.alive:
            return
        sx = int(self.x - cam.x + cam.shake_dx)
        sy = int(self.y + math.sin(self.bob * 0.07) * 3 + cam.shake_dy)
        pygame.draw.rect(surf, (20, 30, 40), (sx - 10, sy - 18, 20, 30), border_radius=6)
        pygame.draw.rect(surf, GREEN, (sx - 8, sy - 8, 16, 18), border_radius=6)
        pygame.draw.rect(surf, WHITE, (sx - 10, sy - 18, 20, 30), 2, border_radius=6)
        pygame.draw.rect(surf, (200, 200, 200), (sx - 6, sy - 20, 12, 6), border_radius=2)

class TorchPickup:
    def __init__(self, x, y, bonus_radius=90, duration=10*FPS):
        self.x = float(x)
        self.y = float(y)
        self.bonus_radius = int(bonus_radius)
        self.duration = int(duration)
        self.alive = True
        self.t = random.uniform(0, 100)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 14), int(self.y - 18), 28, 36)

    def update(self, hero, floats, particles, font, sfx):
        if not self.alive:
            return
        self.t += 1.0
        if self.rect.colliderect(hero.rect):
            self.alive = False
            hero.torch_bonus = max(hero.torch_bonus, self.bonus_radius)
            hero.torch_timer = max(hero.torch_timer, self.duration)
            floats.append(FloatText(self.x, self.y - 25, "Torch +Light", ORANGE, font))
            particles.embers(self.x, self.y, n=14)
            play_sfx(sfx, "torch")

    def draw(self, surf: pygame.Surface, cam: Camera):
        if not self.alive:
            return
        sx = int(self.x - cam.x + cam.shake_dx)
        sy = int(self.y + cam.shake_dy + math.sin(self.t * 0.07) * 3)
        pygame.draw.rect(surf, (120, 80, 40), (sx - 2, sy - 2, 4, 16), border_radius=2)
        pygame.draw.circle(surf, ORANGE, (sx, sy - 8), 8)
        pygame.draw.circle(surf, (255, 220, 120), (sx - 2, sy - 10), 3)

class CheckpointFlag:
    def __init__(self, x):
        self.x = float(x)
        self.rect = pygame.Rect(int(x), GROUND_Y - 90, 26, 90)
        self.used = False
        self.flash = 0

    def update(self, hero, floats, particles, font, sfx):
        if not self.used and self.rect.colliderect(hero.rect):
            self.used = True
            self.flash = 90
            hero.set_checkpoint(self.x)
            hero.heal(50)
            floats.append(FloatText(self.x, GROUND_Y - 120, "+50 HP", GREEN, font))
            particles.burst(self.x + 10, GROUND_Y - 70, GOLD, n=12, spd=3, life=24, r=3)
            play_sfx(sfx, "checkpoint")
        if self.flash > 0:
            self.flash -= 1

    def draw(self, surf: pygame.Surface, cam: Camera):
        rx = int(self.x - cam.x + cam.shake_dx)
        if rx < -50 or rx > SW + 50:
            return
        pygame.draw.rect(surf, (120, 90, 60), (rx, GROUND_Y - 90, 6, 90))
        col = (120, 120, 120) if self.used else GOLD
        pts = [(rx + 6, GROUND_Y - 90), (rx + 6, GROUND_Y - 62), (rx + 40, GROUND_Y - 76)]
        pygame.draw.polygon(surf, col, pts)
        if self.flash > 0:
            a = int(140 * self.flash / 90)
            tmp = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (255, 255, 150, a), (30, 30), 28)
            surf.blit(tmp, (rx - 18, GROUND_Y - 110))

class GateBarrier:
    _label_font: Optional[pygame.font.Font] = None

    def __init__(self, x: int, height: int = 260, enemy_check: Optional[Callable[[List["Enemy"]], bool]] = None,
                 one_way: bool = False):
        self.x = int(x)
        self.h = int(height)
        self.rect = pygame.Rect(self.x, GROUND_Y - self.h, 26, self.h)
        self.enemy_check = enemy_check
        self.open = False
        self.one_way = one_way
        self._locked_behind = False
        self.anim = 0.0  # 0..h

    def update(self, enemies: List["Enemy"]):
        if self.open and not self._locked_behind:
            self.anim = min(self.h, self.anim + 9)
            return
        if self._locked_behind:
            self.anim = max(0, self.anim - 9)
            return
        if self.enemy_check and self.enemy_check(enemies):
            self.open = True

    def block_hero(self, hero):
        # One-way gate: block until enemies cleared, then let hero walk through, then lock behind
        if self.one_way:
            if not self.open and not self._locked_behind:
                # Enemies not yet cleared — block both directions like a normal gate
                if hero.rect.right > self.rect.left and hero.rect.left < self.rect.right:
                    if hero.rect.centerx < self.rect.centerx:
                        hero.rect.right = self.rect.left
                    else:
                        hero.rect.left = self.rect.right
                return
            # Enemies cleared — detect hero passing through, then lock behind
            if not self._locked_behind and hero.rect.left > self.rect.right:
                self._locked_behind = True
                self.open = False
            if self._locked_behind:
                if hero.rect.left < self.rect.right and hero.rect.right > self.rect.left:
                    hero.rect.left = self.rect.right
            return
        if self.open:
            return
        # Treat gate as a full-height wall — block even when hero is airborne
        if hero.rect.right > self.rect.left and hero.rect.left < self.rect.right:
            if hero.rect.centerx < self.rect.centerx:
                hero.rect.right = self.rect.left
            else:
                hero.rect.left = self.rect.right

    def block_enemies(self, enemies):
        if self.open:
            return
        for e in enemies:
            if e.dead:
                continue
            if self.rect.colliderect(e.rect):
                if e.rect.centerx < self.rect.centerx:
                    e.rect.right = self.rect.left
                else:
                    e.rect.left = self.rect.right
                if e.turn_lock <= 0:
                    e.facing *= -1
                    e.turn_lock = 30

    def draw(self, surf: pygame.Surface, cam: Camera):
        rx = self.x - int(cam.x + cam.shake_dx)
        if rx < -80 or rx > SW + 80:
            return
        vis_h = int(self.h - self.anim)
        if vis_h <= 0:
            return
        # bars
        for i in range(5):
            pygame.draw.rect(surf, (90, 70, 55), (rx + i * 5, GROUND_Y - vis_h, 5, vis_h))
        pygame.draw.rect(surf, RED, (rx - 4, GROUND_Y - vis_h, 34, 8))
        if not self.open:
            if GateBarrier._label_font is None:
                GateBarrier._label_font = pygame.font.SysFont("Arial", 12, bold=True)
            t = GateBarrier._label_font.render("CLEAR ENEMIES", True, RED)
            surf.blit(t, (rx - 18, GROUND_Y - vis_h - 16))

class DarkZone:
    _overlay_surf: Optional[pygame.Surface] = None
    _warm_surf: Optional[pygame.Surface] = None

    def __init__(self, x: int, w: int, base_radius: int = 170):
        self.x = int(x)
        self.w = int(w)
        self.base_radius = int(base_radius)

    def inside(self, wx: float) -> bool:
        return self.x <= wx <= self.x + self.w

    def draw(self, surf: pygame.Surface, hero, cam: Camera):
        if DarkZone._overlay_surf is None:
            DarkZone._overlay_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
            DarkZone._warm_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov, wm = DarkZone._overlay_surf, DarkZone._warm_surf
        ov.fill((0, 0, 0, 220))
        rad = self.base_radius + int(hero.torch_bonus)
        hx, hy = cam.world_to_screen(hero.rect.centerx, hero.rect.centery)
        pygame.draw.circle(ov, (0, 0, 0, 0), (hx, hy), rad)
        wm.fill((0, 0, 0, 0))
        pygame.draw.circle(wm, (255, 140, 50, 35), (hx, hy), int(rad * 0.6))
        surf.blit(ov, (0, 0))
        surf.blit(wm, (0, 0))

# Projectiles
class SnowballProj:
    def __init__(self, x, y, vx, vy=-4.0):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.alive = True

    @property
    def rect(self):
        return pygame.Rect(int(self.x - 13), int(self.y - 13), 26, 26)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.08  # slight gravity — snowballs fly mostly straight toward hero
        if self.y > GROUND_Y + 80:
            self.alive = False

    def draw(self, surf: pygame.Surface, cam: Camera):
        sx, sy = cam.world_to_screen(self.x, self.y)
        pygame.draw.circle(surf, (180, 210, 250), (sx, sy), 13)
        pygame.draw.circle(surf, WHITE, (sx, sy), 13, 2)
        pygame.draw.circle(surf, WHITE, (sx - 4, sy - 4), 3)

# Characters
class Char:
    def __init__(self, x, y, w, h, hp):
        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))
        self.hp = int(hp)
        self.max_hp = int(hp)
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1
        self.state = ST_IDLE
        self.dead = False
        self.death_t = 0
        self.hurt_t = 0
        self.atk_t = 0
        self.invuln = 0
        self.anims: Dict[str, List[pygame.Surface]] = {}
        self._af = 0
        self._at = 0
        self._asp = 6
        self.fc = WHITE

    def _fill_anim_fallbacks(self):
        if not self.anims.get(ST_DEAD):
            self.anims[ST_DEAD] = self.anims.get(ST_HURT) or self.anims.get(ST_IDLE, [])
        for k in list(self.anims.keys()):
            if not self.anims[k]:
                self.anims[k] = self.anims.get(ST_IDLE, [])

    def _set_state(self, s: str):
        if self.state != s:
            self.state = s
            self._af = 0
            self._at = 0

    def _tick_anim(self):
        fr = self.anims.get(self.state, [])
        if not fr:
            return

        self._at += 1
        if self._at < self._asp:
            return
        self._at = 0
        # attack/hurt/dead should NOT loop (hold last frame)
        if self.state in (ST_ATK, ST_HURT, ST_DEAD):
            self._af = min(self._af + 1, len(fr) - 1)
        else:
            self._af = (self._af + 1) % len(fr)

    def _frame(self) -> Optional[pygame.Surface]:
        fr = self.anims.get(self.state, [])
        if not fr:
            return None
        f = fr[min(self._af, len(fr) - 1)]
        if self.facing == -1:
            return pygame.transform.flip(f, True, False)
        return f

    def apply_gravity(self):
        self.vy += GRAVITY
        self.rect.y += int(self.vy)
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vy = 0.0
            self.on_ground = True
        else:
            self.on_ground = False

    def do_platforms(self, platforms: List[Platform]):
        if self.vy < 0:
            return
        for p in platforms:
            pr = p.rect
            if (self.rect.bottom >= pr.top and
                self.rect.bottom < pr.top + 35 and
                self.rect.right > pr.left + 4 and
                self.rect.left < pr.right - 4):
                self.rect.bottom = pr.top
                self.vy = 0.0
                self.on_ground = True

    def do_obstacles(self, obstacles: List[Obstacle], allow_auto_jump: bool = True,
                     coins: Optional[List] = None, land_on_top: bool = False):
        if not obstacles:
            return
        # Coins are non-blocking: if we only overlap coins (no obstacle), run over them — no push-back
        run_over_coins_only = False
        if coins:
            overlap_obstacle = any(self.rect.colliderect(o.rect) for o in obstacles)
            overlap_coin = any(
                self.rect.colliderect(c.rect) for c in coins
                if getattr(c, "alive", True)
            )
            run_over_coins_only = overlap_coin and not overlap_obstacle
        # Horizontal block resolution only when NOT jumping over (avoids rubber-band); skip when only on coins
        if not run_over_coins_only:
            CLEAR_MARGIN = 6  # feet above obstacle top = we're clearing it, don't push back
            for obs in obstacles:
                if not self.rect.colliderect(obs.rect):
                    continue
                # Land on top: if falling and feet entered the top surface, snap to top
                if land_on_top and self.vy >= 0:
                    prev_bottom = self.rect.bottom - self.vy - 1
                    if (prev_bottom <= obs.rect.top + 4 and
                            self.rect.right > obs.rect.left + 4 and
                            self.rect.left < obs.rect.right - 4):
                        self.rect.bottom = obs.rect.top
                        self.vy = 0.0
                        self.on_ground = True
                        continue
                # Don't push back if we're in the air and have cleared the obstacle (jumping over)
                if self.rect.bottom <= obs.rect.top + CLEAR_MARGIN:
                    continue
                if self.facing == 1:
                    self.rect.right = obs.rect.left
                else:
                    self.rect.left = obs.rect.right
                # Turn around when blocked by obstacle (enemies only)
                if hasattr(self, 'turn_lock') and self.turn_lock <= 0:
                    self.facing *= -1
                    self.turn_lock = 30

        # Enemies do NOT auto-jump over obstacles — they must walk around or turn back

    def take_dmg(self, dmg: int, particles: Optional[Particles] = None, col=RED) -> bool:
        if self.dead:
            return False
        if self.invuln > 0:
            return False
        self.hp -= int(dmg)
        self.hurt_t = 18
        self.invuln = 26
        if particles:
            particles.burst(self.rect.centerx, self.rect.centery, col, n=12, spd=5, life=22, r=3)
            # Add blood particles for more visceral feedback
            particles.blood(self.rect.centerx, self.rect.centery, n=18)
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.death_t = 0
            self._set_state(ST_DEAD)
        return True

    def heal(self, amount: int):
        self.hp = min(self.max_hp, self.hp + int(amount))

    def draw(self, surf: pygame.Surface, cam: Camera):
        f = self._frame()
        rx = self.rect.x - int(cam.x + cam.shake_dx)
        if f:
            fx = rx + self.rect.w // 2 - f.get_width() // 2
            fy = self.rect.bottom - f.get_height()
            if self.invuln > 0 and (self.invuln // 3) % 2 == 0 and not self.dead:
                f2 = f.copy()
                f2.set_alpha(120)
                surf.blit(f2, (fx, fy))
            else:
                surf.blit(f, (fx, fy))
        else:
            col = RED if (self.hurt_t > 0 and (self.hurt_t // 3) % 2 == 0) else self.fc
            pygame.draw.rect(surf, col, (rx, self.rect.y, self.rect.w, self.rect.h), border_radius=6)

# Hero
class Hero(Char):
    FW, FH = 90, 110

    def __init__(self, x, y):
        super().__init__(x, y, 52, 100, 200)
        self.speed = 4.2
        self.dmg = 28
        self.rng = 85
        self.hp_ghost = 200.0   # For feedback bar effect

        # Extra features
        self.combo_stage = 0
        self.combo_timer = 0
        self.dash_cd = 0
        self.dashing = 0
        self.dash_dir = 1

        self.ko_cd = 0          # Knockout special move cooldown

        # KO visual effect state
        self.ko_flash    = 0        # frames of full-screen gold flash (fade from bright)
        self.ko_shockwaves: List[Dict] = []  # list of {cx,cy,r,max_r,col}
        self.ko_banner   = 0        # frames to show the big K.O.!! banner
        self.ko_hitstop  = 0        # frames of slow-motion (physics paused)

        self.torch_bonus = 0
        self.torch_timer = 0

        self.checkpoint_x = float(x)
        self.checkpoint_y = float(y)

        self._asp = 5
        self._load_anims()

    def _load_anims(self):
        h = self.FH
        idle = load_strip("Hero_stand.png", 10, h)
        walk = load_strip("Hero_Walking.png", 10, h)
        atk  = load_strip("Hero_Attacking.png", 8, h)
        jump = load_strip("Hero_Jumping.png", 11, h)
        hurt = load_strip("Hero_Taking_Damage.png", 5, h)
        dead = load_strip("Hero_Fainting.png", 2, h)
        if dead and len(dead) >= 2:
            dead = [dead[-1]]
        self.anims = {
            ST_IDLE: idle[:1] if idle else [],
            ST_WALK: walk if walk else idle,
            ST_RUN:  walk if walk else idle,
            ST_JUMP: jump if jump else idle,
            ST_ATK:  atk if atk else idle,
            ST_HURT: hurt[:1] if hurt else [],
            ST_DEAD: dead[:1] if dead else [],
        }
        # fallback
        idle_fb = self.anims.get(ST_IDLE, [])
        for k in list(self.anims.keys()):
            if not self.anims[k] and idle_fb:
                self.anims[k] = idle_fb

    def set_checkpoint(self, x: float):
        self.checkpoint_x = float(x)
        self.checkpoint_y = float(GROUND_Y - self.rect.h)

    def respawn(self):
        self.rect.x = int(self.checkpoint_x)
        self.rect.y = int(self.checkpoint_y)
        self.vy = 0.0
        self.hp = self.max_hp
        self.dead = False
        self.death_t = 0
        self.hurt_t = 0
        self.invuln = 70
        self._set_state(ST_IDLE)

    def _attack_rect(self) -> pygame.Rect:
        # Slightly different range depending on combo stage
        rng = self.rng + (self.combo_stage - 1) * 10
        if self.facing == 1:
            return pygame.Rect(self.rect.right - 8, self.rect.y + 16, rng, self.rect.h - 28)
        return pygame.Rect(self.rect.left - rng + 8, self.rect.y + 16, rng, self.rect.h - 28)

    def _do_attack(self, enemies: List["Enemy"], boss: Optional["DarkSanta"], particles: Particles, floats: List[FloatText], font, sfx, camera: Camera, score_ref: Dict[str, int], obstacles: Optional[List] = None):
        ar = self._attack_rect()
        # Combo damage multiplier
        mult = 1.0 + (self.combo_stage - 1) * 0.25
        dmg = int(self.dmg * mult)
        hit_any = False

        def obstacle_blocks(hero_rect: pygame.Rect, tgt_rect: pygame.Rect) -> bool:
            if not obstacles:
                return False
            hcx, tcx = hero_rect.centerx, tgt_rect.centerx
            lo, hi = min(hcx, tcx), max(hcx, tcx)
            y_lo = min(hero_rect.top, tgt_rect.top)
            y_hi = max(hero_rect.bottom, tgt_rect.bottom)
            for obs in obstacles:
                if lo < obs.rect.centerx < hi and obs.rect.bottom > y_lo and obs.rect.top < y_hi:
                    return True
            return False

        def hit_target(tgt: Char):
            nonlocal hit_any
            if tgt.dead:
                return
            if ar.colliderect(tgt.rect):
                if obstacle_blocks(self.rect, tgt.rect):
                    return
                if tgt.take_dmg(dmg, particles, BLOOD):
                    camera.add_shake(6.0, frames=12)
                    hit_any = True
                    # reward
                    if isinstance(tgt, Enemy) and tgt.dead:
                        score_ref["score"] += 100
                        self.heal(50)
                        floats.append(FloatText(tgt.rect.centerx, tgt.rect.top - 20, "+100", GOLD, font))
                        floats.append(FloatText(tgt.rect.centerx, tgt.rect.top - 42, "+50 HP", GREEN, font))
                        play_sfx(sfx, "kill")
                    elif isinstance(tgt, DarkSanta) and tgt.dead:
                        score_ref["score"] += 500

        for e in enemies:
            hit_target(e)
        if boss:
            hit_target(boss)

        play_sfx(sfx, "attack")

        if hit_any:
            # tiny "hit stop" feeling: slow down next few frames for hero only
            self.atk_t = max(self.atk_t, 18)

    def _do_knockout(self, enemies: List["Enemy"], boss: Optional["DarkSanta"], particles: Particles,
                     floats: List[FloatText], font, sfx, camera: Camera, score_ref: Dict[str, int]):
        """Knockout special attack — cinematic blow that impresses the watcher."""
        ko_reach = 700
        hit_any  = False
        hcx, hcy = self.rect.centerx, self.rect.centery

        # ── shockwave ring from hero position ──────────────────────────────
        self.ko_shockwaves.append({"cx": hcx, "cy": hcy, "r": 10,  "max_r": 340, "col": GOLD,   "thick": 6})
        self.ko_shockwaves.append({"cx": hcx, "cy": hcy, "r": 10,  "max_r": 260, "col": (255,255,255), "thick": 3})
        self.ko_shockwaves.append({"cx": hcx, "cy": hcy, "r": 10,  "max_r": 180, "col": ORANGE, "thick": 5})

        # ── small enemies: instant kill (CLOSEST ONE only) ────────────────
        closest_e = None
        closest_dist = ko_reach + 1
        for e in enemies:
            if e.dead:
                continue
            dist = abs(e.rect.centerx - hcx)
            if dist <= ko_reach and dist < closest_dist:
                closest_dist = dist
                closest_e = e

        if closest_e is not None:
            e = closest_e
            cx, cy = e.rect.centerx, e.rect.centery
            # Wave 1 — golden starburst
            particles.burst(cx, cy, GOLD,          n=40, spd=14, life=55, r=7, vy_bias=-4.0)
            # Wave 2 — white sparkle ring
            particles.burst(cx, cy, (255,255,220), n=25, spd=8,  life=40, r=4, vy_bias=-2.0)
            # Wave 3 — blood splatter for impact
            particles.blood(cx, cy, n=30)
            # Wave 4 — orange ember trail
            particles.embers(cx, cy, n=20)
            # per-enemy shockwave ring
            self.ko_shockwaves.append({"cx": cx, "cy": cy, "r": 5, "max_r": 140, "col": (255,220,60), "thick": 4})
            # Force kill
            e.hp = 0
            e.dead = True
            score_ref["score"] += 100
            self.heal(50)
            floats.append(FloatText(cx, cy - 20, "K.O.!",  GOLD,  font))
            floats.append(FloatText(cx, cy - 44, "+100",   GOLD,  font))
            floats.append(FloatText(cx, cy - 68, "+50 HP", GREEN, font))
            play_sfx(sfx, "kill")
            hit_any = True

        # ── Dark Santa: 25% max HP damage ─────────────────────────────────
        if boss and not boss.dead:
            dist = abs(boss.rect.centerx - hcx)
            if dist <= ko_reach:
                ko_dmg = max(1, boss.max_hp // 4)
                boss.take_dmg(ko_dmg, particles, GOLD)
                cx, cy = boss.rect.centerx, boss.rect.centery
                particles.burst(cx, cy, GOLD,           n=55, spd=15, life=60, r=9, vy_bias=-5.0)
                particles.burst(cx, cy, (255,100,50),   n=30, spd=10, life=45, r=6, vy_bias=-3.0)
                particles.burst(cx, cy, (255,255,255),  n=20, spd=6,  life=35, r=4, vy_bias=-2.0)
                particles.embers(cx, cy, n=30)
                self.ko_shockwaves.append({"cx": cx, "cy": cy, "r": 5, "max_r": 220, "col": RED,   "thick": 7})
                self.ko_shockwaves.append({"cx": cx, "cy": cy, "r": 5, "max_r": 160, "col": GOLD,  "thick": 4})
                floats.append(FloatText(cx, cy - 50,  "-25% HP!",    ORANGE, font))
                floats.append(FloatText(cx, cy - 74,  "K.O. PUNCH!", GOLD,   font))
                hit_any = True

        # ── screen-level effects (always fire, hit or not) ─────────────────
        self.ko_flash  = 28     # frames of blinding screen flash
        self.ko_banner = 110    # frames of big K.O.!! banner
        self.ko_hitstop = 14    # frames of slow-motion / physics pause

        if hit_any:
            camera.add_shake(22.0, frames=26)
        else:
            camera.add_shake(6.0, frames=10)

        play_sfx(sfx, "knockout")   # deep boom + crack + zing


    def update(self, keys, inp: Input, platforms: List[Platform], obstacles: List[Obstacle], gates: List[GateBarrier],
               enemies: List["Enemy"], boss: Optional["DarkSanta"], particles: Particles,
               floats: List[FloatText], font, sfx, camera: Camera, score_ref: Dict[str, int]):
        if self.dead:
            self._set_state(ST_DEAD)
            self._tick_anim()
            self.apply_gravity()
            self.do_platforms(platforms)
            return

        # timers
        if self.hurt_t > 0:
            self.hurt_t -= 1
        if self.atk_t > 0:
            self.atk_t -= 1
        if self.invuln > 0:
            self.invuln -= 1

        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo_stage = 0

        if self.dash_cd > 0:
            self.dash_cd -= 1
        if self.dashing > 0:
            self.dashing -= 1

        if self.torch_timer > 0:
            self.torch_timer -= 1
            if self.torch_timer == 0:
                self.torch_bonus = 0

        if self.ko_cd > 0:
            self.ko_cd -= 1

        # tick KO visual effects
        if self.ko_flash > 0:
            self.ko_flash -= 1
        if self.ko_banner > 0:
            self.ko_banner -= 1
        if self.ko_hitstop > 0:
            self.ko_hitstop -= 1
        # expand shockwave rings
        live_waves = []
        for w in self.ko_shockwaves:
            w["r"] += 18    # expand speed
            if w["r"] < w["max_r"]:
                live_waves.append(w)
        self.ko_shockwaves = live_waves

        # movement
        moving = False
        dx = 0.0
        run = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]

        # if dashing: override
        if self.dashing > 0:
            dx = 10.0 * self.dash_dir
            moving = True
        else:
            if self.atk_t == 0:
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    dx -= self.speed
                    self.facing = -1
                    moving = True
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    dx += self.speed
                    self.facing = 1
                    moving = True

        self.rect.x += int(dx)
        self.rect.x = max(0, min(WORLD_W - self.rect.w, self.rect.x))

        # obstacle collisions — hero can land on top but does not auto-jump sideways
        if obstacles:
            self.do_obstacles(obstacles, allow_auto_jump=False, land_on_top=True)
        # gate collisions
        for g in gates:
            g.block_hero(self)

        # jump
        if (inp.pressed(pygame.K_SPACE) or inp.pressed(pygame.K_UP) or inp.pressed(pygame.K_w)) and self.on_ground and self.atk_t == 0:
            self.vy = JUMP_VEL
            play_sfx(sfx, "jump")

        # dash (cooldown)
        if inp.pressed(pygame.K_LSHIFT) or inp.pressed(pygame.K_RSHIFT):
            if self.dash_cd == 0 and not self.dead:
                self.dashing = 10
                self.dash_cd = 60
                self.invuln = max(self.invuln, 12)
                self.dash_dir = self.facing
                particles.embers(self.rect.centerx, self.rect.bottom - 20, n=10)
                camera.add_shake(3.0, frames=8)

        # attack (combo)
        if inp.pressed(pygame.K_z) and self.atk_t == 0:
            # open/continue combo
            if self.combo_timer > 0:
                self.combo_stage = min(3, self.combo_stage + 1)
            else:
                self.combo_stage = 1
            self.combo_timer = 22
            self.atk_t = 24
            self._set_state(ST_ATK)
            self._do_attack(enemies, boss, particles, floats, font, sfx, camera, score_ref, obstacles)

        # knockout special (X key, cooldown)
        if inp.pressed(pygame.K_x) and self.ko_cd == 0 and not self.dead:
            self.ko_cd = KO_COOLDOWN
            self.atk_t = max(self.atk_t, 30)
            self._set_state(ST_ATK)
            self._do_knockout(enemies, boss, particles, floats, font, sfx, camera, score_ref)

        # physics
        self.apply_gravity()
        self.do_platforms(platforms)

        # state logic
        if self.hurt_t > 10:
            self._set_state(ST_HURT)
        elif self.atk_t > 0:
            self._set_state(ST_ATK)
        elif not self.on_ground:
            self._set_state(ST_JUMP)
        elif moving:
            self._set_state(ST_RUN if run else ST_WALK)
        else:
            self._set_state(ST_IDLE)

        self._tick_anim()

# Enemies
class Enemy(Char):
    PFX = "gnome_green"
    FW, FH = 72, 90
    BASE_HP = 80
    BASE_SPD = 2.0
    BASE_DMG = 10
    BASE_COOL = 65
    BASE_PAT = 200
    CHASE_RANGE = 950
    DETECT_RANGE = 650
    TURN_THRESH = 60
    ATK_DIST = 50
    CHASE_STATE = ST_WALK
    PATROL_SPD_MULT = 0.5
    SHAKE_MAG = 4.0
    SHAKE_FRAMES = 10
    CHECK_SAME_LEVEL = True

    def __init__(self, x, y):
        super().__init__(x, y, 48, 82, self.BASE_HP)
        self.max_hp = self.BASE_HP
        self.hp = self.BASE_HP
        self.speed = self.BASE_SPD
        self.dmg = self.BASE_DMG
        self.cool = 0
        self.pat = self.BASE_PAT
        self.ox = float(x)
        self._chasing = False
        self.turn_lock = 0
        self._asp = 7
        self.facing = -1
        self.zone_left = -9999
        self.zone_right = 99999
        self._load_anims()

    def _load_anims(self):
        h = self.FH
        fp = self.PFX.replace("gnome_", "Gnome_")
        idle = load_strip(f"{fp}_stand.png", 10, h)
        walk = load_strip(f"{fp}_Walking.png", 10, h)
        atk  = load_strip(f"{fp}_Attacking.png", 7, h)
        hurt = load_strip(f"{fp}_Taking_Damage.png", 5, h)
        dead = load_strip(f"{fp}_Fainting.png", 2, h)

        # Cap faint frame width — lying-down pose can be very wide
        capped_dead = []
        max_w = h  # cap at same as height
        for df in dead:
            dw, dh = df.get_size()
            if dw > max_w and dh > 0:
                ratio = max_w / dw
                df = pygame.transform.smoothscale(df, (max_w, max(8, int(dh * ratio))))
            capped_dead.append(df)
        dead = capped_dead

        # dead sheet: hold last frame
        if dead and len(dead) >= 2:
            dead = [dead[-1]]

        self.anims = {
            ST_IDLE: idle[:1] if idle else [],
            ST_WALK: walk if walk else idle,
            ST_ATK: atk,
            ST_HURT: hurt[:1] if hurt else (dead[:1] if dead else []),
            ST_DEAD: dead[:1] if dead else [],
        }
        self._fill_anim_fallbacks()

    def _tick_anim(self):
        """Override: loop attack animation for enemies instead of holding last frame."""
        fr = self.anims.get(self.state, [])
        if not fr:
            return
        self._at += 1
        if self._at < self._asp:
            return
        self._at = 0
        # For enemies: attack should LOOP; hurt/dead still hold last frame
        if self.state in (ST_HURT, ST_DEAD):
            self._af = min(self._af + 1, len(fr) - 1)
        else:
            self._af = (self._af + 1) % len(fr)

    def update(self, hero: Hero, platforms: List[Platform], obstacles: List[Obstacle], particles: Particles, sfx, camera: Camera,
               coins: Optional[List] = None):
        if self.dead:
            self.death_t += 1
            self._set_state(ST_DEAD)
            self._tick_anim()
            self.apply_gravity()
            self.do_platforms(platforms)
            return

        if self.hurt_t > 0: self.hurt_t -= 1
        if self.invuln > 0: self.invuln -= 1
        if self.cool > 0: self.cool -= 1
        if self.turn_lock > 0: self.turn_lock -= 1

        dx = hero.rect.centerx - self.rect.centerx
        dist = abs(dx)
        can_engage = not self.CHECK_SAME_LEVEL or abs(hero.rect.centery - self.rect.centery) < 60

        if not hero.dead and (dist < self.DETECT_RANGE or (self._chasing and dist < self.CHASE_RANGE)):
            self._chasing = True
            if self.turn_lock <= 0:
                if dx > self.TURN_THRESH:
                    self.facing = 1; self.turn_lock = 30
                elif dx < -self.TURN_THRESH:
                    self.facing = -1; self.turn_lock = 30

            if can_engage:
                if dist > self.ATK_DIST:
                    self.rect.x += int(self.facing * self.speed)
                    self._set_state(self.CHASE_STATE)
                else:
                    self._set_state(ST_ATK)
                    if self.cool == 0:
                        self.cool = self.BASE_COOL
                        play_sfx(sfx, "attack")
                        if hero.take_dmg(self.dmg, particles, RED):
                            camera.add_shake(self.SHAKE_MAG, frames=self.SHAKE_FRAMES)
                            play_sfx(sfx, "hurt")
            else:
                # Hero is above/below — still chase horizontally but don't melee attack
                if dist > self.ATK_DIST:
                    self.rect.x += int(self.facing * self.speed)
                    self._set_state(self.CHASE_STATE)
                else:
                    self._set_state(ST_IDLE)
        else:
            self._chasing = False
            self.rect.x += int(self.facing * self.speed * self.PATROL_SPD_MULT)
            if abs(self.rect.x - self.ox) > self.pat and self.turn_lock <= 0:
                self.facing *= -1; self.turn_lock = 30
            self._set_state(ST_WALK)

        # Clamp to zone boundaries so enemies never cross gates
        if self.rect.left < self.zone_left:
            self.rect.left = self.zone_left
            if self.facing == -1 and self.turn_lock <= 0:
                self.facing = 1; self.turn_lock = 30
        if self.rect.right > self.zone_right:
            self.rect.right = self.zone_right
            if self.facing == 1 and self.turn_lock <= 0:
                self.facing = -1; self.turn_lock = 30
        self.rect.x = max(0, min(WORLD_W - self.rect.w, self.rect.x))
        self.do_obstacles(obstacles, allow_auto_jump=True, coins=coins)
        self.apply_gravity()
        self.do_platforms(platforms)
        if self.hurt_t > 10: self._set_state(ST_HURT)
        self._tick_anim()

    def draw(self, surf: pygame.Surface, cam: Camera):
        super().draw(surf, cam)
        # HP bar
        if not self.dead and self.hp < self.max_hp:
            rx = self.rect.x - int(cam.x + cam.shake_dx)
            pygame.draw.rect(surf, (30, 0, 0), (rx, self.rect.y - 10, self.rect.w, 6))
            w = int(self.rect.w * self.hp / max(1, self.max_hp))
            pygame.draw.rect(surf, (255, 80, 80), (rx, self.rect.y - 10, w, 6))
            pygame.draw.rect(surf, (255, 255, 255), (rx, self.rect.y - 10, self.rect.w, 6), 1)


class RedGnome(Enemy):
    PFX = "gnome_red"
    BASE_HP = 130
    BASE_SPD = 2.8
    BASE_DMG = 18
    BASE_COOL = 55
    BASE_PAT = 260
    def __init__(self, x, y):
        super().__init__(x, y)
        self._asp = 6

class EvilBiscuit(Enemy):
    PFX = "biscuit"
    BASE_HP = 120
    BASE_SPD = 3.2
    BASE_DMG = 22
    BASE_COOL = 50
    BASE_PAT = 290
    CHASE_RANGE = 700
    DETECT_RANGE = 400
    TURN_THRESH = 50
    ATK_DIST = 40
    CHASE_STATE = ST_WALK
    PATROL_SPD_MULT = 0.45
    SHAKE_MAG = 5.0
    SHAKE_FRAMES = 12
    CHECK_SAME_LEVEL = True
    # Biscuit colors for fallback when sprites missing
    BISCUIT_COLOR = (205, 165, 120)
    BISCUIT_DARK = (140, 100, 70)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.rect.w = 56
        self.rect.h = 90
        self.fc = self.BISCUIT_COLOR
        self._asp = 8

    def draw(self, surf: pygame.Surface, cam: Camera):
        f = self._frame()
        rx = self.rect.x - int(cam.x + cam.shake_dx)
        if f:
            fx = rx + self.rect.w // 2 - f.get_width() // 2
            fy = self.rect.bottom - f.get_height() + 14  # shift down so feet touch ground
            if self.invuln > 0 and (self.invuln // 3) % 2 == 0 and not self.dead:
                f2 = f.copy()
                f2.set_alpha(120)
                surf.blit(f2, (fx, fy))
            else:
                surf.blit(f, (fx, fy))
        else:
            col = RED if (self.hurt_t > 0 and (self.hurt_t // 3) % 2 == 0) else self.fc
            pygame.draw.rect(surf, col, (rx, self.rect.y, self.rect.w, self.rect.h), border_radius=6)
        if not self.dead and self.hp < self.max_hp:
            pygame.draw.rect(surf, (30, 0, 0), (rx, self.rect.y - 10, self.rect.w, 6))
            w = int(self.rect.w * self.hp / max(1, self.max_hp))
            pygame.draw.rect(surf, (255, 80, 80), (rx, self.rect.y - 10, w, 6))
            pygame.draw.rect(surf, (255, 255, 255), (rx, self.rect.y - 10, self.rect.w, 6), 1)

    def _load_anims(self):
        # Biscuit uses fixed size (96x120) — no inset/crop needed
        def _bs(fname, n, sz=(96, 120)):
            img = load_image(fname, alpha=True)
            if not img: return []
            w, h = img.get_width(), img.get_height()
            fw = max(1, w // n)
            return [pygame.transform.smoothscale(img.subsurface((i*fw, 0, fw, h)), sz) for i in range(n) if i*fw+fw <= w]
        idle = _bs("Biscuit_stand.png", 10)
        walk = _bs("Biscuit_Walking.png", 10)
        atk  = _bs("Biscuit_Attacking.png", 7)
        hurt = _bs("Biscuit_Taking_Damage.png", 5)
        dead = _bs("Biscuit_Fainting.png", 2)
        if dead and len(dead) >= 2:
            dead = [dead[-1]]
        self.anims = {
            ST_IDLE: idle[:1] if idle else [],
            ST_WALK: walk if walk else idle,
            ST_RUN: walk if walk else idle,
            ST_ATK: atk,
            ST_HURT: hurt[:1] if hurt else (dead[:1] if dead else []),
            ST_DEAD: dead[:1] if dead else [],
        }
        self._fill_anim_fallbacks()

# Boss
class DarkSanta(Char):
    FW, FH = 130, 160

    def __init__(self, x, y):
        super().__init__(x, y, 112, 156, 350)
        self.speed = 2.0
        self.dmg = 25
        self.cool = 0
        self.phase = 1
        self.balls: List[SnowballProj] = []
        self._asp = 7
        self.turn_lock = 0
        self.zone_left = -9999
        self.zone_right = 99999
        
        self.hp_ghost = 350.0 # for boss ghost health effect
        self._load_anims()

        # extra attacks
        self.slam_cd = 0
        self.summon_cd = 0
        self._atk_lock = 0   # frames to stay rooted during melee swing

    def _load_anims(self):
        # Santa sprite sheets (horizontal strips):
        #   stand:     952x222 → 5 frames @ 190px each
        #   walking:   536x227 → 3 frames @ 179px each
        #   running:   961x223 → 5 frames @ 192px each
        #   attacking: 2984x499 → 5 frames @ 597px each
        #   fainting:  401x223 → 2 frames @ 201px each
        #   jumping:   971x223 → 5 frames @ 194px each
        TGT = (140, 160)

        def load_strip(fname, num_frames_or_points, auto_crop=False):
            img = load_image(fname, alpha=True)
            if img is None:
                return []
            w, h = img.get_width(), img.get_height()
            raw = []
            
            # Use custom points if provided, otherwise uniform slicing
            if isinstance(num_frames_or_points, list):
                points = num_frames_or_points
                num_frames = len(points) - 1
            else:
                num_frames = num_frames_or_points
                points = [int(round(i * w / float(num_frames))) for i in range(num_frames + 1)]

            for i in range(num_frames):
                sx = points[i]
                ex = points[i+1]
                if ex <= sx:
                    break
                fw = ex - sx
                f = pygame.Surface((fw, h), pygame.SRCALPHA)
                f.blit(img, (0, 0), (sx, 0, fw, h))
                if auto_crop:
                    mask = pygame.mask.from_surface(f, 10)
                    bboxes = mask.get_bounding_rects()
                    if bboxes:
                        bboxes.sort(key=lambda b: b.w * b.h, reverse=True)
                        main_r = bboxes[0].copy()
                        r = main_r.copy()
                        main_area = main_r.w * main_r.h
                        for br in bboxes[1:]:
                            is_small = (br.w * br.h < main_area * 0.12)
                            touches_edge = (br.x < 20 or br.right > fw - 20)
                            if is_small and touches_edge:
                                f.fill((0, 0, 0, 0), br)
                            elif is_small and not br.colliderect(main_r.inflate(20, 20)):
                                f.fill((0, 0, 0, 0), br)
                            else:
                                r.union_ip(br)
                        cropped = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                        cropped.blit(f, (0, 0), r)
                        f = cropped
                raw.append(f)
            if not raw:
                return []
            if auto_crop and len(raw) > 1:
                # Scale each frame to target HEIGHT preserving aspect ratio, then
                # place on a shared canvas so all frames are the same size.
                # Use 94% of TGT height so the body matches walk/idle size
                th = int(TGT[1] * 0.94)
                scaled = []
                for f in raw:
                    fw2, fh2 = f.get_size()
                    ratio = th / max(1, fh2)
                    nw = max(1, int(fw2 * ratio))
                    scaled.append(pygame.transform.smoothscale(f, (nw, th)))
                max_w = max(s.get_width() for s in scaled)
                normalised = []
                for s in scaled:
                    canvas = pygame.Surface((max_w, th), pygame.SRCALPHA)
                    ox = (max_w - s.get_width()) // 2
                    canvas.blit(s, (ox, 0))
                    normalised.append(canvas)
                return normalised
            # Scale preserving aspect ratio: fit to TGT height, width proportional
            th = TGT[1]
            scaled = []
            for f in raw:
                fw2, fh2 = f.get_size()
                ratio = th / max(1, fh2)
                nw = max(1, int(fw2 * ratio))
                scaled.append(pygame.transform.smoothscale(f, (nw, th)))
            # Normalise all to same canvas (max width) for consistent draw
            if len(scaled) > 1:
                max_w = max(s.get_width() for s in scaled)
                normalised = []
                for s in scaled:
                    canvas = pygame.Surface((max_w, th), pygame.SRCALPHA)
                    ox = (max_w - s.get_width()) // 2
                    canvas.blit(s, (ox, 0))
                    normalised.append(canvas)
                return normalised
            return scaled

        idle = load_strip("Santa_stand.png", 5)
        walk = load_strip("Santa_Walking.png", 3)
        run  = load_strip("Santa_Running.png", 5)

        # Attack strip: 2984x499 with 5 unevenly-spaced poses.
        # Boundaries found via column-density valleys (deepest dips between poses).
        atk_points = [0, 499, 1027, 1542, 2228, 2984]
        atk = load_strip("Santa_Attacking.png", atk_points, auto_crop=True)

        dead = load_strip("Santa_Fainting.png", 2)
        if dead and len(dead) >= 2:
            dead = [dead[-1]]
        self.anims = {
            ST_IDLE: idle[:2] if idle else [],
            ST_WALK: walk if walk else idle,
            ST_RUN: run if run else walk,
            ST_ATK: atk if atk else (run if run else idle),
            ST_HURT: idle[:1] if idle else [],
            ST_DEAD: dead[:1] if dead else [],
        }
        self._fill_anim_fallbacks()

    def _tick_anim(self):
        """Override: loop attack animation for DarkSanta instead of holding last frame."""
        fr = self.anims.get(self.state, [])
        if not fr:
            return
        self._at += 1
        if self._at < self._asp:
            return
        self._at = 0
        # Boss attack should LOOP; hurt/dead still hold last frame
        if self.state in (ST_HURT, ST_DEAD):
            self._af = min(self._af + 1, len(fr) - 1)
        else:
            self._af = (self._af + 1) % len(fr)


    def _update_balls(self, hero: Hero, particles: Particles, sfx, camera: Camera):
        live: List[SnowballProj] = []
        for b in self.balls:
            b.update()
            if b.alive:
                if not hero.dead and b.rect.colliderect(hero.rect):
                    if hero.take_dmg(14, particles, CYAN):
                        camera.add_shake(5.0, frames=12)
                        play_sfx(sfx, "hurt")
                    b.alive = False
                else:
                    live.append(b)
        self.balls = live

    def update(self, hero: Hero, platforms: List[Platform], obstacles: List[Obstacle], particles: Particles, sfx, camera: Camera,
               spawn_enemy_cb: Optional[Callable[[float], None]] = None, coins: Optional[List] = None):
        self._update_balls(hero, particles, sfx, camera)

        if self.dead:
            self.death_t += 1
            self._set_state(ST_DEAD)
            self._tick_anim()
            self.apply_gravity()
            self.do_platforms(platforms)
            return

        if self.hurt_t > 0:
            self.hurt_t -= 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.cool > 0:
            self.cool -= 1
        if self.slam_cd > 0:
            self.slam_cd -= 1
        if self.summon_cd > 0:
            self.summon_cd -= 1
        if self._atk_lock > 0:
            self._atk_lock -= 1

        ratio = self.hp / max(1, self.max_hp)
        self.phase = 1 if ratio > 0.66 else (2 if ratio > 0.33 else 3)
        spd = self.speed + (self.phase - 1) * 0.9

        dx = hero.rect.centerx - self.rect.centerx
        dy = hero.rect.centery - self.rect.centery
        dist = abs(dx)
        self.facing = 1 if dx > 0 else -1

        # Vertical reach: hero is "up on sticks" (threshold 60)
        can_reach_v = abs(dy) < 60

        # Choose attack style
        will_slam = (self.phase >= 2 and self.slam_cd == 0 and dist < 160 and random.random() < 0.03)
        will_summon = (self.phase == 3 and self.summon_cd == 0 and random.random() < 0.02)

        if will_summon and spawn_enemy_cb:
            self.summon_cd = 240
            spawn_enemy_cb(self.rect.centerx + self.facing * 120)
            particles.embers(self.rect.centerx, self.rect.bottom - 30, n=24)
            camera.add_shake(7.0, frames=14)

        if will_slam:
            self.slam_cd = 180
            self._set_state(ST_ATK)
            # slam damage in small area
            slam_rect = pygame.Rect(self.rect.centerx - 120, self.rect.bottom - 60, 240, 70)
            particles.burst(self.rect.centerx, self.rect.bottom - 40, ORANGE, n=18, spd=4, life=22, r=4)
            camera.add_shake(10.0, frames=18)
            play_sfx(sfx, "attack")
            if slam_rect.colliderect(hero.rect):
                hero.take_dmg(26, particles, ORANGE)
        else:
            # While attack-locked, stay rooted and keep playing attack anim
            if self._atk_lock > 0:
                self._set_state(ST_ATK)
            elif dist > 85: # Move closer (was 120)
                # Keep chasing horizontally even if hero is high up
                self.rect.x += int(self.facing * spd)
                self._set_state(ST_RUN if self.phase == 3 else ST_WALK)
            elif not can_reach_v:
                # Reached X position but hero is too high — go idle
                self._set_state(ST_IDLE)
            else:
                # Reached X position and hero is within vertical reach — attack!
                self._set_state(ST_ATK)
                if self.cool == 0:
                    cool_frames = max(30, 70 - self.phase * 15)
                    self.cool = cool_frames
                    # Root the boss for the full swing duration so it doesn't glide
                    self._atk_lock = cool_frames
                    # Larger hit area to compensate for wide frames (was 70)
                    melee_hit = (self.rect.inflate(130, 20).colliderect(hero.rect))
                    play_sfx(sfx, "attack")
                    if melee_hit and hero.take_dmg(self.dmg, particles, ORANGE):
                        camera.add_shake(7.0, frames=16)
                        play_sfx(sfx, "boss_hit")
                    # projectiles — aim at hero
                    if self.phase >= 2:
                        sx, sy = self.rect.centerx, self.rect.centery - 20
                        tdx = hero.rect.centerx - sx
                        tdy = hero.rect.centery - sy
                        d = max(1, (tdx**2 + tdy**2) ** 0.5)
                        spd_ball = 5.5
                        self.balls.append(SnowballProj(sx, sy, spd_ball * tdx / d, spd_ball * tdy / d))
                    if self.phase == 3 and random.random() < 0.55:
                        sx, sy = self.rect.centerx, self.rect.centery - 30
                        tdx = hero.rect.centerx - sx + random.randint(-40, 40)
                        tdy = hero.rect.centery - sy
                        d = max(1, (tdx**2 + tdy**2) ** 0.5)
                        spd_ball = 4.5
                        self.balls.append(SnowballProj(sx, sy, spd_ball * tdx / d, spd_ball * tdy / d))

        # Clamp to zone boundaries so boss can't cross gates
        if self.rect.left < self.zone_left:
            self.rect.left = self.zone_left
        if self.rect.right > self.zone_right:
            self.rect.right = self.zone_right
        self.rect.x = max(0, min(WORLD_W - self.rect.w, self.rect.x))
        self.do_obstacles(obstacles, allow_auto_jump=True, coins=coins)
        self.apply_gravity()
        self.do_platforms(platforms)

        if self.hurt_t > 10:
            self._set_state(ST_HURT)

        self._tick_anim()

    def draw(self, surf: pygame.Surface, cam: Camera):
        f = self._frame()
        rx = self.rect.x - int(cam.x + cam.shake_dx)
        if f:
            fw, fh = f.get_size()
            # Always center sprite on rect — consistent for every animation state
            # (no position jump when transitioning between walk and attack frames)
            fx = rx + self.rect.w // 2 - fw // 2
            fy = self.rect.bottom - fh + 14
            if self.invuln > 0 and (self.invuln // 3) % 2 == 0 and not self.dead:
                f2 = f.copy()
                f2.set_alpha(120)
                surf.blit(f2, (fx, fy))
            else:
                surf.blit(f, (fx, fy))
        else:
            col = RED if (self.hurt_t > 0 and (self.hurt_t // 3) % 2 == 0) else (120, 30, 30)
            pygame.draw.rect(surf, col, (rx, self.rect.y, self.rect.w, self.rect.h), border_radius=8)
        # Boss HP bar
        if not self.dead:
            bar_w = 200
            bar_x = rx + self.rect.w // 2 - bar_w // 2
            pygame.draw.rect(surf, (30, 0, 0), (bar_x, self.rect.y - 14, bar_w, 8))
            w = int(bar_w * self.hp / max(1, self.max_hp))
            pygame.draw.rect(surf, (255, 40, 40), (bar_x, self.rect.y - 14, w, 8))
            pygame.draw.rect(surf, (255, 255, 255), (bar_x, self.rect.y - 14, bar_w, 8), 1)
        # Snowballs
        for b in self.balls:
            b.draw(surf, cam)

# Child NPC
class Child:
    _img: Optional[pygame.Surface] = None

    def __init__(self, x, y, color=(255, 180, 100)):
        self.x = float(x)
        self.y = float(y)
        self.col = safe_color(color)
        self.released = False
        self.vy = 0.0
        self.t = 0

        if Child._img is None:
            raw = load_image("child.png", alpha=True)
            if raw:
                # scale huge image down
                aspect = raw.get_width() / max(1, raw.get_height())
                th = 76
                tw = int(th * aspect)
                Child._img = pygame.transform.smoothscale(raw, (tw, th))

    def release(self):
        self.released = True
        self.vy = -9.0

    def update(self):
        if not self.released:
            # shiver animation timer
            self.t += 1
            return
        self.t += 1
        self.y += self.vy
        if self.y < GROUND_Y - 60:
            self.vy += 0.4
        else:
            self.y = GROUND_Y - 60
            self.vy = 0.0

    def draw(self, surf: pygame.Surface, cam: Camera):
        sx = int(self.x - cam.x + cam.shake_dx)
        sy = int(self.y + cam.shake_dy)
        if sx < -80 or sx > SW + 80:
            return
        bob = int(math.sin(self.t * 0.15) * 3) if self.released else 0
        shx = 0
        shy = 0
        if not self.released:
            ticks = pygame.time.get_ticks()
            shx = int(math.sin(ticks * 0.06) * 2)
            shy = int(math.cos(ticks * 0.07) * 1)

        if Child._img:
            ix = sx - Child._img.get_width() // 2 + shx
            iy = sy - Child._img.get_height() + 28 + bob + shy
            surf.blit(Child._img, (ix, iy))
        else:
            pygame.draw.rect(surf, self.col, (sx - 11 + shx, sy + bob + shy, 22, 28), border_radius=5)
            pygame.draw.circle(surf, (255, 210, 165), (sx + shx, sy - 10 + bob + shy), 12)

        # star burst on release
        if self.released and self.t < 80:
            for i in range(5):
                a = math.radians(i * 72 + self.t * 12)
                pygame.draw.circle(surf, GOLD, (int(sx + math.cos(a) * 24), int(sy + math.sin(a) * 18 + bob)), 4)

# Background (parallax)
class Background:
    def __init__(self):
        raw = load_image("background.jpg", alpha=False)
        self.img = pygame.transform.scale(raw, (SW, SH)) if raw else None
        # stars for fallback / decoration
        self.stars = [(random.uniform(0, WORLD_W), random.uniform(0, SH * 0.55), random.uniform(0.6, 1.8)) for _ in range(90)]

    def draw(self, surf: pygame.Surface, cam: Camera):
        if self.img:
            iw = self.img.get_width()
            off = int(cam.x * 0.55) % iw
            for t in range(SW // iw + 2):
                surf.blit(self.img, (t * iw - off, 0))
        else:
            # gradient fallback
            surf.fill(DARK_BLU)
            for (sx, sy, r) in self.stars:
                x = (sx - cam.x * 0.2 + WORLD_W) % WORLD_W
                if 0 <= x <= SW:
                    pygame.draw.circle(surf, (255, 255, 255), (int(x), int(sy)), int(r))

# Audio
def make_tone_sound(freq: float, dur: float, vol: float = 0.35, wave: str = "sq") -> Optional[pygame.mixer.Sound]:
    rate = 22050
    n = int(rate * dur)
    buf = bytearray(n * 2)
    for i in range(n):
        t = i / rate
        env = min(1.0, (n - i) / (rate * 0.04 + 1))
        if wave == "sq":
            v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        elif wave == "tri":
            v = 2 * abs(2 * ((freq * t) % 1) - 1) - 1
        else:
            v = math.sin(2 * math.pi * freq * t)
        s = int(v * vol * env * 32767)
        s = max(-32768, min(32767, s))
        buf[i * 2] = s & 255
        buf[i * 2 + 1] = (s >> 8) & 255
    try:
        return pygame.mixer.Sound(buffer=bytes(buf))
    except Exception:
        return None

def make_ko_sound() -> Optional[pygame.mixer.Sound]:
    """Cinematic KO impact: deep boom + crunch + pitch-drop zing, all layered."""
    try:
        rate = 22050
        dur  = 0.55
        n    = int(rate * dur)
        buf  = bytearray(n * 2)
        for i in range(n):
            t   = i / rate
            env = math.exp(-t * 6.5)   # master exponential decay

            # Layer 1: deep booming thud (60 Hz square wave)
            boom_v  = (1.0 if math.sin(2 * math.pi * 60 * t) >= 0 else -1.0) * 0.52

            # Layer 2: sharp crunch (220 Hz triangle, ultra-fast decay)
            frac    = (220 * t) % 1
            crack_v = (2 * abs(2 * frac - 1) - 1) * 0.32 * math.exp(-t * 22.0)

            # Layer 3: zing — sine that pitch-drops from 900 → 280 Hz
            zing_f  = 900 - 620 * min(1.0, t / 0.20)
            zing_v  = math.sin(2 * math.pi * zing_f * t) * 0.22 * math.exp(-t * 11.0)

            v = (boom_v + crack_v + zing_v) * env
            s = int(max(-1.0, min(1.0, v)) * 32767)
            buf[i * 2]     = s & 255
            buf[i * 2 + 1] = (s >> 8) & 255
        snd = pygame.mixer.Sound(buffer=bytes(buf))
        return snd
    except Exception:
        return None

def load_sound_by_name(preferred: List[str], fallback_tone: Optional[Tuple[float, float, float, str]] = None) -> Optional[pygame.mixer.Sound]:
    # Try exact names first
    for fname in preferred:
        p = try_path(fname, fname.replace(" .", "."), fname.replace(".mp3", " .mp3"))
        if p:
            try:
                return pygame.mixer.Sound(p)
            except Exception:
                pass
    # Try fuzzy contains
    for fname in preferred:
        base = os.path.splitext(fname)[0]
        parts = [p for p in base.replace("-", " ").replace("_", " ").split() if len(p) > 3]
        if parts:
            p = find_by_contains(parts, exts=(".mp3", ".wav", ".ogg"))
            if p:
                try:
                    return pygame.mixer.Sound(p)
                except Exception:
                    pass
    # synth
    if fallback_tone:
        f, d, v, wv = fallback_tone
        return make_tone_sound(f, d, v, wv)
    return None

def setup_audio(opts: Options) -> Dict[str, Optional[pygame.mixer.Sound]]:
    sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
    # SFX
    sounds["attack"]    = load_sound_by_name(["freesound_community-punch-2-37333.mp3"], (250, 0.11, 0.45, "sq"))
    sounds["jump"]      = load_sound_by_name(["edr-8-bit-jump-001-171817.mp3"], (520, 0.09, 0.28, "sine"))
    sounds["hurt"]      = make_tone_sound(120, 0.18, 0.55, "sq")
    sounds["kill"]      = make_tone_sound(760, 0.22, 0.42, "sine")
    sounds["boss_hit"]  = make_tone_sound(80, 0.30, 0.65, "sq")
    sounds["heal"]      = make_tone_sound(660, 0.12, 0.30, "sine")
    sounds["coin"]      = make_tone_sound(980, 0.08, 0.20, "sine")
    sounds["torch"]     = make_tone_sound(420, 0.10, 0.25, "tri")
    sounds["checkpoint"]= make_tone_sound(560, 0.18, 0.28, "sine")
    sounds["kids"]      = load_sound_by_name(["magiaz-baby-crying-327495.mp3"], None)
    sounds["knockout"]  = load_sound_by_name(["OK.mpeg"]) or make_ko_sound()   # user KO sound, synth fallback

    # apply sfx volume
    for k, snd in sounds.items():
        if snd:
            snd.set_volume(opts.sfx_vol)

    # Music: prefer "ready-to-fight"; else any music file containing fight/ready in name
    music_path = try_path("u_9vcmnl4trh-ready-to-fight-474973.mp3")
    if not music_path:
        music_path = find_by_contains(["ready", "fight"], exts=(".mp3", ".ogg", ".wav"))
    if not music_path:
        music_path = find_by_contains(["fight"], exts=(".mp3", ".ogg", ".wav"))

    try:
        if music_path:
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(opts.music_vol)
            pygame.mixer.music.play(-1)
    except Exception:
        pass

    return sounds

# HUD / UI helpers
def draw_hpbar(surf, x, y, w, h, hp, mhp, fg=(200, 30, 30), bg=(40, 40, 50, 180), ghost_hp=None, segments=10):
    # Background with border
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surf, (20, 20, 30), rect.inflate(4, 4), border_radius=4)
    pygame.draw.rect(surf, bg[:3], rect, border_radius=2)
    
    # Ghost bar (lags behind damage)
    if ghost_hp is not None and ghost_hp > hp:
        gw = int(w * min(ghost_hp, mhp) / max(1, mhp))
        pygame.draw.rect(surf, (220, 180, 180), (x, y, gw, h), border_radius=2)

    # Main bar
    if hp > 0:
        bw = max(1, int(w * min(hp, mhp) / max(1, mhp)))
        # Gradient-like effect: draw main color then a lighter highlight top half
        pygame.draw.rect(surf, fg, (x, y, bw, h), border_radius=2)
        highlight = pygame.Surface((bw, h // 2), pygame.SRCALPHA)
        highlight.fill((255, 255, 255, 45))
        surf.blit(highlight, (x, y))

    # Segments
    if segments > 0:
        for i in range(1, segments):
            sx = x + (w * i // segments)
            pygame.draw.line(surf, (0, 0, 0, 100), (sx, y), (sx, y + h - 1), 1)

    # Outer border
    pygame.draw.rect(surf, (220, 220, 230), rect.inflate(2, 2), 2, border_radius=4)

def wrap_text(font, text: str, max_w: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur: List[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        if font.size(trial)[0] <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines

def draw_text_box(surf, x, y, w, h, border_col=(180, 150, 80), fill_alpha=210, border_w=3, radius=18):
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 8, 20, fill_alpha), (0, 0, w, h), border_radius=radius)
    glow = pygame.Surface((w - 8, 6), pygame.SRCALPHA)
    glow.fill((*border_col, 38))
    panel.blit(glow, (4, 4))
    pygame.draw.rect(panel, (*border_col, 220), (0, 0, w, h), border_w, border_radius=radius)
    surf.blit(panel, (x, y))

def ornament_line(surf, cx, y, col=(180, 150, 80), width=220):
    half = width // 2
    pygame.draw.line(surf, col, (cx - half, y), (cx - 14, y), 2)
    pygame.draw.line(surf, col, (cx + 14, y), (cx + half, y), 2)
    pts = [(cx, y - 5), (cx + 6, y), (cx, y + 5), (cx - 6, y)]
    pygame.draw.polygon(surf, col, pts)

class HUD:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 20, bold=True)
        self.sfont = pygame.font.SysFont("Arial", 14)
        self.bfont = pygame.font.SysFont("Arial", 22, bold=True)

    def draw(self, surf: pygame.Surface, hero: Hero, score: int, zone_name: str, boss: Optional[DarkSanta], show_fps: bool, fps_val: float):
        # Update HP target for ghost bar
        if not hasattr(hero, 'hp_ghost'):
            hero.hp_ghost = float(hero.hp)
        
        # Smoothly move ghost bar towards current HP
        if hero.hp_ghost > hero.hp:
            hero.hp_ghost -= 1.2 # Sluggish drop
            if hero.hp_ghost < hero.hp: hero.hp_ghost = hero.hp
        else:
            hero.hp_ghost = hero.hp # Instant fill on heal

        # HUD background panel (taller to fit KO bar)
        draw_text_box(surf, 8, 8, 410, 120, border_col=(100, 140, 180), fill_alpha=160, radius=12)

        hp_pct = hero.hp / max(1, hero.max_hp)
        # Premium color palette
        if hp_pct > 0.6:
            hp_col = (70, 230, 110) # Vibrant Green
        elif hp_pct > 0.3:
            hp_col = (255, 180, 50) # Amber
        else:
            hp_col = (255, 60, 60)  # Bright Red

        # Main HP Bar
        draw_hpbar(surf, 26, 22, 260, 24, hero.hp, hero.max_hp, fg=hp_col, ghost_hp=hero.hp_ghost, segments=5)
        
        # HP Text with shadow
        hp_text = f"{int(hero.hp)} / {hero.max_hp}"
        txt_shadow = self.font.render(hp_text, True, (20, 20, 25))
        txt_main = self.font.render(hp_text, True, SNOW)
        surf.blit(txt_shadow, (300, 23))
        surf.blit(txt_main, (298, 21))

        # Dash cooldown bar (stamina)
        dash_max = 60
        dash_ready = max(0, dash_max - hero.dash_cd)
        dash_col = CYAN if dash_ready >= dash_max else (60, 140, 180)
        draw_hpbar(surf, 26, 54, 180, 12, dash_ready, dash_max, fg=dash_col, bg=(25, 40, 60), segments=0)
        surf.blit(self.sfont.render("DASH READY" if dash_ready >= dash_max else "CHARGING...", True, dash_col), (216, 52))

        # Knockout cooldown bar
        ko_ready = max(0, KO_COOLDOWN - getattr(hero, 'ko_cd', 0))
        ko_full  = (ko_ready >= KO_COOLDOWN)
        ko_col   = GOLD if ko_full else PURPLE
        draw_hpbar(surf, 26, 72, 180, 12, ko_ready, KO_COOLDOWN, fg=ko_col, bg=(40, 20, 60), segments=0)
        if ko_full:
            ko_label = "KNOCKOUT READY!"
        else:
            secs_left = math.ceil(hero.ko_cd / max(1, FPS))
            ko_label = f"KO COOLDOWN: {secs_left}s"
        surf.blit(self.sfont.render(ko_label, True, ko_col), (216, 70))

        # Score & Info logic
        score_txt = self.font.render(f"STARS: {score}", True, GOLD)
        surf.blit(score_txt, (26, 92))
        
        loc_txt = self.sfont.render("• ACT II: THE DARK FOREST •", True, SNOW)
        surf.blit(loc_txt, (220, 95))

        if zone_name:
            zt = self.sfont.render(zone_name.upper(), True, PURPLE)
            draw_text_box(surf, SW // 2 - 100, 8, 200, 32, border_col=PURPLE, fill_alpha=180, radius=8)
            surf.blit(zt, (SW // 2 - zt.get_width() // 2, 15))

        ctrl = self.sfont.render("WASD: MOVE   SPACE: JUMP   Z: ATTACK   X: KNOCKOUT   SHIFT: DASH   P: PAUSE", True, (180, 190, 200))
        surf.blit(ctrl, (SW // 2 - ctrl.get_width() // 2, SH - 24))

        if boss and not boss.dead:
            # Update boss ghost HP
            if not hasattr(boss, 'hp_ghost'): boss.hp_ghost = float(boss.hp)
            if boss.hp_ghost > boss.hp:
                boss.hp_ghost -= 0.8 # slower drop for boss
            else:
                boss.hp_ghost = boss.hp

            bw = 600
            bx = (SW - bw) // 2
            # Boss health panel
            draw_text_box(surf, bx - 20, SH - 100, bw + 40, 68, border_col=RED, fill_alpha=190, radius=10)
            
            fg = [RED, ORANGE, (255, 60, 60)][boss.phase - 1]
            draw_hpbar(surf, bx, SH - 72, bw, 22, boss.hp, boss.max_hp, fg=fg, ghost_hp=boss.hp_ghost, segments=10)
            
            bn = self.bfont.render(f"--- DARK SANTA [PHASE {boss.phase}] ---", True, RED)
            surf.blit(bn, (SW // 2 - bn.get_width() // 2, SH - 104))

        if show_fps:
            ft = self.sfont.render(f"FPS: {fps_val:.1f}", True, (220, 220, 220))
            surf.blit(ft, (SW - ft.get_width() - 10, 10))

# Level & zones
ZONE_NAMES = [
    (0, 1200, "The Entrance"),
    (1200, 2400, "Gnome Territory"),
    (2400, 3600, "The Dark Corridor"),
    (3600, 4800, "Biscuit Wasteland"),
    (4800, 6400, "The Frozen Gauntlet"),
    (6400, WORLD_W, "Dark Santa's Lair"),  # 6400-9000
]

def get_zone_name(x: float) -> str:
    for a, b, name in ZONE_NAMES:
        if a <= x < b:
            return name
    return ""

# Game
class Game:
    S_MENU = 0
    S_INTRO = 1
    S_PLAY = 2
    S_PAUSE = 3
    S_LORE = 4
    S_WIN = 5
    S_OVER = 6
    S_OPTIONS = 7

    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        except Exception:
            pass

        self.save = load_save()
        self.opts = self.save.options

        self.screen = pygame.display.set_mode((SW, SH), pygame.FULLSCREEN if self.opts.fullscreen else 0)
        pygame.display.set_caption("Evil Santa — Level 2: The Dark Forest")
        self.clock = pygame.time.Clock()

        self.input = Input()

        self.font = pygame.font.SysFont("Arial", 22, bold=True)
        self.sfont = pygame.font.SysFont("Arial", 16)
        self.bfont = pygame.font.SysFont("Arial", 54, bold=True)
        # Cached fonts for draw screens (avoid per-frame SysFont calls)
        self._title_font = pygame.font.SysFont("Georgia", 24, bold=True)
        self._head_font = pygame.font.SysFont("Georgia", 16, bold=True)
        self._lore_font = pygame.font.SysFont("Georgia", 14)
        self._narr_font = pygame.font.SysFont("Georgia", 17)
        self._vfont = pygame.font.SysFont("Georgia", 16)
        self._boss_font = pygame.font.SysFont("Georgia", 17, bold=True)
        self._zone_font = pygame.font.SysFont("Georgia", 42, bold=True)

        self.hud = HUD()
        self.camera = Camera()
        self.bg = Background()

        self.sfx = setup_audio(self.opts) if pygame.mixer.get_init() else {}

        self.state = self.S_MENU
        self.menu_idx = 0

        self.toasts: List[Toast] = []
        self.achievements: Set[str] = set()

        self._new_game()

    def _overlay(self, alpha: int):
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((0, 0, 0, alpha))
        self.screen.blit(ov, (0, 0))

    # ── Achievements
    def unlock(self, key: str, title: str, body: str, col=GOLD):
        if key in self.achievements:
            return
        self.achievements.add(key)
        self.toasts.append(Toast(title, body, col, self.font, self.sfont))
        # small sparkle
        self.particles.burst(self.hero.rect.centerx, self.hero.rect.top - 20, col, n=16, spd=4, life=30, r=3)

    def _new_game(self):
        # core state
        self.score_ref = {"score": 0}
        self.zone = ""
        self.zone_flash = 0
        self._seen_enemy_types: Set[str] = set()
        self._encounter_popup: Optional[EnemyEncounterPopup] = None

        self.bg = Background()
        self.particles = Particles()
        self.floats: List[FloatText] = []

        self.hero = Hero(140, GROUND_Y - 100)

        # Zones: 0–1200 | 1200–2500 | 2500–3700 | 3700–4900 | 4900–6500 | 6500–7750 | 7750+ (boss)
        gy = GROUND_Y
        # (x, height_offset, width)
        _plat = [(480,130,160),(900,180,140),(1500,160,160),(1950,200,150),(2300,150,140),
                 (2700,190,150),(3100,220,130),(3450,170,140),(3900,145,150),(4300,210,160),
                 (4650,165,140),(5100,195,150),(5500,155,130),(5900,220,120),(6200,170,140),
                 (6700,145,160),(7100,200,140),(7500,175,180),
                 (7900,180,140),(8250,200,120),(8550,145,130),(8100,270,100)]
        self.platforms: List[Platform] = [Platform(x, gy-h, w) for x, h, w in _plat]

        obs_y = gy - OBSTACLE_H
        _obs = [(450,0),(1250,1),(1800,2),(2550,3),(3000,4),(3350,5),(3750,6),(4150,7),
                (4550,8),(4950,0),(5350,3),(5750,6),(6100,1),(6500,4),(6900,7),(7300,2),(7700,5)]
        self.obstacles: List[Obstacle] = [Obstacle(x, obs_y, fi) for x, fi in _obs]

        _gcx = [200,450,600,850,1150,1600,1800,1950,2250,2700,2950,3150,3500,
                3900,4095,4350,4700,5150,5500,6050,6300,6700,7050,7400,7850]
        _pcx = [(560,150),(970,200),(1580,180),(2040,215),(2375,180),(2775,210),(3165,240),
                (3520,180),(3975,170),(4380,230),(4725,180),(5180,210),(5580,180),(5960,240),
                (6275,190),(6780,180),(7180,220),(7600,220)]
        self.coins: List[Coin] = [Coin(x, gy-55) for x in _gcx] + [Coin(x, gy-h) for x, h in _pcx]

        self.potions: List[Potion] = [Potion(x, gy-60, heal=h) for x, h in [(1050,40),(2400,40),(4475,45),(6250,60)]]
        self.torches: List[TorchPickup] = [TorchPickup(x, gy-60) for x in (2650, 6450)]
        self.checkpoints: List[CheckpointFlag] = [CheckpointFlag(x) for x in (750, 2450, 3650, 4850, 6450)]

        # Enemies: (class, x, zone_left, zone_right)
        self.enemies: List[Enemy] = []
        for cls, ex, zl, zr in [
            (Enemy,350,0,1200),(Enemy,900,0,1200),
            (Enemy,1500,1200,2500),(RedGnome,1950,1200,2500),(RedGnome,2250,1200,2500),
            (RedGnome,2700,2500,3700),(RedGnome,3100,2500,3700),(Enemy,3450,2500,3700),
            (EvilBiscuit,3900,3700,4800),(Enemy,4300,3700,4800),(EvilBiscuit,4650,3700,4875),
            (RedGnome,5100,4800,6500),(EvilBiscuit,5450,4800,6500),(RedGnome,5800,4800,6500),
            (Enemy,6050,4800,6500),(EvilBiscuit,6300,4800,6500),
            (RedGnome,6600,6500,7750),(RedGnome,6850,6500,7750),(EvilBiscuit,7150,6500,7750),(RedGnome,7400,6500,7750),
        ]:
            e = cls(ex, gy - 82); e.zone_left = zl; e.zone_right = zr
            self.enemies.append(e)

        self.spikes: List[SpikeTrap] = [SpikeTrap(x, c) for x, c in [
            (1650,3),(2000,3),(2800,4),(3200,3),(4000,4),(4400,3),
            (5200,4),(5600,3),(5900,5),(6750,4),(7450,5),(8050,3),(8350,4)]]
        self.pendulums: List[PendulumHazard] = [PendulumHazard(x, 40, l, s) for x, l, s in [
            (1750,150,1.5),(2850,170,2.0),(4250,160,1.8),(5450,180,1.6),(6650,165,2.2),(7350,150,2.5)]]

        self.spawners = [[1100,1900,360,0],[2900,4100,300,0],[5200,6300,240,0]]
        self.rolling_balls: List[RollingSnowball] = []

        def gate_check(a, b):
            return lambda enemies: all(e.dead or not (a < e.rect.centerx < b) for e in enemies)
        self.gates: List[GateBarrier] = [
            GateBarrier(1200, enemy_check=gate_check(0,1200)),
            GateBarrier(2500, enemy_check=gate_check(1200,2500)),
            GateBarrier(3700, enemy_check=gate_check(2500,3700)),
            GateBarrier(4900, enemy_check=gate_check(3700,4900)),
            GateBarrier(6500, enemy_check=gate_check(4800,6500)),
            GateBarrier(7750, enemy_check=gate_check(6500,7750), one_way=True),
        ]

        self.dark_zones: List[DarkZone] = [DarkZone(2900,1500,160), DarkZone(6400,700,150)]

        self.boss = DarkSanta(8400, gy - 156)
        self.boss.zone_left = 7750; self.boss.zone_right = WORLD_W
        self.boss_active = False; self.boss_dead_t = 0; self.boss_monologue = 0

        self._arena_heal_cd = 0
        self._boss_minions: List[Enemy] = []
        self._arena_plats = [(7900,gy-180),(8250,gy-200),(8100,gy-270)]

        self.children: List[Child] = [Child(8600, gy - OBSTACLE_H - 60, (255, 150, 90))]

        self._scored_dead_ids: Set[int] = set()
        self._kids_channel = None
        self._kids_playing = False
        if pygame.mixer.get_init():
            self._kids_channel = pygame.mixer.Channel(1)

        self.itimer = 0
        self.state = self.S_INTRO if self.state != self.S_MENU else self.S_MENU

    # ────────────────────────────────────────────────────────────
    # UI screens
    # ────────────────────────────────────────────────────────────
    def draw_menu(self):
        self.bg.draw(self.screen, self.camera)
        self.particles.snow(self.camera.x, n=4)
        self.particles.update()
        self.particles.draw(self.screen, self.camera)

        self._overlay(200)

        cx = SW // 2
        draw_text_box(self.screen, cx - 380, 90, 760, 460, border_col=(200, 160, 50), fill_alpha=220)
        title = self.bfont.render("EVIL SANTA", True, RED)
        shadow = self.bfont.render("EVIL SANTA", True, (60, 10, 10))
        self.screen.blit(shadow, (cx - shadow.get_width() // 2 + 2, 112))
        self.screen.blit(title, (cx - title.get_width() // 2, 110))
        sub = self.font.render("Level 2 — The Dark Forest", True, SNOW)
        self.screen.blit(sub, (cx - sub.get_width() // 2, 170))
        ornament_line(self.screen, cx, 205, col=GOLD, width=300)

        items = ["Start Game", "Enemy Lore", "Options", "Quit"]
        for i, it in enumerate(items):
            col = GOLD if i == self.menu_idx else (220, 220, 230)
            txt = self.font.render(it, True, col)
            self.screen.blit(txt, (cx - txt.get_width() // 2, 250 + i * 52))

        hs = self.sfont.render(f"Highscore: {self.save.highscore}", True, (200, 200, 200))
        self.screen.blit(hs, (cx - hs.get_width() // 2, 470))

        hint = self.sfont.render("Use ↑↓ and ENTER.  ESC quits.", True, (170, 170, 170))
        self.screen.blit(hint, (cx - hint.get_width() // 2, 525))

    def draw_options(self):
        self.bg.draw(self.screen, self.camera)
        self._overlay(210)
        cx = SW // 2
        draw_text_box(self.screen, cx - 360, 120, 720, 400, border_col=GOLD, fill_alpha=230)
        t = self.font.render("OPTIONS", True, GOLD)
        self.screen.blit(t, (cx - t.get_width() // 2, 140))
        ornament_line(self.screen, cx, 172, col=GOLD, width=220)

        lines = [
            f"Music Volume  : {self.opts.music_vol:.2f}   (Left/Right)",
            f"SFX Volume    : {self.opts.sfx_vol:.2f}   (A/D)",
            f"Fullscreen    : {'ON' if self.opts.fullscreen else 'OFF'}   (F)",
            f"Show FPS      : {'ON' if self.opts.show_fps else 'OFF'}   (G)",
            "",
            "Press ESC to return",
        ]
        y = 210
        for ln in lines:
            tx = self.sfont.render(ln, True, (230, 230, 240))
            self.screen.blit(tx, (cx - tx.get_width() // 2, y))
            y += 36

    def draw_lore_screen(self):
        self.bg.draw(self.screen, self.camera)
        self._overlay(215)
        cx = SW // 2
        draw_text_box(self.screen, cx - 450, 40, 900, 560, border_col=(160, 130, 60), fill_alpha=230)

        tt = self._title_font.render("— Enemy Lore —", True, GOLD)
        self.screen.blit(tt, (cx - tt.get_width() // 2, 60))
        ornament_line(self.screen, cx, 92, col=GOLD, width=260)

        sections = [
            ("GREEN GNOMES", LORE_GREEN_GNOMES, (100, 220, 120)),
            ("RED GNOMES", LORE_RED_GNOMES, (220, 100, 100)),
            ("EVIL BISCUIT", LORE_EVIL_BISCUIT, (200, 150, 80)),
            ("DARK SANTA", LORE_DARK_SANTA, (180, 50, 50)),
        ]
        y = 110
        max_w = 900 - 120
        for name, paragraph, col in sections:
            lines = wrap_text(self._lore_font, paragraph, max_w)
            card_h = 42 + len(lines) * 18
            draw_text_box(self.screen, cx - 420, y, 840, card_h, border_col=col, fill_alpha=160, border_w=2, radius=12)
            self.screen.blit(self._head_font.render(name, True, col), (cx - 400, y + 10))
            ly = y + 32
            for l in lines:
                self.screen.blit(self._lore_font.render(l, True, (220, 220, 235)), (cx - 400, ly))
                ly += 18
            y += card_h + 12

        hint = self._lore_font.render("Press ESC to return", True, (180, 180, 180))
        self.screen.blit(hint, (cx - hint.get_width() // 2, 574))

    def draw_pause(self):
        self._overlay(170)
        cx = SW // 2
        draw_text_box(self.screen, cx - 280, 190, 560, 220, border_col=(160, 160, 200), fill_alpha=230)
        t = self.bfont.render("PAUSED", True, (200, 200, 230))
        self.screen.blit(t, (cx - t.get_width() // 2, 210))
        msg = self.font.render("Press P to resume   |   ESC to quit to menu", True, (230, 230, 240))
        self.screen.blit(msg, (cx - msg.get_width() // 2, 320))

    def draw_intro(self):
        self.bg.draw(self.screen, self.camera)
        self.particles.snow(self.camera.x, n=4)
        self.particles.update()
        self.particles.draw(self.screen, self.camera)

        self._overlay(210)

        cx = SW // 2
        pw, ph = 760, 430
        px, py = cx - pw // 2, 70
        draw_text_box(self.screen, px, py, pw, ph, border_col=(200, 160, 50), fill_alpha=230)

        title = self.bfont.render("EVIL SANTA", True, RED)
        shadow = self.bfont.render("EVIL SANTA", True, (60, 10, 10))
        self.screen.blit(shadow, (cx - shadow.get_width() // 2 + 2, py + 24 + 2))
        self.screen.blit(title, (cx - title.get_width() // 2, py + 24))
        sub = self.font.render("Level 2  —  The Dark Forest", True, SNOW)
        self.screen.blit(sub, (cx - sub.get_width() // 2, py + 88))
        ornament_line(self.screen, cx, py + 122, col=GOLD, width=280)

        total = 0
        max_chars = int(self.itimer * 1.1)
        y = py + 150
        for i, ln in enumerate(INTRO_NARRATION):
            visible = max(0, max_chars - total)
            shown = ln[:visible]
            if shown:
                col = GOLD if i == len(INTRO_NARRATION) - 1 else (230, 225, 210)
                txt = self._narr_font.render(shown, True, col)
                self.screen.blit(txt, (cx - txt.get_width() // 2, y))
            total += len(ln)
            y += 30
            if visible < len(ln):
                break

        a = int(128 + 127 * math.sin(self.itimer * 0.09))
        prompt = self.font.render("Press any key to begin", True, GOLD)
        prompt.set_alpha(a)
        self.screen.blit(prompt, (cx - prompt.get_width() // 2, py + 378))

    def draw_win(self):
        self._overlay(180)
        cx = SW // 2
        draw_text_box(self.screen, cx - 340, 120, 680, 360, border_col=GOLD, fill_alpha=220)

        shadow = self.bfont.render("CHILDREN SAVED!", True, (80, 50, 0))
        main = self.bfont.render("CHILDREN SAVED!", True, GOLD)
        self.screen.blit(shadow, (cx - shadow.get_width() // 2 + 2, 146))
        self.screen.blit(main, (cx - main.get_width() // 2, 144))

        sub = self.font.render("Level 2 Complete!", True, WHITE)
        self.screen.blit(sub, (cx - sub.get_width() // 2, 210))
        ornament_line(self.screen, cx, 240, col=GOLD, width=240)

        y = 266
        for ln in VICTORY_SPEECH:
            t = self._vfont.render(ln, True, (215, 215, 255))
            self.screen.blit(t, (cx - t.get_width() // 2, y))
            y += 26

        sc = self.font.render(f"Final Score: {self.score_ref['score']}", True, CYAN)
        self.screen.blit(sc, (cx - sc.get_width() // 2, 400))
        hint = self.sfont.render("Press R to restart   |   ESC to Menu", True, (200, 200, 200))
        self.screen.blit(hint, (cx - hint.get_width() // 2, 440))

    def draw_over(self):
        self._overlay(210)
        cx = SW // 2
        draw_text_box(self.screen, cx - 320, 150, 640, 320, border_col=(160, 30, 30), fill_alpha=225)

        shadow = self.bfont.render("GAME OVER", True, (60, 5, 5))
        main = self.bfont.render("GAME OVER", True, RED)
        self.screen.blit(shadow, (cx - shadow.get_width() // 2 + 2, 176))
        self.screen.blit(main, (cx - main.get_width() // 2, 174))
        ornament_line(self.screen, cx, 246, col=(140, 30, 30), width=220)

        g1 = self._vfont.render(GAME_OVER_LINE1, True, (190, 185, 200))
        g2 = self._vfont.render(GAME_OVER_LINE2, True, (170, 165, 190))
        self.screen.blit(g1, (cx - g1.get_width() // 2, 270))
        self.screen.blit(g2, (cx - g2.get_width() // 2, 296))

        sc = self.font.render(f"Score: {self.score_ref['score']}", True, WHITE)
        self.screen.blit(sc, (cx - sc.get_width() // 2, 344))

        hint = self.sfont.render("Press R to retry   |   ESC to Menu", True, (200, 200, 200))
        self.screen.blit(hint, (cx - hint.get_width() // 2, 414))

    def draw_boss_monologue(self):
        # bottom dialogue box
        cx = SW // 2
        bw, bh = SW - 160, 130
        bx, by = 80, SH - bh - 10
        draw_text_box(self.screen, bx, by, bw, bh, border_col=(180, 40, 40), fill_alpha=230)

        # typewriter based on timer
        progress = 1.0 - self.boss_monologue / 300.0
        max_chars = int(progress * 120)
        total = 0
        y = by + 22
        for ln in BOSS_MONOLOGUE:
            visible = max(0, max_chars - total)
            shown = ln[:visible]
            if shown:
                t = self._boss_font.render(shown, True, (255, 190, 190))
                self.screen.blit(t, (bx + 20, y))
            total += len(ln)
            y += 34
            if visible < len(ln):
                break

    # ────────────────────────────────────────────────────────────
    # Gameplay update
    # ────────────────────────────────────────────────────────────
    def update_play(self, keys):
        # snow
        self.particles.snow(self.camera.x, n=2 if random.random() < 0.6 else 3)

        # zone label
        new_zone = get_zone_name(self.hero.rect.centerx)
        if new_zone != self.zone:
            self.zone = new_zone
            self.zone_flash = 210
        if self.zone_flash > 0:
            self.zone_flash -= 1

        # spawn rolling snowballs
        for sp in self.spawners:
            if self.hero.rect.centerx > sp[0]:
                sp[3] += 1
                if sp[3] >= sp[2]:
                    sp[3] = 0
                    self.rolling_balls.append(RollingSnowball(sp[1], vx=-3.8))
        self.rolling_balls = [b for b in self.rolling_balls if b.alive]

        # gates update — block enemies and hero
        for g in self.gates:
            g.update(self.enemies)
            g.block_enemies(self.enemies)
            g.block_hero(self.hero)

        # boss activation
        if not self.boss_active and abs(self.hero.rect.centerx - self.boss.rect.centerx) < 750:
            self.boss_active = True
            self.boss_monologue = 300
            self.unlock("boss_encounter", "BOSS ENCOUNTER", "Dark Santa emerges from the snow...", col=RED)

        if self.boss_active and self.boss_monologue > 0:
            self.boss_monologue -= 1

        # Update hero
        self.hero.update(
            keys=keys,
            inp=self.input,
            platforms=self.platforms,
            obstacles=self.obstacles,
            gates=self.gates,
            enemies=self.enemies,
            boss=self.boss if self.boss_active else None,
            particles=self.particles,
            floats=self.floats,
            font=self.font,
            sfx=self.sfx,
            camera=self.camera,
            score_ref=self.score_ref,
        )

        # Hazards
        for group in (self.spikes, self.pendulums, self.rolling_balls, self.obstacles):
            for h in group:
                h.update(self.hero, self.particles, self.sfx)

        # Checkpoints, pickups
        for group in (self.checkpoints, self.potions, self.torches):
            for obj in group:
                obj.update(self.hero, self.floats, self.particles, self.font, self.sfx)
        for c in self.coins:
            c.update(self.hero, self.score_ref, self.floats, self.particles, self.font, self.sfx)

        # enemies (coins passed so NPCs run over coins but don't collect)
        for e in self.enemies:
            e.update(self.hero, self.platforms, self.obstacles, self.particles, self.sfx, self.camera, coins=self.coins)

        # First-encounter popup
        if self._encounter_popup:
            if not self._encounter_popup.update():
                self._encounter_popup = None
        else:
            for e in self.enemies:
                if e.dead or abs(e.rect.centerx - self.hero.rect.centerx) > 250:
                    continue
                if isinstance(e, EvilBiscuit):
                    key = "evil_biscuit"
                elif isinstance(e, RedGnome):
                    key = "red_gnome"
                else:
                    key = "green_gnome"
                if key not in self._seen_enemy_types:
                    self._seen_enemy_types.add(key)
                    sprite = e.anims.get(ST_IDLE, [None])[0] if e.anims.get(ST_IDLE) else None
                    hero_sp = self.hero.anims.get(ST_IDLE, [None])[0] if self.hero.anims.get(ST_IDLE) else None
                    self._encounter_popup = EnemyEncounterPopup(key, sprite, hero_sp, self.font, self.sfont)
                    break
            if (self.boss_active and "dark_santa" not in self._seen_enemy_types
                    and not self.boss.dead):
                self._seen_enemy_types.add("dark_santa")
                sprite = self.boss.anims.get(ST_IDLE, [None])[0] if self.boss.anims.get(ST_IDLE) else None
                hero_sp = self.hero.anims.get(ST_IDLE, [None])[0] if self.hero.anims.get(ST_IDLE) else None
                self._encounter_popup = EnemyEncounterPopup("dark_santa", sprite, hero_sp, self.font, self.sfont)
                self.boss_monologue = 0

        # remove dead enemies after linger and score once
        LINGER = 50
        live_enemies = []
        for e in self.enemies:
            if e.dead:
                if id(e) not in self._scored_dead_ids:
                    self._scored_dead_ids.add(id(e))
                    # (score handled in hero attack; still handle if killed by hazards)
                    self.score_ref["score"] += 100
                    self.hero.heal(50)
                    self.floats.append(FloatText(e.rect.centerx, e.rect.top - 20, "+100", GOLD, self.font))
                    self.floats.append(FloatText(e.rect.centerx, e.rect.top - 42, "+50 HP", GREEN, self.font))
                if e.death_t < LINGER:
                    live_enemies.append(e)
            else:
                live_enemies.append(e)
        self.enemies = live_enemies

        # boss update
        if self.boss_active:
            MAX_BOSS_MINIONS = 3
            def spawn_minion(xpos: float):
                alive_minions = sum(1 for e in self._boss_minions if not e.dead)
                if alive_minions >= MAX_BOSS_MINIONS:
                    return
                if random.random() < 0.5:
                    m = RedGnome(int(xpos), GROUND_Y - 82)
                else:
                    m = Enemy(int(xpos), GROUND_Y - 82)
                m.zone_left = 7750
                m.zone_right = WORLD_W
                self.enemies.append(m)
                self._boss_minions.append(m)

            # Arena heal: drop ONE +50 HP potion on a random boss platform
            # Only spawn if hero HP < 100, no uncollected arena potion exists, and cooldown elapsed
            if self._arena_heal_cd > 0:
                self._arena_heal_cd -= 1
            arena_potion_exists = any(
                p.alive and p.heal == 50 and p.x > 7800 for p in self.potions
            )
            if (self.hero.hp < 100 and not self.hero.dead
                    and not self.boss.dead and self._arena_heal_cd == 0
                    and not arena_potion_exists):
                px, py = random.choice(self._arena_plats)
                self.potions.append(Potion(px + 40, py - 30, heal=50))
                self._arena_heal_cd = 300

            self.boss.update(self.hero, self.platforms, self.obstacles, self.particles, self.sfx, self.camera, spawn_enemy_cb=spawn_minion, coins=self.coins)
            if self.boss.dead:
                self.boss_dead_t += 1
                if self.boss_dead_t == 1:
                    self.unlock("boss_defeated", "BOSS DOWN", "Dark Santa has fallen!", col=GOLD)
                    self.score_ref["score"] += 500
                    for ch in self.children:
                        ch.release()
                    for m in self._boss_minions:
                        if not m.dead:
                            m.hp = 0
                            m.dead = True
                            m.death_t = 0
                    self._boss_minions.clear()
                if self.boss_dead_t > 220:
                    self.state = self.S_WIN
                    # update highscore
                    self.save.highscore = max(self.save.highscore, int(self.score_ref["score"]))
                    save_save(self.save)

        # children update
        for ch in self.children:
            ch.update()

        # crying loop when any child visible (and not released)
        if pygame.mixer.get_init() and self._kids_channel and self.sfx.get("kids"):
            cam_x = self.camera.x
            kids_on = any((cam_x - 80) <= ch.x <= (cam_x + SW + 80) and not ch.released for ch in self.children)
            if kids_on and not self._kids_playing:
                self._kids_channel.play(self.sfx["kids"], loops=-1)
                self._kids_playing = True
            if (not kids_on) and self._kids_playing:
                self._kids_channel.stop()
                self._kids_playing = False

        # float texts, particles
        self.floats = [f for f in self.floats if f.update()]
        self.particles.update()

        # achievements
        if self.score_ref["score"] >= 500 and "score_500" not in self.achievements:
            self.unlock("score_500", "TREASURE HUNTER", "Reached 500 score.", col=GOLD)
        if self.hero.hp == self.hero.max_hp and self.hero.rect.centerx > 2500 and "perfect_mid" not in self.achievements:
            self.unlock("perfect_mid", "UNTOUCHED", "Still at full HP past the corridor!", col=GREEN)

        # camera follow
        target = self.hero.rect.centerx - SW // 3
        self.camera.x = lerp(self.camera.x, target, 0.10)
        self.camera.x = clamp(self.camera.x, 0.0, float(WORLD_W - SW))
        self.camera.update()

        # death check
        if self.hero.dead:
            self.state = self.S_OVER
            if self._kids_playing and self._kids_channel:
                self._kids_channel.stop()
                self._kids_playing = False
            self.save.highscore = max(self.save.highscore, int(self.score_ref["score"]))
            save_save(self.save)

    # ────────────────────────────────────────────────────────────
    # Draw world
    # ────────────────────────────────────────────────────────────
    def draw_world(self):
        self.bg.draw(self.screen, self.camera)

        # ground
        gx = -int(self.camera.x + self.camera.shake_dx)
        pygame.draw.rect(self.screen, (35, 25, 15), (gx, GROUND_Y, WORLD_W, SH - GROUND_Y))
        pygame.draw.rect(self.screen, SNOW, (gx, GROUND_Y, WORLD_W, 13))

        # snow particles behind everything
        self.particles.draw(self.screen, self.camera)

        # platforms, obstacles, traps, gates, checkpoints, pickups
        for group in (self.platforms, self.obstacles, self.spikes,
                      self.pendulums, self.rolling_balls, self.gates,
                      self.checkpoints, self.coins, self.potions, self.torches,
                      self.children, self.enemies):
            for obj in group:
                obj.draw(self.screen, self.camera)

        if self.boss_active and (not self.boss.dead or self.boss.death_t < 50):
            self.boss.draw(self.screen, self.camera)

        self.hero.draw(self.screen, self.camera)

        # floats on top
        for f in self.floats:
            f.draw(self.screen, self.camera)

        # dark zone overlay if inside
        for dz in self.dark_zones:
            if dz.inside(self.hero.rect.centerx):
                dz.draw(self.screen, self.hero, self.camera)
                break

        # zone flash big text
        if self.zone_flash > 0:
            a = min(255, self.zone_flash * 2)
            txt = self._zone_font.render(self.zone, True, PURPLE)
            txt.set_alpha(a)
            self.screen.blit(txt, (SW // 2 - txt.get_width() // 2, SH // 3))

        # ── KO CINEMATIC EFFECTS ─────────────────────────────────────────
        hero = self.hero

        # 1) Expanding shockwave rings (world-space circles drawn on screen)
        for w in getattr(hero, "ko_shockwaves", []):
            sx, sy = self.camera.world_to_screen(w["cx"], w["cy"])
            progress = w["r"] / max(1, w["max_r"])
            alpha = int(255 * (1.0 - progress) * 0.85)
            if alpha <= 0:
                continue
            col = w.get("col", GOLD)
            thick = max(1, w["thick"] - int(progress * w["thick"]))
            ring_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (*col, alpha), (sx, sy), int(w["r"]), thick)
            # inner glow
            glow_a = max(0, alpha // 3)
            if glow_a > 0 and int(w["r"]) > 4:
                pygame.draw.circle(ring_surf, (*col, glow_a), (sx, sy), max(1, int(w["r"]) - thick), thick + 2)
            self.screen.blit(ring_surf, (0, 0))

        # 2) Full-screen white-gold flash (brightest right after input)
        ko_flash = getattr(hero, "ko_flash", 0)
        if ko_flash > 0:
            flash_max = 28
            # Start peak white (#ffffff) → fade to gold → transparent
            t = ko_flash / flash_max
            if t > 0.6:
                # Peak: blinding white
                fa = int(255 * ((t - 0.6) / 0.4))
                fc = (255, 255, 255)
            else:
                # Fade: gold tint
                fa = int(200 * (t / 0.6))
                fc = (255, 220, 80)
            flash = pygame.Surface((SW, SH), pygame.SRCALPHA)
            flash.fill((*fc, min(200, fa)))
            self.screen.blit(flash, (0, 0))

        # 3) Slow-motion blue tint while hitstop is active
        ko_hitstop = getattr(hero, "ko_hitstop", 0)
        if ko_hitstop > 0:
            tint = pygame.Surface((SW, SH), pygame.SRCALPHA)
            tint.fill((30, 60, 140, 35))
            self.screen.blit(tint, (0, 0))

        # 4) Big K.O.!! banner — centre-screen, pulsing & scaling
        ko_banner = getattr(hero, "ko_banner", 0)
        if ko_banner > 0:
            banner_max = 110
            t = ko_banner / banner_max
            # slide-in from top, then hold, then fade out
            if t > 0.75:      # sliding in (first 25% of lifetime = last frames)
                slide_t = (t - 0.75) / 0.25
                yoff = int(-200 * slide_t)
                alpha = int(255 * (1.0 - slide_t))
            elif t < 0.18:    # fade out
                yoff = 0
                alpha = int(255 * (t / 0.18))
            else:
                yoff = 0
                alpha = 255

            pulse = 1.0 + 0.06 * math.sin(pygame.time.get_ticks() * 0.018)
            base_sz = 120
            sz = max(20, int(base_sz * pulse))

            if not hasattr(self, "_ko_font_cache") or self._ko_font_cache[0] != sz:
                self._ko_font_cache = (sz, pygame.font.SysFont("Arial", sz, bold=True))
            ko_font = self._ko_font_cache[1]

            # glow aura (slightly bigger, semi-transparent)
            glow_surf = pygame.font.SysFont("Arial", sz + 14, bold=True).render("K.O.!!", True, (255, 200, 0))
            glow_surf.set_alpha(max(0, alpha // 2))
            gx_ = SW // 2 - glow_surf.get_width() // 2
            gy_ = SH // 3 + yoff
            self.screen.blit(glow_surf, (gx_ - 4, gy_ + 4))

            # outline (dark)
            for ox, oy in ((-4,0),(4,0),(0,-4),(0,4)):
                out = ko_font.render("K.O.!!", True, (20, 10, 0))
                out.set_alpha(max(0, alpha))
                self.screen.blit(out, (SW // 2 - out.get_width() // 2 + ox, SH // 3 + yoff + oy))

            # main text (gold → white flicker at peak)
            txt_col = (255, 230, 40) if t > 0.5 else (255, 255, 140)
            ko_txt = ko_font.render("K.O.!!", True, txt_col)
            ko_txt.set_alpha(max(0, alpha))
            self.screen.blit(ko_txt, (SW // 2 - ko_txt.get_width() // 2, SH // 3 + yoff))

    def draw(self, fps_val: float):
        if self.state == self.S_MENU:
            self.draw_menu()
        elif self.state == self.S_OPTIONS:
            self.draw_options()
        elif self.state == self.S_LORE:
            self.draw_lore_screen()
        elif self.state == self.S_INTRO:
            self.draw_intro()
        else:
            # world
            self.draw_world()
            # HUD
            boss = self.boss if self.boss_active else None
            zone_name = self.zone if self.zone_flash > 120 else ""
            self.hud.draw(self.screen, self.hero, self.score_ref["score"], zone_name, boss, self.opts.show_fps, fps_val)

            # boss monologue
            if self.boss_active and self.boss_monologue > 0:
                self.draw_boss_monologue()

            # enemy encounter popup
            if self._encounter_popup:
                self._encounter_popup.draw(self.screen)

            # toasts
            self.toasts = [t for t in self.toasts if t.update()]
            for i, t in enumerate(self.toasts[:3]):
                t.draw(self.screen, 14, 96 + i * 76)

            if self.state == self.S_PAUSE:
                self.draw_pause()
            elif self.state == self.S_WIN:
                self.draw_win()
            elif self.state == self.S_OVER:
                self.draw_over()

        pygame.display.flip()

    # ────────────────────────────────────────────────────────────
    # Main loop
    # ────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            fps_val = self.clock.get_fps()

            self.input.begin_frame()

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.input.feed_event(e)

                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        # ESC behaviour depends on state
                        if self.state == self.S_MENU:
                            pygame.quit()
                            sys.exit()
                        elif self.state == self.S_PLAY:
                            self.state = self.S_PAUSE
                        else:
                            self.state = self.S_MENU

            keys = pygame.key.get_pressed()

            # MENU
            if self.state == self.S_MENU:
                self.itimer += 1
                if self.input.pressed(pygame.K_UP):
                    self.menu_idx = (self.menu_idx - 1) % 4
                if self.input.pressed(pygame.K_DOWN):
                    self.menu_idx = (self.menu_idx + 1) % 4
                if self.input.pressed(pygame.K_RETURN) or self.input.pressed(pygame.K_KP_ENTER):
                    if self.menu_idx == 0:
                        # Show loading screen before heavy init
                        self.screen.fill((0, 0, 0))
                        loading_txt = self.bfont.render("Loading...", True, SNOW)
                        self.screen.blit(loading_txt, (SW // 2 - loading_txt.get_width() // 2, SH // 2 - 30))
                        pygame.display.flip()
                        self._new_game()
                        self.state = self.S_INTRO
                    elif self.menu_idx == 1:
                        self.state = self.S_LORE
                    elif self.menu_idx == 2:
                        self.state = self.S_OPTIONS
                    elif self.menu_idx == 3:
                        pygame.quit()
                        sys.exit()

                # animate background camera slightly
                self.camera.x = (self.camera.x + 0.4) % max(1, WORLD_W - SW)
                self.camera.update()

            # OPTIONS
            elif self.state == self.S_OPTIONS:
                # adjust volumes / toggles
                if self.input.pressed(pygame.K_LEFT):
                    self.opts.music_vol = clamp(self.opts.music_vol - 0.05, 0.0, 1.0)
                    try:
                        pygame.mixer.music.set_volume(self.opts.music_vol)
                    except Exception:
                        pass
                if self.input.pressed(pygame.K_RIGHT):
                    self.opts.music_vol = clamp(self.opts.music_vol + 0.05, 0.0, 1.0)
                    try:
                        pygame.mixer.music.set_volume(self.opts.music_vol)
                    except Exception:
                        pass
                if self.input.pressed(pygame.K_a):
                    self.opts.sfx_vol = clamp(self.opts.sfx_vol - 0.05, 0.0, 1.0)
                    for s in self.sfx.values():
                        if s:
                            s.set_volume(self.opts.sfx_vol)
                if self.input.pressed(pygame.K_d):
                    self.opts.sfx_vol = clamp(self.opts.sfx_vol + 0.05, 0.0, 1.0)
                    for s in self.sfx.values():
                        if s:
                            s.set_volume(self.opts.sfx_vol)
                if self.input.pressed(pygame.K_f):
                    self.opts.fullscreen = not self.opts.fullscreen
                    self.screen = pygame.display.set_mode((SW, SH), pygame.FULLSCREEN if self.opts.fullscreen else 0)
                if self.input.pressed(pygame.K_g):
                    self.opts.show_fps = not self.opts.show_fps

                self.save.options = self.opts
                save_save(self.save)

            # LORE
            elif self.state == self.S_LORE:
                pass

            # INTRO
            elif self.state == self.S_INTRO:
                self.itimer += 1
                if self.itimer > 260 or any(self.input.just_pressed) or any(keys):
                    self.state = self.S_PLAY

            # PLAY
            elif self.state == self.S_PLAY:
                if self.input.pressed(pygame.K_p):
                    self.state = self.S_PAUSE
                else:
                    self.update_play(keys)

            # PAUSE
            elif self.state == self.S_PAUSE:
                if self.input.pressed(pygame.K_p):
                    self.state = self.S_PLAY

            # WIN / OVER
            elif self.state in (self.S_WIN, self.S_OVER):
                if self.input.pressed(pygame.K_r):
                    self._new_game()
                    self.state = self.S_INTRO

            # draw
            self.draw(fps_val)

# Entry
if __name__ == "__main__":
    Game().run()
