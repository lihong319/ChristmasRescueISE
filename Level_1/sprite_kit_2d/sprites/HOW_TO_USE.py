"""
SPRITE KIT - Python Game Helper
================================
All sprites are extracted with transparent backgrounds (RGBA PNG).

FOLDER STRUCTURE:
  sprites/
    background/           - winter_village_background.png
    blue_gnome/           - idle, walk, run, jump, attack, damage, faint, crouch, pull, climb
    red_gnome/            - idle, walk, run, jump, attack, damage, swim, crouch
    ice_monster/          - idle, walk, run, jump, attack, damage, faint, crouch, pull
    turban_gnome/         - idle, walk, run, jump, attack, damage, faint, swim, crouch, pull, climb
    dark_stag_brown/      - walk, run, attack, charge
    dark_stag_brown_alt/  - walk, run, attack, charge
    dark_stag_dark/       - walk, run, attack, charge
    dark_stag_gray/       - walk, run, attack, charge
    dark_stag_red/        - walk, run, attack, charge
    dark_stag_red_alt/    - walk, run, attack, charge
    evil_santa/           - attack_row1, attack_row2, attack_row3, attack_row4
    
    Each folder also has a sheets/ subfolder with pre-made spritesheets.

EXAMPLE USAGE WITH PYGAME:
"""

import pygame
import os

def load_animation(sprite_folder, anim_name, scale=None):
    """Load all frames of an animation and return as list of surfaces."""
    folder = os.path.join(sprite_folder, anim_name)
    frames = []
    if not os.path.exists(folder):
        return frames
    for fname in sorted(os.listdir(folder)):
        if fname.endswith('.png'):
            surf = pygame.image.load(os.path.join(folder, fname)).convert_alpha()
            if scale:
                surf = pygame.transform.scale(surf, scale)
            frames.append(surf)
    return frames

def load_spritesheet(sprite_folder, anim_name):
    """Load a pre-built spritesheet PNG."""
    path = os.path.join(sprite_folder, 'sheets', f'spritesheet_{anim_name}.png')
    if os.path.exists(path):
        return pygame.image.load(path).convert_alpha()
    return None


# ── EXAMPLE GAME LOOP ────────────────────────────────────────────────────────
class AnimatedSprite:
    def __init__(self, frames, fps=8):
        self.frames = frames
        self.fps = fps
        self.frame_index = 0
        self.timer = 0

    def update(self, dt):
        self.timer += dt
        if self.timer >= 1 / self.fps:
            self.timer = 0
            self.frame_index = (self.frame_index + 1) % len(self.frames)

    def get_frame(self):
        return self.frames[self.frame_index]


# QUICK START:
if __name__ == '__main__':
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    clock = pygame.time.Clock()

    SPRITE_DIR = os.path.dirname(__file__)  # folder where sprites are

    # Load animations
    gnome_idle   = load_animation(os.path.join(SPRITE_DIR, 'blue_gnome'), 'idle')
    gnome_walk   = load_animation(os.path.join(SPRITE_DIR, 'blue_gnome'), 'walk')
    gnome_run    = load_animation(os.path.join(SPRITE_DIR, 'blue_gnome'), 'run')
    gnome_jump   = load_animation(os.path.join(SPRITE_DIR, 'blue_gnome'), 'jump')
    gnome_attack = load_animation(os.path.join(SPRITE_DIR, 'blue_gnome'), 'attack')

    # Background
    background   = pygame.image.load(os.path.join(SPRITE_DIR, 'background', 'winter_village_background.png')).convert()

    sprite = AnimatedSprite(gnome_idle, fps=8)
    x, y = 300, 400
    state = 'idle'

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_RIGHT]:
            state = 'walk'; sprite.frames = gnome_walk; x += 3
        elif keys[pygame.K_SPACE]:
            state = 'jump'; sprite.frames = gnome_jump
        elif keys[pygame.K_z]:
            state = 'attack'; sprite.frames = gnome_attack
        else:
            if state != 'idle':
                state = 'idle'; sprite.frames = gnome_idle

        sprite.update(dt)

        screen.blit(background, (0, 0))
        frame = sprite.get_frame()
        scaled = pygame.transform.scale(frame, (100, 100))
        screen.blit(scaled, (x, y))
        pygame.display.flip()

    pygame.quit()
