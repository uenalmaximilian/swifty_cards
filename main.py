import sys
import settings
import pygame
import game

if __name__ == "__main__":
    if "--debug" in sys.argv:
        settings.DEBUG_MODE = 1

    pygame.init()
    g = game.Game()
    g.run()