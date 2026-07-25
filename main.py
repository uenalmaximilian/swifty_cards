import sys
import settings
import pygame
import game
import asyncio

async def main():
    if "--debug" in sys.argv:
        settings.DEBUG_MODE = 1

    pygame.init()
    g = game.Game()
    await g.run()

if __name__ == "__main__":
    asyncio.run(main())