import pygame
import sys
import os
import math

# Updated Dimensions to match your request
SW, SH = 1300, 650 
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

class StoryPage:
    def __init__(self, image_path, text):
        # Normalizes path for Windows/Mac
        self.image_path = image_path.replace("/", os.sep) 
        self.text = text
        self.image = None
        
    def load(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Look in root assets folder (one level up from Level_1)
        root_search = os.path.abspath(os.path.join(script_dir, "..", self.image_path))
        local_search = os.path.abspath(os.path.join(script_dir, self.image_path))
        cwd_search = os.path.abspath(self.image_path)

        target_path = None
        for path in [root_search, local_search, cwd_search]:
            if os.path.exists(path):
                target_path = path
                break

        if target_path:
            try:
                self.image = pygame.image.load(target_path).convert()
                self.image = pygame.transform.scale(self.image, (SW, SH))
            except Exception as e:
                print(f"Error loading {target_path}: {e}")
                self._create_fallback()
        else:
            self._create_fallback()

    def _create_fallback(self):
        self.image = pygame.Surface((SW, SH))
        self.image.fill((30, 20, 40))

class NarrativeManager:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        # Ensure font is initialized
        if not pygame.font.get_init():
            pygame.font.init()
        self.font = pygame.font.SysFont('Georgia', 32, italic=True)
        self.hint_font = pygame.font.SysFont('Arial', 18, bold=True)
        
        self.pages = [
            StoryPage("assets/story1.png", "Beneath the shimmering lights of the solstice, Santa Claus appears not as a saint, but as a predator, offering enchanted gifts to lure children into his reach."),
            StoryPage("assets/story2.jpg", "As the children reach for their presents, the \"gifts\" transform into shadow-shackles, dragging them away into the frozen depths of the Dark Forest."),
            StoryPage("assets/story3.png", "A lone wanderer, bound by a code of honor, hears the distant cries of the innocent and resolves to infiltrate the forest alone to bring them home.")
        ]
        self.current_page_idx = 0
        self.display_time = 50000 

    def render_text(self, text, pos):
        words = text.split(' ')
        x, y = pos
        max_w = SW - 100
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
        for page in self.pages: 
            page.load()
            
        start_ticks = pygame.time.get_ticks()
        
        # Loop until all pages are shown
        while self.current_page_idx < len(self.pages):
            self.clock.tick(FPS)
            elapsed = pygame.time.get_ticks() - start_ticks
            
            # 1. Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT: 
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    self.current_page_idx += 1
                    start_ticks = pygame.time.get_ticks()
            
            # 2. Timer Handling
            if elapsed > self.display_time:
                self.current_page_idx += 1
                start_ticks = pygame.time.get_ticks()

            # 3. Drawing (only if index is valid)
            if self.current_page_idx < len(self.pages):
                self.screen.fill(BLACK)
                self.screen.blit(self.pages[self.current_page_idx].image, (0, 0))
                
                # Dark overlay for text
                overlay = pygame.Surface((SW, 220), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180)) 
                self.screen.blit(overlay, (0, SH - 220))
                
                self.render_text(self.pages[self.current_page_idx].text, (60, SH - 160))

                # Pulsing hint
                pulse = (math.sin(pygame.time.get_ticks() * 0.005) + 1) / 2
                hint_col = (int(200*pulse+55), int(200*pulse+55), int(200*pulse+55))
                hint_surf = self.hint_font.render("PRESS ANY KEY TO CONTINUE", True, hint_col)
                self.screen.blit(hint_surf, (SW // 2 - hint_surf.get_width() // 2, SH - 40))
                
                pygame.display.flip()
        
        return True # Exit to Level 1