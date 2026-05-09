"""
CHRISTMAS RESCUE - LEVEL 2: THE DARK FOREST
ISE Assignment CT029-3-2

CONTROLS: Arrow Keys/WASD=Move, SPACE/Up=Jump, Z=Attack, R=Restart, ESC=Quit

All sprite sheets have been normalised:
  - Tight-cropped per frame, uniform size, bottom-aligned
  - New clean filenames:
      hero_*.png          (90x110 per frame)
      gnome_green_*.png   (72x90  per frame)
      gnome_red_*.png     (72x90  per frame)
      biscuit_*.png       (88x90  per frame)
      darksanta_*.png     (130x160 per frame)
"""

import pygame, math, random, sys, os

try:
    from story import (
        INTRO_NARRATION, BOSS_MONOLOGUE, VICTORY_SPEECH,
        GAME_OVER_LINE1, GAME_OVER_LINE2,
        HERO_VOW,
        LORE_GREEN_GNOMES, LORE_RED_GNOMES, LORE_EVIL_BISCUIT, LORE_DARK_SANTA,
    )
except ImportError:
    INTRO_NARRATION = ["The Dark Forest awaits.", "Rescue the children.", "Press any key to begin."]
    BOSS_MONOLOGUE = ["You should not have come."]
    VICTORY_SPEECH = ["The children are free."]
    GAME_OVER_LINE1 = "The snow covers those who fall."
    GAME_OVER_LINE2 = "The children still wait."
    HERO_VOW = "I will save the children."
    LORE_GREEN_GNOMES = LORE_RED_GNOMES = LORE_EVIL_BISCUIT = LORE_DARK_SANTA = "No lore loaded."

# ── Screen & Physics ─────────────────────────────────────────────
SW, SH   = 1280, 640
FPS      = 60
GRAVITY  = 0.55
JUMP_VEL = -14
GROUND_Y = SH - 110
WORLD_W  = 5000

# ── Colours ──────────────────────────────────────────────────────
WHITE    = (255, 255, 255)
RED      = (220,  30,  30)
DARK_RED = (140,  10,  10)
BLOOD    = (180,  15,  25)   # blood red for NPC hit particles
DARK_BLU = ( 12,  18,  45)
GOLD     = (255, 195,   0)
ORANGE   = (255, 130,   0)
CYAN     = ( 80, 220, 255)
SNOW     = (220, 235, 255)

