import argparse
import asyncio

from .spymaster import Spymaster


async def main():
    from .players import HumanPlayer, players

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "p1", choices=[p for p in players.keys()],
    )
    parser.add_argument(
        "p2", choices=[p for p in players.keys()], nargs="?"
    )
    args = parser.parse_args()
    if args.p2 is None:
        p1 = HumanPlayer("You")
        p2 = players[args.p1]
    else:
        p1 = players[args.p1]
        p2 = players[args.p2]

    game = Spymaster(white=p1, black=p2)
    await game.play()
    game.print_score()


if __name__ == "__main__":
    asyncio.run(main())
