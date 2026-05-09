import pygame
import sys
import os
import math

# Dimensions matching your game
SW, SH = 1300, 650 
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

class StoryPage:
    def __init__(self, image_path, text):
        self.image_path = image_path.replace("/", os.sep) 
        self.text = text
        self.image = None
        
    def load(self):
        # Look relative to narrative2.py's location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Search Paths: 
        # 1. Directly inside Level_2/assets/
        # 2. Inside assets/ at the root
        paths_to_check = [
            os.path.abspath(os.path.join(script_dir, "assets", os.path.basename(self.image_path))),
            os.path.abspath(os.path.join(script_dir, "..", self.image_path)),
            os.path.abspath(self.image_path)
        ]

        target_path = None
        for path in paths_to_check:
            if os.path.exists(path):
                target_path = path
                break

        if target_path:
            try:
                self.image = pygame.image.load(target_path).convert()
                self.image = pygame.transform.scale(self.image, (SW, SH))
            except:
                self._create_fallback()
        else:
            self._create_fallback()

    def _create_fallback(self):
        self.image = pygame.Surface((SW, SH))
        self.image.fill((40, 10, 10)) # Dark red fallback for danger

class NarrativeManager2:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Georgia', 32, italic=True)
        self.hint_font = pygame.font.SysFont('Arial', 18, bold=True)
        
        # Your Level 2 Story Content
        self.pages = [
            StoryPage("Level_2/assets/story4.png", 
                      "Upon entering the forest, a malevolent curse from Dark Santa shatters the Warrior's long-range weaponry, forcing him to rely solely on his fists and raw strength to survive.")
        ]
        self.current_page_idx = 0
        self.display_time = 60000 # Slightly longer to read the text

    def render_text(self, text, pos):
        words = text.split(' ')
        x, y = pos
        max_w = SW - 120
        for word in words:
            surf = self.font.render(word, True, WHITE)
            if x + surf.get_width() > max_w:
                x = pos[0]
                y += surf.get_height() + 10
            shadow = self.font.render(word, True, (20, 20, 20))
            self.screen.blit(shadow, (x+2, y+2))
            self.screen.blit(surf, (x, y))
            x += surf.get_width() + self.font.size(' ')[0]

    def run(self):
        for page in self.pages: page.load()
        start_ticks = pygame.time.get_ticks()
        
        while self.current_page_idx < len(self.pages):
            self.clock.tick(FPS)
            elapsed = pygame.time.get_ticks() - start_ticks
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    self.current_page_idx += 1
                    start_ticks = pygame.time.get_ticks()
            
            if elapsed > self.display_time:
                self.current_page_idx += 1
                start_ticks = pygame.time.get_ticks()

            if self.current_page_idx < len(self.pages):
                self.screen.fill(BLACK)
                self.screen.blit(self.pages[self.current_page_idx].image, (0, 0))
                overlay = pygame.Surface((SW, 220), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 190)) 
                self.screen.blit(overlay, (0, SH - 220))
                self.render_text(self.pages[self.current_page_idx].text, (80, SH - 160))
                
                pulse = (math.sin(pygame.time.get_ticks() * 0.005) + 1) / 2
                hint_col = (int(200*pulse+55), int(100*pulse), int(100*pulse)) # Pulsing Red
                hint_surf = self.hint_font.render("THE CURSE TAKES HOLD - PRESS ANY KEY", True, hint_col)
                self.screen.blit(hint_surf, (SW // 2 - hint_surf.get_width() // 2, SH - 40))
                
                pygame.display.flip()