ST_IDLE = 'idle'
ST_WALK = 'walk'
ST_RUN  = 'run'
ST_JUMP = 'jump'
ST_ATK  = 'attack'
ST_HURT = 'hurt'
ST_DEAD = 'dead'

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# ════════════════════════════════════════════════════════════════
#  ASSET HELPER — all sheets are now uniform (same fw x fh per file)
# ════════════════════════════════════════════════════════════════
def load_anim(fname, fw, fh):
    """Slice a uniform sprite-sheet into frames. Returns [] if missing."""
    path = os.path.join(ASSET_DIR, fname)
    if not os.path.exists(path):
        return []
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except Exception:
        return []
    n = max(1, sheet.get_width() // fw)
    frames = []
    for i in range(n):
        f = pygame.Surface((fw, fh), pygame.SRCALPHA)
        f.blit(sheet, (0, 0), (i * fw, 0, fw, fh))
        frames.append(f)
    return frames


def scale_frames_to(frames, tw, th):
    """Scale every frame to (tw, th) so animations stay a fixed size (e.g. match walk)."""
    if not frames: return frames
    out = []
    for f in frames:
        if f.get_size() == (tw, th):
            out.append(f)
        else:
            out.append(pygame.transform.smoothscale(f, (tw, th)))
    return out


def scale_frames_up_then_down(frames, fw, fh, zoom=1.5):
    """Scale frames up then back to (fw, fh) so small-drawn characters fill the cell (same size as walk)."""
    if not frames: return frames
    big_w, big_h = max(1, int(fw * zoom)), max(1, int(fh * zoom))
    out = []
    for f in frames:
        up = pygame.transform.smoothscale(f, (big_w, big_h))
        out.append(pygame.transform.smoothscale(up, (fw, fh)))
    return out


def _tight_rect(surf, threshold=10):
    """Bounding rect of non-transparent pixels so we draw only the obstacle itself."""
    w, h = surf.get_width(), surf.get_height()
    xmin, ymin, xmax, ymax = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            if surf.get_at((x, y))[3] > threshold:
                xmin = min(xmin, x); xmax = max(xmax, x)
                ymin = min(ymin, y); ymax = max(ymax, y)
    if xmax < xmin or ymax < ymin:
        return pygame.Rect(0, 0, w, h)
    return pygame.Rect(xmin, ymin, xmax - xmin + 1, ymax - ymin + 1)


def load_obstacle_sheet():
    """Load obstacle.png and slice into cells (5 cols x 2 rows). Returns list of surfaces."""
    path = os.path.join(ASSET_DIR, 'obstacle.png')
    if not os.path.exists(path):
        return []
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except Exception:
        return []
    w, h = sheet.get_width(), sheet.get_height()
    cols, rows = 5, 2
    cw, ch = max(1, w // cols), max(1, h // rows)
    frames = []
    for row in range(rows):
        for col in range(cols):
            f = pygame.Surface((cw, ch), pygame.SRCALPHA)
            f.blit(sheet, (0, 0), (col * cw, row * ch, cw, ch))
            frames.append(f)
    return frames


def get_obstacle_tight_rects(sheet):
    """Precompute tight rect per frame so we only draw the obstacle pixels."""
    if not sheet:
        return []
    return [_tight_rect(f) for f in sheet]


def load_bg(fname):
    path = os.path.join(ASSET_DIR, fname)
    if not os.path.exists(path):
        return None
    try:
        return pygame.image.load(path).convert()
    except Exception:
        return None


def safe_color(col):
    return (int(col[0]) & 0xFF, int(col[1]) & 0xFF, int(col[2]) & 0xFF)


# ════════════════════════════════════════════════════════════════
#  PARTICLES
# ════════════════════════════════════════════════════════════════
class Particles:
    def __init__(self): self._p = []

    def burst(self, x, y, col, n=10, spd=5, life=28, radius=4):
        c = safe_color(col)
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(1.0, float(spd))
            self._p.append([float(x), float(y),
                             math.cos(a)*s, math.sin(a)*s - 2.0,
                             c, int(life), int(life), int(radius)])

    def blood_burst(self, x, y, n=22, spd=6, life=24, radius=5):
        """Spawn blood-like particles (red/dark red shades) when NPC is hit."""
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(2.0, float(spd))
            # Mix red and dark red for blood
            r = random.randint(100, 220)
            g = random.randint(5, 35)
            b = random.randint(15, 40)
            c = safe_color((r, g, b))
            self._p.append([float(x), float(y),
                            math.cos(a)*s, math.sin(a)*s - 1.5,
                            c, int(life), int(life), max(2, int(radius))])

    def snow(self, n=2, cam=0):
        """Spawn snow in the current viewport so it falls across the whole level."""
        c = safe_color(SNOW)
        for _ in range(n):
            # Spawn in visible area (world x = cam to cam+SW) so snow appears everywhere
            x_world = cam + random.randint(0, max(1, SW))
            self._p.append([float(x_world), -4.0,
                            random.uniform(-0.4, 0.4), random.uniform(0.6, 1.8),
                            c, random.randint(180, 320),
                            random.randint(180, 320), random.randint(2, 4)])

    def update_draw(self, surf, cam=0):
        """Update and draw particles. cam = camera x so particles trace the world."""
        live = []
        for p in self._p:
            grav = p[9] if len(p) > 9 else 0.18
            p[0] += p[2]; p[1] += p[3]; p[3] += grav; p[5] -= 1
            if p[5] > 0:
                sx = int(p[0]) - cam
                shape = p[8] if len(p) > 8 else 'circle'
                rad = max(1, int(p[7]))
                if shape == 'rect':
                    # Draw as a small rectangle (shell casing)
                    w = rad * 2
                    pygame.draw.rect(surf, p[4], (sx - w//2, int(p[1]) - rad//2, w, rad))
                else:
                    # Shrink circles over time if they have no gravity (fire/smoke)
                    draw_rad = max(1, int(rad * (p[5] / max(1, p[6])))) if grav <= 0 else rad
                    pygame.draw.circle(surf, p[4], (sx, int(p[1])), draw_rad)
                live.append(p)
        self._p = live


# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════
def draw_hpbar(surf, x, y, w, h, hp, mhp, fg=(200,30,30), bg=(60,0,0)):
    pygame.draw.rect(surf, bg, (x, y, w, h))
    if hp > 0:
        pygame.draw.rect(surf, fg, (x, y, max(1, int(w*hp/max(1,mhp))), h))
    pygame.draw.rect(surf, WHITE, (x, y, w, h), 2)


class FloatText:
    def __init__(self, x, y, text, color, font):
        self.x, self.y = float(x), float(y)
        self.text  = text
        self.color = safe_color(color)
        self.font  = font
        self.life  = 70

    def update(self): self.y -= 0.9; self.life -= 1; return self.life > 0

    def draw(self, surf, cam):
        a = max(0, int(255*self.life/70))
        s = self.font.render(self.text, True, self.color)
        s.set_alpha(a)
        surf.blit(s, (int(self.x)-cam-s.get_width()//2, int(self.y)))


# ════════════════════════════════════════════════════════════════
#  SNOWBALL
# ════════════════════════════════════════════════════════════════
class Snowball:
    def __init__(self, x, y, vx):
        self.x=float(x); self.y=float(y)
        self.vx=float(vx); self.vy=-4.0; self.alive=True

    def update(self):
        self.x+=self.vx; self.y+=self.vy; self.vy+=0.22
        if self.y > GROUND_Y+60: self.alive=False

    def draw(self, surf, cam):
        if not self.alive: return
        rx,ry = int(self.x)-cam, int(self.y)
        pygame.draw.circle(surf,(180,210,250),(rx,ry),13)
        pygame.draw.circle(surf,WHITE,(rx,ry),13,2)
        pygame.draw.circle(surf,WHITE,(rx-4,ry-4),3)

    @property
    def rect(self): return pygame.Rect(int(self.x)-13,int(self.y)-13,26,26)


# ════════════════════════════════════════════════════════════════
#  BASE CHARACTER
# ════════════════════════════════════════════════════════════════
class Char:
    def __init__(self, x, y, w, h, hp):
        self.rect      = pygame.Rect(x, y, w, h)
        self.hp        = hp
        self.max_hp    = hp
        self.vy        = 0.0
        self.on_ground = False
        self.facing    = 1
        self.state     = ST_IDLE
        self._af=0; self._at=0; self._asp=6
        self.dead      = False
        self.death_t   = 0   # frames since death (for removal after animation)
        self.hurt_t    = 0
        self.atk_t     = 0
        self.anims     = {}
        self.fc        = WHITE

    def _ss(self, ns, active_anims=None):
        if self.state != ns:
            self.state = ns
            self._at = 0
            self._af = 0
            if ns == ST_ATK:
                # find attack frame count
                anims_dict = active_anims if active_anims is not None else self.anims
                fr = anims_dict.get(ST_ATK)
                self._atk_frames = len(fr) if fr else 1

    def _tick_anim(self, active_anims=None):
        anims_dict = active_anims if active_anims is not None else self.anims
        fr = anims_dict.get(self.state)
        if not fr: return
        self._at += 1
        if self._at >= self._asp: self._at=0; self._af=(self._af+1)%len(fr)

    def _cur_frame(self, active_anims=None):
        anims_dict = active_anims if active_anims is not None else getattr(self, 'anims', {})
        # Note: when we draw we don't always know what active_anims to use because draw is separate from update.
        # So we should just use self.show_rifle if it exists.
        if hasattr(self, 'show_rifle'):
            anims_dict = self.anims_rifle if self.show_rifle else self.anims
            
        fr = anims_dict.get(self.state)
        if not fr: return None
        f = fr[min(self._af, len(fr)-1)]
        return pygame.transform.flip(f, True, False) if self.facing==-1 else f

    def do_gravity(self):
        self.vy += GRAVITY
        self.rect.y += int(self.vy)
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom=GROUND_Y; self.vy=0; self.on_ground=True
        else:
            self.on_ground=False   # do_platforms may restore to True

    def do_platforms(self, platforms):
        if self.vy < 0: return
        for p in platforms:
            if (self.rect.bottom >= p.rect.top and
                    self.rect.bottom < p.rect.top+35 and
                    self.rect.right  > p.rect.left+4 and
                    self.rect.left   < p.rect.right-4):
                if self.rect.bottom > p.rect.top:
                    self.rect.bottom = p.rect.top
                self.vy = 0
                self.on_ground = True

    def do_obstacles(self, obstacles, moving=False, jump_when_facing=True):
        """Block on obstacles. If jump_when_facing, NPCs auto-jump; hero jumps only with Space."""
        if not obstacles: return
        for obs in obstacles:
            if not self.rect.colliderect(obs.rect): continue
            # Push back so we don't overlap
            if self.facing == 1:
                self.rect.right = obs.rect.left
            else:
                self.rect.left = obs.rect.right
        if not jump_when_facing or not moving or not self.on_ground: return
        ahead = 48
        for obs in obstacles:
            if obs.rect.bottom < self.rect.top or obs.rect.top > self.rect.bottom:
                continue
            if self.facing == 1:
                if obs.rect.left >= self.rect.right and obs.rect.left <= self.rect.right + ahead:
                    self.vy = JUMP_VEL
                    break
            else:
                if obs.rect.right <= self.rect.left and obs.rect.right >= self.rect.left - ahead:
                    self.vy = JUMP_VEL
                    break

    def draw(self, surf, cam=0):
        rx = self.rect.x - cam
        f = self._cur_frame()
        if f:
            # bottom-align the sprite inside the hitbox
            fx = rx + self.rect.w//2 - f.get_width()//2
            fy = self.rect.bottom - f.get_height()
            surf.blit(f, (fx, fy))
        else:
            col = RED if (self.hurt_t>0 and self.hurt_t%4<2) else self.fc
            pygame.draw.rect(surf, col,
                             (rx,self.rect.y,self.rect.w,self.rect.h), border_radius=6)
        if not isinstance(self, Hero) and self.hp<self.max_hp and not self.dead:
            draw_hpbar(surf, rx, self.rect.y-10, self.rect.w, 6, self.hp, self.max_hp)

    def take_dmg(self, dmg, particles=None, col=RED):
        if self.dead or self.hurt_t>0: return False
        self.hp -= dmg; self.hurt_t=18
        if particles:
            particles.burst(self.rect.centerx, self.rect.centery,
                            col, n=14, spd=5, life=22, radius=4)
        if self.hp <= 0:
            self.hp=0; self.dead=True; self.death_t=0
            self._ss(ST_DEAD)   # immediately show dead sprite
        return True


# ════════════════════════════════════════════════════════════════
#  HERO  — 90x110 per frame
# ════════════════════════════════════════════════════════════════
class Hero(Char):
    HEAL_ON_KILL = 30
    FW, FH = 90, 110

    def __init__(self, x, y):
        super().__init__(x, y, 52, 100, 200)
        self.fc=(180,140,60); self._asp=5
        self.speed=4; self.dmg=28; self.rng=500
        self._load_anims()
        self.show_rifle = True

    def _load_anims(self):
        fw, fh = self.FW, self.FH
        self.anims = {
            ST_IDLE: load_anim('hero_idle.png',   fw, fh),
            ST_WALK: load_anim('hero_walk.png',   fw, fh),
            ST_RUN:  load_anim('hero_run.png',    fw, fh),
            ST_JUMP: load_anim('hero_jump.png',   fw, fh),
            ST_ATK:  load_anim('hero_attack.png', fw, fh), # Melee/boxing attack animation
            ST_HURT: load_anim('hero_hurt.png',   fw, fh),
            ST_DEAD: load_anim('hero_hurt.png',   fw, fh),
        }
        
        self.anims_rifle = {
            ST_IDLE: load_anim('hero_idle.png',   fw, fh),
            ST_WALK: load_anim('hero_walk.png',   fw, fh),
            ST_RUN:  load_anim('hero_run.png',    fw, fh),
            ST_JUMP: load_anim('hero_jump.png',   fw, fh),
            ST_ATK:  load_anim('hero_idle.png', fw, fh), # Rifle attack just uses idle frame + rifle firing
            ST_HURT: load_anim('hero_hurt.png',   fw, fh),
            ST_DEAD: load_anim('hero_hurt.png',   fw, fh),
        }
        idle = self.anims[ST_IDLE]
        for k in self.anims:
            if not self.anims[k] and idle: self.anims[k]=idle
        self._weapon_img = self._load_rifle()

    def _load_rifle(self):
        """Load rifle from hero_rifle.png, or draw a visible gun as fallback."""
        path = os.path.join(ASSET_DIR, 'hero_rifle.png')
        if os.path.exists(path):
            try:
                sheet = pygame.image.load(path).convert_alpha()
                w, h = sheet.get_width(), sheet.get_height()
                cols = max(1, min(8, w // 32))
                fw, fh = max(1, w // cols), max(1, h // 6)
                frame = pygame.Surface((fw, fh), pygame.SRCALPHA)
                frame.blit(sheet, (0, 0), (0, 0, fw, fh))
                return pygame.transform.smoothscale(frame, (84, 32)) # Scaled up 2x
            except Exception:
                pass
        # Fallback: detailed drawn AK-47
        surf = pygame.Surface((120, 48), pygame.SRCALPHA)
        
        # Colors based on reference image
        WOOD_DARK = (90, 45, 20)
        WOOD_MID = (140, 65, 30)
        WOOD_LIGHT = (180, 85, 40)
        METAL_DARK = (40, 45, 50)
        METAL_MID = (70, 75, 85)
        METAL_LITE = (100, 105, 115)
        
        # 1. Stock (Wood)
        pygame.draw.polygon(surf, WOOD_MID, [(0, 12), (30, 12), (30, 26), (15, 22), (0, 28)])
        pygame.draw.polygon(surf, WOOD_DARK, [(0, 24), (15, 20), (30, 24), (30, 26), (15, 22), (0, 28)])
        pygame.draw.rect(surf, METAL_DARK, (0, 12, 4, 16)) # Stock pad
        
        # 2. Receiver (Metal)
        pygame.draw.rect(surf, METAL_MID, (30, 10, 45, 16))
        pygame.draw.rect(surf, METAL_DARK, (30, 22, 45, 4)) # Lower receiver detail
        pygame.draw.rect(surf, METAL_LITE, (32, 12, 40, 2)) # Dust cover detail
        pygame.draw.rect(surf, METAL_DARK, (70, 14, 5, 2))  # Ejection port
        
        # 3. Grip (Wood/Bakelite)
        pygame.draw.polygon(surf, WOOD_DARK, [(34, 26), (42, 26), (38, 40), (30, 40)])
        
        # 4. Trigger & Guard
        pygame.draw.rect(surf, METAL_DARK, (42, 26, 12, 8), 2) # Guard
        pygame.draw.rect(surf, METAL_MID, (46, 26, 2, 4)) # Trigger
        
        # 5. Magazine (Curved Metal)
        pygame.draw.polygon(surf, METAL_DARK, [(54, 26), (64, 26), (76, 46), (62, 48)])
        pygame.draw.polygon(surf, METAL_MID, [(56, 26), (62, 26), (72, 44), (64, 46)]) # Ribbing highlight
        
        # 6. Handguard (Wood)
        pygame.draw.rect(surf, WOOD_MID, (75, 12, 25, 8))
        pygame.draw.rect(surf, WOOD_DARK, (75, 16, 25, 4))
        pygame.draw.rect(surf, WOOD_LIGHT, (75, 12, 25, 2))
        
        # 7. Barrel & Gas Tube (Metal)
        pygame.draw.rect(surf, METAL_MID, (75, 8, 20, 4)) # Gas tube
        pygame.draw.rect(surf, METAL_DARK, (100, 14, 18, 4)) # Barrel
        pygame.draw.polygon(surf, METAL_DARK, [(114, 6), (116, 6), (116, 14), (114, 14)]) # Front sight
        pygame.draw.polygon(surf, METAL_DARK, [(118, 14), (120, 14), (118, 16)]) # Slant brake
        
        # 8. Rear Sight
        pygame.draw.polygon(surf, METAL_DARK, [(65, 8), (70, 6), (75, 8)])
        
        return surf

    def draw(self, surf, cam=0):
        super().draw(surf, cam)
        if not self._weapon_img or self.dead or not self.show_rifle:
            return
        rx = self.rect.x - cam
        f = self._cur_frame()
        if not f:
            return
        fx = rx + self.rect.w//2 - f.get_width()//2
        fy = self.rect.bottom - f.get_height()
        sw, sh = self._weapon_img.get_width(), self._weapon_img.get_height()
        # Hand position: grips the handle/stock.
        # Hero hand is roughly at fx + 55, fy + 58
        # We want the rifle to be higher and more centered on the hands
        hx = fx + 16 if self.facing == 1 else fx - 40
        hy = fy + 50  # adjust height to match hands rather than waist
        weapon = self._weapon_img
        if self.facing == -1:
            weapon = pygame.transform.flip(weapon, True, False)
        surf.blit(weapon, (hx, hy))

    def update(self, keys, enemies, platforms, particles, sounds, obstacles=None):
        if self.dead:
            self._ss(ST_DEAD); self._tick_anim()
            self.do_gravity(); self.do_platforms(platforms); return

        if self.hurt_t>0: self.hurt_t-=1
        if self.atk_t >0: self.atk_t -=1

        if keys[pygame.K_1]: self.show_rifle = False
        if keys[pygame.K_2]: self.show_rifle = True

        moving = False
        if self.atk_t==0:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.rect.x-=self.speed; self.facing=-1; moving=True
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.rect.x+=self.speed; self.facing= 1; moving=True
        self.rect.x = max(0, self.rect.x)
        if obstacles:
            self.do_obstacles(obstacles, moving, jump_when_facing=False)  # hero jumps with Space only

        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) \
                and self.on_ground and self.atk_t==0:
            self.vy=JUMP_VEL
            snd=sounds.get('jump')
            if snd: snd.play()

        if keys[pygame.K_z] and self.atk_t==0:
            self.atk_t=28
            self._do_attack(enemies, particles, sounds)

        # Physics BEFORE anim state so on_ground is accurate
        self.do_gravity()
        self.do_platforms(platforms)

        # Use right animation dictionary
        active_anims = self.anims_rifle if self.show_rifle else self.anims

        if   self.hurt_t>10:      self._ss(ST_HURT, active_anims)
        elif self.atk_t >0:       self._ss(ST_ATK, active_anims)
        elif not self.on_ground:  self._ss(ST_JUMP, active_anims)
        elif moving:              self._ss(ST_WALK, active_anims)
        else:                     self._ss(ST_IDLE, active_anims)
        self._tick_anim(active_anims)

    def _do_attack(self, enemies, particles, sounds):
        if self.show_rifle:
            snd=sounds.get('attack')
            if snd: snd.play()
            if self.facing==1:
                ar=pygame.Rect(self.rect.right-10, self.rect.y+10, self.rng, self.rect.h-20)
                mx, my = self.rect.right + 75, self.rect.y + 42 # Barrel tip
                ex, ey = self.rect.right + 25, self.rect.y + 42 # Ejection port
                gx, gy = self.rect.right + 40, self.rect.y + 36 # Gas tube
                vx_base = 22.0
                face = 1
            else:
                ar=pygame.Rect(self.rect.left-self.rng+10, self.rect.y+10, self.rng, self.rect.h-20)
                mx, my = self.rect.left - 75, self.rect.y + 42
                ex, ey = self.rect.left - 25, self.rect.y + 42
                gx, gy = self.rect.left - 40, self.rect.y + 36
                vx_base = -22.0
                face = -1

            # 1. Muzzle Flash (Orange/Yellow burst at barrel tip)
            for _ in range(8):
                vx = face * random.uniform(2.0, 10.0)
                vy = random.uniform(-6.0, 6.0)
                c = random.choice([(255,200,50), (255,150,0), (255,255,100)])
                particles._p.append([float(mx), float(my), vx, vy, c, 5, 5, random.randint(4, 12), 'circle', 0.0])
                
            # 2. Receiver Fire (Orange/Yellow escaping top)
            for _ in range(5):
                vx = face * random.uniform(-2.0, 2.0)
                vy = random.uniform(-6.0, -2.0)
                c = random.choice([(255,100,0), (255,150,0), (255,50,0)])
                particles._p.append([float(gx + random.uniform(-10, 10)), float(gy), vx, vy, c, 8, 8, random.randint(3, 8), 'circle', 0.0])

            # 3. Smoke (Gray drifting up and back)
            for _ in range(4):
                vx = face * random.uniform(-3.0, 0.0)
                vy = random.uniform(-3.0, -1.0)
                c = (160, 160, 160)
                particles._p.append([float(gx), float(gy), vx, vy, c, 30, 30, random.randint(4, 8), 'circle', -0.05])
                particles._p.append([float(mx), float(my-5), vx, vy, c, 30, 30, random.randint(3, 6), 'circle', -0.05])

            # 4. Shell Casings (Brass rectangles ejecting backward/upward)
            for _ in range(1):
                vx = face * random.uniform(-6.0, -3.0)
                vy = random.uniform(-8.0, -4.0)
                particles._p.append([float(ex), float(ey), vx, vy, (210, 170, 50), 40, 40, 3, 'rect', 0.5])

            # 5. Fast Bullet trails/scatter (White lines/circles)
            for _ in range(6):
                vx = vx_base * random.uniform(0.7, 1.3)
                vy = random.uniform(-1.0, 1.0)
                r = random.randint(2, 5)
                particles._p.append([float(mx), float(my), vx, vy, WHITE, 12, 12, r, 'circle', 0.0])
        else:
            # Boxing logic
            snd=sounds.get('punch')
            if snd: snd.play()
            if self.facing==1:
                ar=pygame.Rect(self.rect.centerx, self.rect.y-20, 110, self.rect.h+40)
            else:
                ar=pygame.Rect(self.rect.centerx-110, self.rect.y-20, 110, self.rect.h+40)

        for e in enemies:
            if not e.dead and ar.colliderect(e.rect):
                was_alive = not e.dead
                # Melee attack could use a different damage value, let's keep it same for now
                hit = e.take_dmg(self.dmg, particles, BLOOD)
                if hit:
                    particles.blood_burst(e.rect.centerx, e.rect.centery,
                                         n=22, spd=6, life=24, radius=5)
                    if e.dead and was_alive:
                        self.hp=min(self.max_hp, self.hp+self.HEAL_ON_KILL)

    def heal(self, amount):
        self.hp=min(self.max_hp, self.hp+amount)


# ════════════════════════════════════════════════════════════════
#  GENERIC PATROL ENEMY
# ════════════════════════════════════════════════════════════════
class Enemy(Char):
    PFX      = 'gnome_green'
    FW=72; FH=90                     # uniform after normalisation
    BASE_HP=80; BASE_SPD=2.0; BASE_DMG=10; BASE_PAT=200; BASE_COOL=65

    def __init__(self, x, y):
        super().__init__(x, y, 48, 80, self.BASE_HP)
        self.max_hp=self.BASE_HP; self.hp=self.BASE_HP
        self.speed=self.BASE_SPD; self.dmg=self.BASE_DMG
        self.pat=self.BASE_PAT; self.cool=0
        self.ox=x; self.facing=-1; self._asp=7
        self._load_anims()

    def _load_anims(self):
        p=self.PFX; fw,fh=self.FW,self.FH
        dead_frames = load_anim(f'{p}_dead.png', fw, fh)
        # Use dead sheet for full sequence: frame 0 = first hit, 1..n-2 = damage, last = death
        if len(dead_frames) >= 2:
            hurt_frames = dead_frames[:-1]           # first hit + damage (all but last)
            dead_hold   = [dead_frames[-1]]          # last frame = dying, hold it
            # Zoom death/hurt so small-drawn character matches normal NPC size
            st_hurt = scale_frames_up_then_down(hurt_frames, fw, fh, zoom=1.5)
            st_dead = scale_frames_up_then_down(dead_hold, fw, fh, zoom=1.5)
        else:
            st_hurt = scale_frames_up_then_down(dead_frames or load_anim(f'{p}_hurt.png', fw, fh), fw, fh, 1.5)
            st_dead = scale_frames_up_then_down(dead_frames or [], fw, fh, 1.5)
        self.anims = {
            ST_IDLE: load_anim(f'{p}_idle.png',   fw, fh),
            ST_WALK: load_anim(f'{p}_walk.png',   fw, fh),
            ST_ATK:  load_anim(f'{p}_attack.png', fw, fh),
            ST_HURT: st_hurt,
            ST_DEAD: st_dead,
        }
        idle = self.anims[ST_IDLE]
        if not self.anims[ST_DEAD]:
            self.anims[ST_DEAD] = self.anims.get(ST_HURT) or idle
        for k in self.anims:
            if not self.anims[k] and idle: self.anims[k] = idle

    def update(self, hero, platforms, particles, sounds, obstacles=None):
        if self.dead:                          # locked — nothing overwrites dead
            self.death_t += 1
            self._ss(ST_DEAD); self._tick_anim()
            self.do_gravity(); self.do_platforms(platforms); return

        if self.hurt_t>0: self.hurt_t-=1
        if self.cool  >0: self.cool  -=1

        dx=hero.rect.centerx-self.rect.centerx
        dist=abs(dx)
        same_level = abs(self.rect.centery-hero.rect.centery) < 90

        if dist<380 and not hero.dead and same_level:
            self.facing = 1 if dx>0 else -1
            if dist>55:
                self.rect.x+=self.facing*self.speed; self._ss(ST_WALK)
            else:
                self._ss(ST_ATK)
                if self.cool==0:
                    self.cool=self.BASE_COOL
                    if hero.take_dmg(self.dmg, particles, RED):
                        snd=sounds.get('hurt')
                        if snd: snd.play()
        else:
            self.rect.x+=self.facing*self.speed*0.5
            if abs(self.rect.x-self.ox)>self.pat: self.facing*=-1
            self._ss(ST_WALK)

        if obstacles:
            self.do_obstacles(obstacles, moving=True)
        self.do_gravity(); self.do_platforms(platforms)
        if self.hurt_t>10: self._ss(ST_HURT)
        self._tick_anim()


# ── Enemy subclasses ──────────────────────────────────────────────
class GreenGnome(Enemy):
    PFX='gnome_green'; FW=72; FH=90
    BASE_HP=80;  BASE_SPD=2.0; BASE_DMG=10; BASE_PAT=200; BASE_COOL=65
    def __init__(self,x,y): super().__init__(x,y); self.fc=(30,160,30)

class RedGnome(Enemy):
    PFX='gnome_red'; FW=72; FH=90
    BASE_HP=130; BASE_SPD=2.8; BASE_DMG=18; BASE_PAT=250; BASE_COOL=55
    def __init__(self,x,y): super().__init__(x,y); self.fc=(180,50,30)

class EvilBiscuit(Enemy):
    PFX='biscuit'; FW=88; FH=90
    BASE_HP=200; BASE_SPD=3.2; BASE_DMG=22; BASE_PAT=280; BASE_COOL=50
    def __init__(self,x,y): super().__init__(x,y); self.fc=(160,90,40)


# ════════════════════════════════════════════════════════════════
#  DARK SANTA BOSS  — 130x160 per frame
# ════════════════════════════════════════════════════════════════
class DarkSanta(Char):
    FW, FH = 130, 160

    def __init__(self, x, y):
        # 56 HP = 2 hero punches (28 dmg each)
        super().__init__(x, y, 110, 155, 56)
        self.fc=DARK_RED; self._asp=6
        self.speed=2.0; self.dmg=35
        self.cool=0; self.phase=1; self.balls=[]
        self._load_anims()

    def _load_anims(self):
        fw,fh=self.FW,self.FH
        dead_frames = load_anim('darksanta_dead.png', fw, fh)
        # Same as small enemies: dead sheet = first hit + damage + last frame death
        if len(dead_frames) >= 2:
            hurt_frames = dead_frames[:-1]
            dead_hold   = [dead_frames[-1]]
            st_hurt = scale_frames_up_then_down(hurt_frames, fw, fh, zoom=1.5)
            st_dead = scale_frames_up_then_down(dead_hold, fw, fh, zoom=1.5)
        else:
            st_hurt = scale_frames_up_then_down(
                dead_frames or load_anim('darksanta_hurt.png', fw, fh), fw, fh, 1.5)
            st_dead = scale_frames_up_then_down(dead_frames or [], fw, fh, 1.5)
        self.anims = {
            ST_IDLE: load_anim('darksanta_idle.png',   fw, fh),
            ST_WALK: load_anim('darksanta_walk.png',   fw, fh),
            ST_RUN:  load_anim('darksanta_run.png',    fw, fh),
            ST_ATK:  load_anim('darksanta_attack.png', fw, fh),
            ST_HURT: st_hurt,
            ST_DEAD: st_dead,
        }
        idle=self.anims[ST_IDLE]
        if not self.anims[ST_DEAD]:
            self.anims[ST_DEAD]=self.anims.get(ST_HURT) or idle
        for k in self.anims:
            if not self.anims[k] and idle: self.anims[k]=idle

    def update(self, hero, platforms, particles, sounds, obstacles=None):
        self._update_balls(hero, particles, sounds)
        if self.dead:
            self.death_t += 1
            self._ss(ST_DEAD); self._tick_anim()
            self.do_gravity(); self.do_platforms(platforms); return

        if self.hurt_t>0: self.hurt_t-=1
        if self.cool  >0: self.cool  -=1

        ratio=self.hp/max(1,self.max_hp)
        self.phase=1 if ratio>0.66 else(2 if ratio>0.33 else 3)
        spd=self.speed+(self.phase-1)*0.8

        dx=hero.rect.centerx-self.rect.centerx
        self.facing=1 if dx>0 else -1
        dist=abs(dx)

        if dist>120:
            self.rect.x+=self.facing*spd
            if obstacles:
                self.do_obstacles(obstacles, moving=True)
            self._ss(ST_RUN if self.phase==3 else ST_WALK)
        else:
            self._ss(ST_ATK)
            if self.cool==0:
                self.cool=max(30, 70-self.phase*15)
                if hero.take_dmg(self.dmg, particles, ORANGE):
                    snd=sounds.get('boss_hit')
                    if snd: snd.play()
                if self.phase>=2:
                    self.balls.append(
                        Snowball(self.rect.centerx, self.rect.centery-20,
                                 5.5*self.facing))

        self.do_gravity(); self.do_platforms(platforms)
        if self.hurt_t>10: self._ss(ST_HURT)
        self._tick_anim()

    def _update_balls(self, hero, particles, sounds):
        live=[]
        for b in self.balls:
            b.update()
            if b.alive:
                if not hero.dead and b.rect.colliderect(hero.rect):
                    if hero.take_dmg(14, particles, CYAN):
                        snd=sounds.get('hurt')
                        if snd: snd.play()
                    b.alive=False
                else: live.append(b)
        self.balls=live

    def draw(self, surf, cam=0):
        super().draw(surf, cam)
        for b in self.balls: b.draw(surf, cam)


# ════════════════════════════════════════════════════════════════
#  PLATFORM
# ════════════════════════════════════════════════════════════════
class Platform:
    def __init__(self, x, y, w): self.rect=pygame.Rect(x,y,w,18)

    def draw(self, surf, cam):
        rx=self.rect.x-cam
        pygame.draw.rect(surf,(80,50,25),(rx,self.rect.y,self.rect.w,self.rect.h),border_radius=4)
        pygame.draw.rect(surf,SNOW,(rx,self.rect.y,self.rect.w,5),border_radius=4)
        pygame.draw.rect(surf,WHITE,(rx,self.rect.y,self.rect.w,self.rect.h),2,border_radius=4)


# ════════════════════════════════════════════════════════════════
#  OBSTACLE — characters jump when facing one
# ════════════════════════════════════════════════════════════════
OBSTACLE_W, OBSTACLE_H = 48, 56   # hitbox (jumpable height)

class Obstacle:
    _sheet = None   # loaded once
    _tight_rects = None  # one per frame, computed once

    def __init__(self, x, y, frame_index=0):
        # Bottom of obstacle at y+h = ground; rect is hitbox
        self.rect = pygame.Rect(x, y, OBSTACLE_W, OBSTACLE_H)
        self.frame_index = frame_index % max(1, len(self._get_sheet()))

    @classmethod
    def _get_sheet(cls):
        if cls._sheet is None:
            cls._sheet = load_obstacle_sheet()
            cls._tight_rects = get_obstacle_tight_rects(cls._sheet)
        return cls._sheet

    def draw(self, surf, cam):
        sheet = self._get_sheet()
        if not sheet or self.frame_index >= len(sheet): return
        rx = self.rect.x - cam
        img = sheet[self.frame_index]
        tight = self._tight_rects[self.frame_index] if self._tight_rects and self.frame_index < len(self._tight_rects) else _tight_rect(img)
        if tight.w <= 0 or tight.h <= 0: return
        crop = img.subsurface(tight)
        # Scale to fit hitbox height, keep aspect; bottom-align on ground
        scale = OBSTACLE_H / max(1, crop.get_height())
        nw = max(8, min(OBSTACLE_W * 2, int(crop.get_width() * scale)))
        nh = max(8, int(crop.get_height() * scale))
        scaled = pygame.transform.smoothscale(crop, (nw, nh))
        by = self.rect.bottom - nh  # bottom of image on ground
        surf.blit(scaled, (rx + (OBSTACLE_W - nw) // 2, by))


# ════════════════════════════════════════════════════════════════
#  CHILD NPC
# ════════════════════════════════════════════════════════════════
_CHILD_COLS=[(255,180,100),(180,255,130),(130,200,255),(255,130,200),(255,220,80)]

class Child:
    def __init__(self,x,y,idx=0):
        self.x=float(x); self.y=float(y)
        self.col=_CHILD_COLS[idx%len(_CHILD_COLS)]
        self.released=False; self.vy=0.0; self.t=0

    def release(self): self.released=True; self.vy=-9.0

    def update(self):
        if not self.released: return
        self.t+=1; self.y+=self.vy
        if self.y<GROUND_Y-60: self.vy+=0.4
        else: self.y=GROUND_Y-60; self.vy=0.0

    def draw(self, surf, cam):
        rx=int(self.x)-cam; ry=int(self.y)
        bob=int(math.sin(self.t*0.15)*3) if self.released else 0
        pygame.draw.rect(surf,self.col,(rx-11,ry+bob,22,28),border_radius=5)
        pygame.draw.circle(surf,(255,210,165),(rx,ry-10+bob),12)
        pygame.draw.polygon(surf,RED,[(rx-10,ry-20+bob),(rx+10,ry-20+bob),(rx+2,ry-36+bob)])
        pygame.draw.circle(surf,WHITE,(rx+2,ry-36+bob),4)
        pygame.draw.rect(surf,RED,(rx-11,ry+3+bob,22,6))
        if self.released and self.t<80:
            for i in range(5):
                a=math.radians(i*72+self.t*12)
                pygame.draw.circle(surf,GOLD,
                    (int(rx+math.cos(a)*24),int(ry+math.sin(a)*18+bob)),4)


# ════════════════════════════════════════════════════════════════
#  BACKGROUND
# ════════════════════════════════════════════════════════════════
class Background:
    def __init__(self):
        raw=load_bg('background.jpg')
        self.img=pygame.transform.scale(raw,(SW,SH)) if raw else None

    def draw(self, surf, cam):
        if self.img:
            iw=self.img.get_width()
            off=int(cam*0.6)%iw
            for t in range(SW//iw+2):
                surf.blit(self.img,(t*iw-off,0))
        else:
            surf.fill(DARK_BLU)
            for i in range(60):
                sx=(i*137+int(cam*0.2))%SW
                sy=(i*97)%(SH//2)
                pygame.draw.circle(surf,WHITE,(sx,sy),2)


# ════════════════════════════════════════════════════════════════
#  AUDIO
# ════════════════════════════════════════════════════════════════
def make_sounds():
    rate=22050
    def tone(freq,dur,vol=0.35,wave='sq'):
        n=int(rate*dur); buf=bytearray(n*2)
        for i in range(n):
            t=i/rate; env=min(1.0,(n-i)/(rate*0.04+1))
            if wave=='sq':    v=1.0 if math.sin(2*math.pi*freq*t)>=0 else -1.0
            elif wave=='tri': v=2*abs(2*(freq*t%1)-1)-1
            else:             v=math.sin(2*math.pi*freq*t)
            s=max(-32768,min(32767,int(v*vol*env*32767)))
            buf[i*2]=s&0xFF; buf[i*2+1]=(s>>8)&0xFF
        try: return pygame.mixer.Sound(buffer=bytes(buf))
        except: return None
    sounds={}
    try:
        attack_path = os.path.join(ASSET_DIR, 'freesound_community-battle-rifle-42734.mp3')
        if os.path.exists(attack_path):
            sounds['attack'] = pygame.mixer.Sound(attack_path)
        else:
            sounds['attack'] = tone(250,0.11,0.45,'sq')
    except Exception:
        try: sounds['attack'] = tone(250,0.11,0.45,'sq')
        except: pass
    try:
        jump_path = os.path.join(ASSET_DIR, 'edr-8-bit-jump-001-171817.mp3')
        if os.path.exists(jump_path):
            sounds['jump'] = pygame.mixer.Sound(jump_path)
        else:
            sounds['jump'] = tone(480,0.09,0.28,'sine')
    except Exception:
        try: sounds['jump'] = tone(480,0.09,0.28,'sine')
        except: pass
    try:
        sounds['hurt']    =tone(120,0.18,0.55,'sq')
        sounds['kill']    =tone(700,0.22,0.45,'sine')
        sounds['boss_hit']=tone( 75,0.28,0.65,'sq')
        sounds['heal']    =tone(660,0.12,0.30,'sine')
    except: pass

    try:
        punch_path = os.path.join(ASSET_DIR, 'freesound_community-punch-2-37333.mp3')
        if os.path.exists(punch_path):
            sounds['punch'] = pygame.mixer.Sound(punch_path)
        else:
            sounds['punch'] = tone(150,0.08,0.4,'sq')
    except Exception:
        try: sounds['punch'] = tone(150,0.08,0.4,'sq')
        except: pass
    try:
        win_path = os.path.join(ASSET_DIR, 'floraphonic-you-win-sequence-1-183948.mp3')
        if os.path.exists(win_path):
            sounds['win'] = pygame.mixer.Sound(win_path)
        else:
            sounds['win'] = tone(550,0.45,0.38,'sine')
    except Exception:
        try: sounds['win'] = tone(550,0.45,0.38,'sine')
        except: pass
    try:
        kids_cry_path = os.path.join(ASSET_DIR, 'magiaz-baby-crying-327495.mp3')
        if os.path.exists(kids_cry_path):
            sounds['kids_crying'] = pygame.mixer.Sound(kids_cry_path)
        else:
            sounds['kids_crying'] = None
    except Exception:
        sounds['kids_crying'] = None
    # Death/fail sound
    try:
        fail_path = os.path.join(ASSET_DIR, 'mixkit-wrong-answer-fail-notification-946.wav')
        if os.path.exists(fail_path):
            sounds['death'] = pygame.mixer.Sound(fail_path)
        else:
            sounds['death'] = tone(150, 0.5, 0.5, 'sq')
    except Exception:
        sounds['death'] = None
    # Background music — Christmas theme (used in Level 1 & Level 2)
    try:
        music_path = os.path.join(ASSET_DIR, 'sigmamusicart-christmas-453699.mp3')
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(-1)  # -1 = loop forever
        else:
            fallback = os.path.join(ASSET_DIR, 'u_9vcmnl4trh-ready-to-fight-474973.mp3')
            if os.path.exists(fallback):
                pygame.mixer.music.load(fallback)
                pygame.mixer.music.play(-1)
    except Exception:
        pass
    return sounds


# ════════════════════════════════════════════════════════════════
#  HUD
# ════════════════════════════════════════════════════════════════
class HUD:
    def __init__(self):
        self.font =pygame.font.SysFont('Arial',20,bold=True)
        self.sfont=pygame.font.SysFont('Arial',15)
        self.bfont=pygame.font.SysFont('Arial',22,bold=True)

    def draw(self, surf, hero, score, boss=None):
        panel=pygame.Surface((360,70),pygame.SRCALPHA)
        panel.fill((0,0,0,150)); surf.blit(panel,(8,8))
        draw_hpbar(surf,18,16,220,18,hero.hp,hero.max_hp)
        hp_pct=hero.hp/hero.max_hp
        hp_col=(100,220,100) if hp_pct>0.5 else (255,200,0) if hp_pct>0.25 else RED
        surf.blit(self.sfont.render(f'HP  {hero.hp}/{hero.max_hp}',True,hp_col),(244,18))
        surf.blit(self.font.render(f'Score: {score}',True,GOLD),(18,40))
        surf.blit(self.sfont.render('Level 2',True,SNOW),(220,42))
        ctrl=self.sfont.render('Arrows/WASD Move   SPACE Jump   Z Attack',True,(180,180,180))
        surf.blit(ctrl,(SW//2-ctrl.get_width()//2,SH-24))
        if boss and not boss.dead:
            bw=480; bx=(SW-bw)//2
            bp=pygame.Surface((bw+40,52),pygame.SRCALPHA)
            bp.fill((0,0,0,165)); surf.blit(bp,(bx-20,SH-82))
            fg=[(200,30,30),(255,110,0),(255,30,30)][boss.phase-1]
            draw_hpbar(surf,bx,SH-68,bw,20,boss.hp,boss.max_hp,fg=fg)
            bn=self.bfont.render('☠  DARK SANTA  ☠',True,RED)
            surf.blit(bn,(SW//2-bn.get_width()//2,SH-92))
            surf.blit(self.sfont.render(f'Phase {boss.phase}',True,(255,180,0)),(bx+bw+6,SH-66))


# Map enemy class name -> (lore_paragraph, "We are..." title, color) for encounter popups
ENEMY_LORE = {
    'GreenGnome':  (LORE_GREEN_GNOMES,  'We are the Green Gnomes.',  (100, 220, 120)),
    'RedGnome':    (LORE_RED_GNOMES,    'We are the Red Gnomes.',    (220, 100, 100)),
    'EvilBiscuit': (LORE_EVIL_BISCUIT,  'We are the Evil Biscuit.',  (200, 150, 80)),
    'DarkSanta':   (LORE_DARK_SANTA,    'I am Dark Santa.',          (180, 50, 50)),
}


def _wrap_text(font, text, max_width):
    """Split text into lines that fit within max_width pixels."""
    words = text.split()
    lines = []
    current = []
    for w in words:
        trial = " ".join(current + [w])
        if font.size(trial)[0] <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


# ════════════════════════════════════════════════════════════════
#  MAIN GAME
# ════════════════════════════════════════════════════════════════
class Game:
    S_INTRO=0; S_PLAY=1; S_WIN=2; S_OVER=3; S_LORE=4

    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=22050,size=-16,channels=2,buffer=512)
        self.screen=pygame.display.set_mode((SW,SH))
        pygame.display.set_caption('Christmas Rescue — Level 2: The Dark Forest')
        self.clock =pygame.time.Clock()
        self.font  =pygame.font.SysFont('Arial',22,bold=True)
        self.bfont =pygame.font.SysFont('Arial',52,bold=True)
        self.sfont =pygame.font.SysFont('Arial',16)
        self.sounds=make_sounds()
        self.hud   =HUD()
        self._new_game()

    def _new_game(self):
        self.state=self.S_INTRO
        self.cam=0.0; self.score=0; self.itimer=0
        # Restart background music
        try:
            if pygame.mixer.music.get_busy(): # Check if something is already playing
                pygame.mixer.music.stop()
        
            # Only play if something is actually loaded
            pygame.mixer.music.play(-1)
        except pygame.error:
            print("Note: Music could not be played because no file is loaded.")
            
        self.bg=Background()
        self.particles=Particles()
        self.floats=[]
        self.hero=Hero(140, GROUND_Y-100)
        self.platforms=[
            Platform( 580,GROUND_Y-105,160), Platform( 880,GROUND_Y-168,130),
            Platform(1280,GROUND_Y-125,190), Platform(1680,GROUND_Y-185,140),
            Platform(2080,GROUND_Y- 95,180), Platform(2480,GROUND_Y-205,120),
            Platform(2880,GROUND_Y-148,160), Platform(3280,GROUND_Y- 85,200),
        ]
        # Obstacles: (x, y_top). y = GROUND_Y - OBSTACLE_H so they sit on ground
        obs_y = GROUND_Y - OBSTACLE_H
        self.obstacles = [
            Obstacle( 620, obs_y, 0), Obstacle(1250, obs_y, 1), Obstacle(1950, obs_y, 2),
            Obstacle(2650, obs_y, 3), Obstacle(3380, obs_y, 4), Obstacle(4100, obs_y, 5),
        ]
        self.enemies=[
            GreenGnome ( 680,GROUND_Y-80),
            GreenGnome (1050,GROUND_Y-80),
            RedGnome   (1780,GROUND_Y-80),
            RedGnome   (2180,GROUND_Y-80),
            EvilBiscuit(2800,GROUND_Y-80),
        ]
        self.boss       =DarkSanta(4250,GROUND_Y-155)
        self.boss_active=False
        self.boss_dead_t=0
        self.children   =[Child(4060+i*40,GROUND_Y-60,i) for i in range(5)]
        self._scored    =set()
        self._kids_crying_playing = False
        self._kids_cry_channel = pygame.mixer.Channel(1)
        self._kids_cry_channel.stop()
        self._boss_monologue_timer = 0
        self._lore_shown = set()  # enemy type names already shown
        self._encounter_lore_timer = 0
        self._encounter_lore_title = None
        self._encounter_lore_lines = []

    def _update_camera(self):
        target=self.hero.rect.centerx-SW//3
        self.cam+=(target-self.cam)*0.10
        self.cam=max(0.0,min(self.cam,float(WORLD_W-SW)))

    def update(self):
        keys=pygame.key.get_pressed()
        if random.random()<0.5: self.particles.snow(2, int(self.cam))
        else: self.particles.snow(1, int(self.cam))

        if self.state==self.S_INTRO:
            self.itimer+=1
            if keys[pygame.K_l]:
                self.state=self.S_LORE
                return
            key_pressed = any(keys[k] for k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_z, pygame.K_r))
            if self.itimer>220 or key_pressed: self.state=self.S_PLAY
            return
        if self.state==self.S_LORE:
            return
        if self.state in(self.S_WIN,self.S_OVER): return

        all_e=self.enemies+([self.boss] if self.boss_active else [])
        # Show enemy lore when hero first faces each type
        if self._encounter_lore_timer > 0:
            self._encounter_lore_timer -= 1
        else:
            for e in all_e:
                if e.dead: continue
                tname = type(e).__name__
                if tname not in ENEMY_LORE or tname in self._lore_shown: continue
                dist = abs(self.hero.rect.centerx - e.rect.centerx)
                same_level = abs(self.hero.rect.centery - e.rect.centery) < 100
                if dist < 420 and same_level:
                    self._lore_shown.add(tname)
                    para, title, col = ENEMY_LORE[tname]
                    lore_font = pygame.font.SysFont('Arial', 15)
                    self._encounter_lore_title = (title, col)
                    self._encounter_lore_lines = _wrap_text(lore_font, para, SW - 100)
                    self._encounter_lore_timer = 360  # ~6 sec
                    break
        self.hero.update(keys,all_e,self.platforms,self.particles,self.sounds,self.obstacles)

        for e in self.enemies:
            e.update(self.hero,self.platforms,self.particles,self.sounds,self.obstacles)
            if e.dead and id(e) not in self._scored:
                self._scored.add(id(e))
                self.score+=100
                self.hero.heal(Hero.HEAL_ON_KILL)
                for snd_key in('heal','kill'):
                    snd=self.sounds.get(snd_key)
                    if snd: snd.play()
                self.floats.append(
                    FloatText(e.rect.centerx,e.rect.top-20,'+100',GOLD,self.font))
                self.floats.append(
                    FloatText(e.rect.centerx,e.rect.top-45,
                              f'+{Hero.HEAL_ON_KILL}HP',(100,255,100),self.font))

        # Remove dead enemies after death animation has shown (~0.8s)
        DEATH_LINGER = 50
        self.enemies = [e for e in self.enemies if not e.dead or e.death_t < DEATH_LINGER]

        if not self.boss_active and \
                abs(self.hero.rect.centerx-self.boss.rect.centerx)<700:
            self.boss_active = True
            self._boss_monologue_timer = 320  # ~5 sec of boss monologue

        if self.boss_active:
            if self._boss_monologue_timer > 0:
                self._boss_monologue_timer -= 1
            self.boss.update(self.hero,self.platforms,self.particles,self.sounds,self.obstacles)
            if self.boss.dead and id(self.boss) not in self._scored:
                self._scored.add(id(self.boss))
                self.score+=500
                pygame.mixer.music.stop()
                snd=self.sounds.get('win')
                if snd: snd.play()
                for c in self.children: c.release()
            if self.boss.dead:
                self.boss_dead_t+=1
                if self.boss_dead_t>200:
                    self.state=self.S_WIN
                    if self._kids_crying_playing:
                        self._kids_cry_channel.stop()
                        self._kids_crying_playing = False

        for c in self.children: c.update()
        self.floats=[f for f in self.floats if f.update()]
        self._update_camera()

        # Play baby crying on loop when any kid is visible on screen
        cam = int(self.cam)
        margin = 80
        kids_on_screen = any(cam - margin <= c.x <= cam + SW + margin for c in self.children)
        snd = self.sounds.get('kids_crying')
        if snd:
            if kids_on_screen and not self._kids_crying_playing:
                self._kids_cry_channel.play(snd, loops=-1)
                self._kids_crying_playing = True
            elif not kids_on_screen and self._kids_crying_playing:
                self._kids_cry_channel.stop()
                self._kids_crying_playing = False

        if self.hero.dead:
            self.state=self.S_OVER
            if self._kids_crying_playing:
                self._kids_cry_channel.stop()
                self._kids_crying_playing = False
            # Stop background music and play death sound
            pygame.mixer.music.stop()
            snd = self.sounds.get('death')
            if snd:
                snd.play()

    def draw(self):
        cam=int(self.cam)
        self.bg.draw(self.screen,cam)
        gx=-cam
        pygame.draw.rect(self.screen,(35,25,15),(gx,GROUND_Y,WORLD_W,SH-GROUND_Y))
        pygame.draw.rect(self.screen,SNOW,(gx,GROUND_Y,WORLD_W,13))
        for p in self.platforms: p.draw(self.screen,cam)
        for o in self.obstacles: o.draw(self.screen,cam)

        if self.state==self.S_INTRO:
            self.particles.update_draw(self.screen, cam)
            self._draw_intro(); pygame.display.flip(); return
        if self.state==self.S_LORE:
            self._draw_lore(); pygame.display.flip(); return

        for c in self.children: c.draw(self.screen,cam)
        for e in self.enemies:  e.draw(self.screen,cam)
        if self.boss_active and (not self.boss.dead or self.boss.death_t < 50):
            self.boss.draw(self.screen,cam)
        self.hero.draw(self.screen,cam)
        self.particles.update_draw(self.screen, cam)
        for f in self.floats: f.draw(self.screen,cam)
        self.hud.draw(self.screen,self.hero,self.score,
                      self.boss if self.boss_active else None)
        if self._encounter_lore_timer > 0:
            self._draw_encounter_lore()
        elif self._boss_monologue_timer > 0:
            self._draw_boss_monologue()
        if self.state==self.S_WIN:    self._draw_win()
        elif self.state==self.S_OVER: self._draw_over()
        pygame.display.flip()

    def _overlay(self,a=170):
        o=pygame.Surface((SW,SH),pygame.SRCALPHA)
        o.fill((0,0,0,a)); self.screen.blit(o,(0,0))

    def _draw_intro(self):
        self._overlay(175)
        t=self.bfont.render('CHRISTMAS RESCUE',True,RED)
        self.screen.blit(t,(SW//2-t.get_width()//2,115))
        s=self.font.render('Level 2  —  The Dark Forest',True,SNOW)
        self.screen.blit(s,(SW//2-s.get_width()//2,178))
        # Intro screen narration (storybook)
        for i, ln in enumerate(INTRO_NARRATION):
            col = GOLD if i == len(INTRO_NARRATION) - 1 else WHITE
            lt = self.sfont.render(ln, True, col)
            self.screen.blit(lt, (SW//2 - lt.get_width()//2, 228 + i * 28))
        ctrl=self.sfont.render('Arrows/WASD Move    SPACE/Up Jump    Z Attack',True,(200,200,200))
        self.screen.blit(ctrl,(SW//2-ctrl.get_width()//2,408))
        lore_hint=self.sfont.render('Press L for Enemy Lore',True,(180,180,200))
        self.screen.blit(lore_hint,(SW//2-lore_hint.get_width()//2,438))
        a=int(128+127*math.sin(self.itimer*0.09))
        pt=self.font.render('Press any key to begin',True,GOLD); pt.set_alpha(a)
        self.screen.blit(pt,(SW//2-pt.get_width()//2,468))

    def _draw_encounter_lore(self):
        """Story popup: hero's vow first, then enemy lore when hero faces them."""
        if not self._encounter_lore_title or not self._encounter_lore_lines: return
        self._overlay(180)
        title, col = self._encounter_lore_title
        title_font = pygame.font.SysFont('Arial', 22, bold=True)
        lore_font = pygame.font.SysFont('Arial', 16)
        y = 88
        # Hero speaks first: "I will save the children..."
        hero_font = pygame.font.SysFont('Arial', 18, bold=True)
        hero_txt = hero_font.render(HERO_VOW, True, GOLD)
        self.screen.blit(hero_txt, (SW//2 - hero_txt.get_width()//2, y))
        y += 42
        # Then enemy: "We are the Green Gnomes." + lore
        self.screen.blit(title_font.render(title, True, col), (SW//2 - title_font.size(title)[0]//2, y))
        y += 38
        for line in self._encounter_lore_lines:
            t = lore_font.render(line, True, (230, 230, 245))
            self.screen.blit(t, (SW//2 - t.get_width()//2, y))
            y += 22
        self.screen.blit(lore_font.render("...", True, (180, 180, 200)), (SW//2 - 8, y + 8))

    def _draw_boss_monologue(self):
        self._overlay(200)
        lines = BOSS_MONOLOGUE
        y0 = SH//2 - (len(lines) * 22) // 2
        for i, ln in enumerate(lines):
            t = self.font.render(ln, True, (255, 200, 200))
            self.screen.blit(t, (SW//2 - t.get_width()//2, y0 + i * 28))

    def _draw_lore(self):
        """Enemy Lore screen — Green Gnomes, Red Gnomes, Evil Biscuit, Dark Santa."""
        self._overlay(200)
        lore_font = pygame.font.SysFont('Arial', 15)
        max_w = SW - 120
        sections = [
            ("GREEN GNOMES", LORE_GREEN_GNOMES, (100, 220, 120)),
            ("RED GNOMES", LORE_RED_GNOMES, (220, 100, 100)),
            ("EVIL BISCUIT", LORE_EVIL_BISCUIT, (200, 150, 80)),
            ("DARK SANTA", LORE_DARK_SANTA, (180, 50, 50)),
        ]
        y = 72
        title_font = pygame.font.SysFont('Arial', 18, bold=True)
        self.screen.blit(title_font.render("— Enemy Lore —", True, GOLD), (SW//2 - 70, 28))
        self.screen.blit(lore_font.render("The darkness that awaits...", True, (200, 200, 220)), (SW//2 - 95, 52))
        for title, paragraph, col in sections:
            self.screen.blit(title_font.render(title, True, col), (80, y))
            y += 26
            for line in _wrap_text(lore_font, paragraph, max_w):
                self.screen.blit(lore_font.render(line, True, (220, 220, 240)), (80, y))
                y += 20
            y += 14
        self.screen.blit(lore_font.render("Press any key to return", True, (180, 180, 200)), (SW//2 - 95, SH - 36))

    def _draw_win(self):
        self._overlay(155)
        for _ in range(8):
            pygame.draw.circle(self.screen,GOLD,
                (random.randint(0,SW),random.randint(0,SH)),random.randint(2,6))
        items=[
            ('CHILDREN SAVED!',GOLD,165,self.bfont),
            ('Level 2 Complete!',WHITE,228,self.font),
        ]
        for txt,col,y,fnt in items:
            t=fnt.render(txt,True,col)
            self.screen.blit(t,(SW//2-t.get_width()//2,y))
        for i, ln in enumerate(VICTORY_SPEECH):
            t = self.sfont.render(ln, True, (220, 220, 255))
            self.screen.blit(t, (SW//2 - t.get_width()//2, 278 + i * 24))
        items2=[
            (f'Final Score: {self.score}',CYAN,368,self.font),
            ('Press R to restart  |  ESC to quit',(200,200,200),418,self.sfont),
        ]
        for txt,col,y,fnt in items2:
            t=fnt.render(txt,True,col)
            self.screen.blit(t,(SW//2-t.get_width()//2,y))

    def _draw_over(self):
        self._overlay(185)
        items=[
            ('GAME OVER',RED,185,self.bfont),
            (GAME_OVER_LINE1,(180,180,200),255,self.sfont),
            (GAME_OVER_LINE2,(160,160,200),285,self.sfont),
            (f'Score: {self.score}',WHITE,330,self.font),
            ('Press R to retry  |  ESC to quit',(200,200,200),378,self.sfont),
        ]
        for txt,col,y,fnt in items:
            t=fnt.render(txt,True,col)
            self.screen.blit(t,(SW//2-t.get_width()//2,y))

    def run(self):
        while True:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type==pygame.QUIT: pygame.quit(); sys.exit()
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                    if event.key==pygame.K_r and self.state in(self.S_WIN,self.S_OVER):
                        self._new_game()
                    if self.state==self.S_LORE:
                        self.state=self.S_INTRO
            self.update(); self.draw()


if __name__=='__main__':
    Game().run()
