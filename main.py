"""
CHRISTMAS RESCUE - Main Launcher
Runs Level 1 first, then Level 2. Same hero throughout.
"""

import sys
import pygame

# Level 1 Imports
from Level_1.level1 import Level1Game
from Level_1.narrative import NarrativeManager

# Level 2 Imports
from Level_2.level2 import Game
from Level_2.narrative2 import NarrativeManager2

SW, SH = 1300, 650
def main():
    # 1. Start with the Narrative
    pygame.init()
    screen = pygame.display.set_mode((SW, SH))

    story = NarrativeManager(screen)
    story.run()

    # Level 1: The House at the Edge of the Forest
    
    level1 = Level1Game()
    go_to_level2 = level1.run()

    if go_to_level2:
        # Level 2: The Dark Forest
       
        transition = NarrativeManager2(screen)
        transition.run()
        Game().run()
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
