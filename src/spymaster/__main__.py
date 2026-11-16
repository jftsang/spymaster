import argparse
import asyncio

from spymaster import Spymaster
from spymaster.players.benchmarks import BENCHMARK_FACTORIES
from spymaster.players.computer_players import FACTORIES
from spymaster.tournament import TOURNAMENT_RESULTS_PATH


def build_parser() -> argparse.ArgumentParser:
    player_names = list(FACTORIES.keys())

    def add_common(p, *, iterations, population=32, n_replace=8, test_games_help):
        p.add_argument("--iterations", type=int, default=iterations)
        p.add_argument("--population", type=int, default=population)
        p.add_argument("--n-replace", type=int, default=n_replace)
        p.add_argument("--mutation-rate", type=float, default=0.1)
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--test-games", type=int, default=100, help=test_games_help)

    parser = argparse.ArgumentParser(prog="spymaster")
    subparsers = parser.add_subparsers(dest="command", required=True)

    play = subparsers.add_parser("play", help="Play a game.")
    play.add_argument("p1", choices=player_names)
    play.add_argument("p2", choices=player_names, nargs="?")
    play.set_defaults(func=play_command)

    train = subparsers.add_parser(
        "train",
        help="Train LinearPlayer players against a computer player.",
    )
    train.add_argument(
        "--opponent",
        choices=player_names,
        nargs="+",
        default=["AI (Benchmark, Hard)"],
        help="Computer player(s) to train against (default: AI (Benchmark, Hard)).",
    )
    add_common(
        train,
        iterations=200,
        test_games_help="Games to play against each default computer player.",
    )
    train.add_argument(
        "--output",
        default="slp_weights.npy",
        help="Where to save the best weights.",
    )
    train.set_defaults(func=train_command)

    benchmark = subparsers.add_parser(
        "benchmark",
        help="Report AI players' performance against benchmarks.",
    )
    benchmark.add_argument(
        "candidate", help="Player to benchmark", choices=player_names
    )
    benchmark.add_argument("--games", type=int, default=100)
    benchmark.add_argument("--seed", type=int, default=0)
    benchmark.set_defaults(func=benchmark_command)

    tournament = subparsers.add_parser(
        "tournament",
        help="Run a round-robin tournament between all computer players.",
    )
    tournament.add_argument("--games", type=int, default=100)
    tournament.add_argument("--seed", type=int, default=0)
    tournament.add_argument(
        "--output",
        default=str(TOURNAMENT_RESULTS_PATH),
        help="Where to save the results.",
    )
    tournament.set_defaults(func=tournament_command)

    tune = subparsers.add_parser(
        "tune",
        help="Evolve TunedAdaptivePlayer's parameters against the benchmark players.",
    )
    tune.add_argument("--n-games", type=int, default=20)
    add_common(
        tune,
        iterations=100,
        test_games_help="Games to play against each benchmark player.",
    )
    tune.add_argument(
        "--output",
        default=None,
        help="Where to save the tuned parameters.",
    )
    tune.set_defaults(func=tune_command)

    return parser


async def play_command(args: argparse.Namespace) -> None:
    from spymaster.players.human_player import HumanPlayer

    if args.p2 is None:
        p1 = HumanPlayer(name="You")
        p2 = FACTORIES[args.p1]()
    else:
        p1 = FACTORIES[args.p1]()
        p2 = FACTORIES[args.p2]()

    game = Spymaster(white=p1, black=p2)
    await game.play()
    print(game.history.to_table())


async def benchmark_command(args: argparse.Namespace) -> None:
    import numpy as np

    from spymaster.gene_pool import evaluate_against_computer_players

    if args.seed is not None:
        np.random.seed(args.seed)

    factory = FACTORIES[args.candidate]
    results = await evaluate_against_computer_players(
        factory,
        n_games=args.games,
        opponent_names=list(BENCHMARK_FACTORIES.keys()),
    )
    print(
        f"\n{args.candidate} vs benchmark computer players "
        f"({args.games} games each):"
    )
    for opponent, (wins, draws, losses) in results.items():
        points = wins - losses
        print(f"  vs. {opponent}: {wins}W {draws}D {losses}L (net {points:+d})")


async def tournament_command(args: argparse.Namespace) -> None:
    from spymaster.tournament import run_round_robin

    await run_round_robin(
        n_games=args.games,
        seed=args.seed,
        output=args.output,
    )
    print(f"Saved tournament results to {args.output}")


async def tune_command(args: argparse.Namespace) -> None:
    from spymaster.players.adaptive import run_tuning

    kwargs = {}
    if args.output:
        kwargs["output"] = args.output
    await run_tuning(
        n_players=args.population,
        n_iterations=args.iterations,
        n_games=args.n_games,
        n_replace=args.n_replace,
        mutation_rate=args.mutation_rate,
        seed=args.seed,
        test_games=args.test_games,
        **kwargs,
    )


async def train_command(args: argparse.Namespace) -> None:
    from spymaster.players.linear import run_gene_pool

    await run_gene_pool(
        opponent_names=args.opponent,
        n_players=args.population,
        n_iterations=args.iterations,
        n_replace=args.n_replace,
        mutation_rate=args.mutation_rate,
        seed=args.seed,
        test_games=args.test_games,
        output=args.output,
    )


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
