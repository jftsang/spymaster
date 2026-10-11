import argparse
import asyncio
import sys

from .spymaster import Spymaster


def build_parser() -> argparse.ArgumentParser:
    from spymaster.players.computer_players import computer_players

    player_names = list(computer_players.keys())

    parser = argparse.ArgumentParser(prog="spymaster")
    subparsers = parser.add_subparsers(dest="command")

    play = subparsers.add_parser("play", help="Play a game.")
    play.add_argument("p1", choices=player_names)
    play.add_argument("p2", choices=player_names, nargs="?")

    train = subparsers.add_parser(
        "train",
        help="Train SingleLayerPerceptron players against a computer player.",
    )
    train.add_argument(
        "--opponent",
        choices=player_names,
        nargs="+",
        default=["AI (Hard)"],
        help="Computer player(s) to train against (default: AI (Hard)).",
    )
    train.add_argument("--iterations", type=int, default=200)
    train.add_argument("--population", type=int, default=32)
    train.add_argument("--n-replace", type=int, default=8)
    train.add_argument("--mutation-rate", type=float, default=0.1)
    train.add_argument("--seed", type=int, default=0)
    train.add_argument(
        "--test-games",
        type=int,
        default=100,
        help="Games to play against each default computer player.",
    )
    train.add_argument(
        "--output",
        default="slp_weights.npy",
        help="Where to save the best weights.",
    )

    benchmark = subparsers.add_parser(
        "benchmark",
        help="Report the trained perceptron players' performance.",
    )
    benchmark.add_argument("--games", type=int, default=100)
    benchmark.add_argument("--seed", type=int, default=0)

    tune = subparsers.add_parser(
        "tune",
        help="Evolve TunedAdaptivePlayer's parameters against the benchmark players.",
    )
    tune.add_argument("--iterations", type=int, default=100)
    tune.add_argument("--population", type=int, default=32)
    tune.add_argument("--n-games", type=int, default=20)
    tune.add_argument("--n-replace", type=int, default=8)
    tune.add_argument("--mutation-rate", type=float, default=0.1)
    tune.add_argument("--seed", type=int, default=0)
    tune.add_argument(
        "--test-games",
        type=int,
        default=100,
        help="Games to play against each benchmark player.",
    )
    tune.add_argument(
        "--output",
        default=None,
        help="Where to save the tuned parameters.",
    )

    return parser


async def play_command(args: argparse.Namespace) -> None:
    from spymaster.players import HumanPlayer
    from spymaster.players.computer_players import computer_players as players

    if args.p2 is None:
        p1 = HumanPlayer(name="You")
        p2 = players[args.p1]
    else:
        p1 = players[args.p1]
        p2 = players[args.p2]

    game = Spymaster(white=p1, black=p2)
    await game.play()
    game.print_score()


async def benchmark_command(args: argparse.Namespace) -> None:
    from spymaster.gene_pool import (
        evaluate_against_computer_players,
        head_to_head,
    )
    from spymaster.players.benchmarks import default_computer_player_names
    from spymaster.players.computer_players import (
        LINEAR_PLAYER_SPECS,
        load_perceptron,
    )

    import numpy as np

    if args.seed is not None:
        np.random.seed(args.seed)

    players = {
        name: load_perceptron(name, path)
        for name, path in LINEAR_PLAYER_SPECS
        if path.exists()
    }

    for name, player in players.items():
        results = await evaluate_against_computer_players(
            player,
            n_games=args.games,
            opponent_names=default_computer_player_names,
        )
        print(f"\n{name} vs default computer players ({args.games} games each):")
        for opponent, (wins, draws, losses) in results.items():
            points = wins + 0.5 * draws
            print(
                f"  {opponent}: {wins}W {draws}D {losses}L "
                f"({points / args.games:.1%})"
            )

    names = list(players)
    if len(names) >= 2:
        a_name, b_name = names[0], names[1]
        a_wins, draws, b_wins = await head_to_head(
            players[a_name], players[b_name], n_games=args.games
        )
        total = 2 * args.games
        print(f"\nHead to head ({total} games):")
        print(f"  {a_name}: {a_wins}W {draws}D {b_wins}L")
        print(f"  {b_name}: {b_wins}W {draws}D {a_wins}L")


def main() -> None:
    parser = build_parser()

    argv = sys.argv[1:]
    if not argv or argv[0] not in {"play", "train", "benchmark", "tune", "-h", "--help"}:
        argv = ["play"] + argv

    args = parser.parse_args(argv)

    if args.command == "benchmark":
        asyncio.run(benchmark_command(args))
    elif args.command == "tune":
        from spymaster.gene_pool import run_tuning

        kwargs = {
            "n_players": args.population,
            "n_iterations": args.iterations,
            "n_games": args.n_games,
            "n_replace": args.n_replace,
            "mutation_rate": args.mutation_rate,
            "seed": args.seed,
            "test_games": args.test_games,
        }
        if args.output:
            kwargs["output"] = args.output
        asyncio.run(run_tuning(**kwargs))
    elif args.command == "train":
        from spymaster.gene_pool import run_gene_pool

        asyncio.run(
            run_gene_pool(
                opponent_names=args.opponent,
                n_players=args.population,
                n_iterations=args.iterations,
                n_replace=args.n_replace,
                mutation_rate=args.mutation_rate,
                seed=args.seed,
                test_games=args.test_games,
                output=args.output,
            )
        )
    else:
        asyncio.run(play_command(args))


if __name__ == "__main__":
    main()
