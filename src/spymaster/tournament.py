import abc
import asyncio
import random
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np
from tqdm.auto import tqdm

from spymaster import Spymaster
from spymaster.players import Player

TOURNAMENT_RESULTS_PATH = Path(__file__).parent / "tournament_results.npz"
DEFAULT_GAMES_PER_PAIR = 100


class Tournament(abc.ABC):
    @abc.abstractmethod
    async def play(self, players: Sequence[Player]) -> list[float]:
        pass


class RoundRobinTournament(Tournament):
    async def play(self, players: Sequence[Player]) -> list[float]:
        """Round-robin tournament between all pairs of players. Each
        pair plays two games.
        """
        n_players = len(players)
        scores: list[float] = [0.0] * n_players

        games: dict[tuple[int, int], Spymaster] = {}
        for i, j in product(range(n_players), range(n_players)):
            if i != j:
                games[i, j] = Spymaster(white=players[i], black=players[j])

        await asyncio.gather(*(game.play() for game in games.values()))

        for (i, j), game in games.items():
            if game.white_score > game.black_score:
                scores[i] += 1
                scores[j] -= 1
            elif game.black_score > game.white_score:
                scores[i] -= 1
                scores[j] += 1
            else:
                pass
        return scores


@dataclass
class TournamentResults:
    scores: np.ndarray
    player_names: list[str]
    evaluator_names: list[str]

    def save(self, path: str | Path = TOURNAMENT_RESULTS_PATH) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            scores=self.scores,
            player_names=np.array(self.player_names),
            evaluator_names=np.array(self.evaluator_names),
        )

    @classmethod
    def load(cls, path: str | Path = TOURNAMENT_RESULTS_PATH) -> TournamentResults:
        with np.load(path) as data:
            scores = np.array(data["scores"])
            player_names = [str(name) for name in data["player_names"]]
            evaluator_names = [str(name) for name in data["evaluator_names"]]
        return cls(
            scores=scores,
            player_names=player_names,
            evaluator_names=evaluator_names,
        )


def _new_player(name: str) -> Player:
    from spymaster.players.computer_players import new_computer_player

    return new_computer_player(name)


def _net_score(a_is_white: bool, game: Spymaster) -> int:
    if a_is_white:
        a_score, b_score = game.white_score, game.black_score
    else:
        a_score, b_score = game.black_score, game.white_score
    if a_score > b_score:
        return 1
    if a_score < b_score:
        return -1
    return 0


async def play_pair(
    a_name: str,
    b_name: str,
    n_games: int = DEFAULT_GAMES_PER_PAIR,
    progress: tqdm | None = None,
) -> int:
    """Play ``n_games`` games between two named players, alternating
    colours, and return the net score for ``a_name``: +1 per win, 0 per
    draw, -1 per loss.
    """
    games: list[tuple[bool, Spymaster]] = []
    for k in range(n_games):
        a_is_white = k % 2 == 0
        white_name, black_name = (a_name, b_name) if a_is_white else (b_name, a_name)
        game = Spymaster(
            white=_new_player(white_name),
            black=_new_player(black_name),
        )
        games.append((a_is_white, game))

    tasks = [asyncio.create_task(game.play()) for _, game in games]
    try:
        for task in asyncio.as_completed(tasks):
            await task
            if progress is not None:
                progress.update(1)
    except BaseException:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    return sum(_net_score(a_is_white, game) for a_is_white, game in games)


async def run_round_robin(
    player_names: Sequence[str] | None = None,
    evaluator_names: Sequence[str] | None = None,
    n_games: int = DEFAULT_GAMES_PER_PAIR,
    seed: int | None = 0,
    progress: bool = True,
    output: str | Path | None = None,
) -> TournamentResults:
    """Run a round-robin tournament and optionally save the net score
    matrix. When the player and evaluator lists are identical, each pair
    is played once and the matrix is antisymmetric.
    """
    if player_names is None or evaluator_names is None:
        from spymaster.players.computer_players import FACTORIES

        if player_names is None:
            player_names = list(FACTORIES)
        if evaluator_names is None:
            evaluator_names = list(player_names)

    player_names = list(player_names)
    evaluator_names = list(evaluator_names)

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    scores = np.zeros((len(player_names), len(evaluator_names)), dtype=np.int16)
    same_sets = player_names == evaluator_names

    if same_sets:
        pairs = [
            (i, j)
            for i in range(len(player_names))
            for j in range(i + 1, len(player_names))
        ]
    else:
        pairs = [
            (i, j)
            for i, player in enumerate(player_names)
            for j, evaluator in enumerate(evaluator_names)
            if player != evaluator
        ]

    bar = (
        tqdm(total=len(pairs) * n_games, desc="Tournament", unit="game")
        if progress
        else None
    )
    try:
        for i, j in pairs:
            net = await play_pair(
                player_names[i],
                evaluator_names[j],
                n_games=n_games,
                progress=bar,
            )
            scores[i, j] = net
            if same_sets:
                scores[j, i] = -net
    finally:
        if bar is not None:
            bar.close()

    results = TournamentResults(
        scores=scores,
        player_names=player_names,
        evaluator_names=evaluator_names,
    )
    if output is not None:
        results.save(output)

    totals = scores.sum(axis=1)
    for name, total in zip(player_names, totals, strict=True):
        print(f"{name}: {total:+d}")

    return results
