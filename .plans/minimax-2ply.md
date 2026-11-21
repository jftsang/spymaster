# Plan: Adaptive 2-ply Nash analysis

## Context

- `Spymaster` starts with **16 cards per side** (`card_factory()` returns `0..15`) and **16 missions** (`mission_factory()` returns `1..16`).
- `NashAnalyser` is currently 1-ply: it resolves the current mission, then evaluates the child with `CrudeEvaluator` by default. `EXACT_ROUNDS = 3` sends small children to `exact_equity`.
- `NashPlayer` is analyser-driven: `pick()` samples from `analyser.analyse(position).strategy`.
- The webserver shares one analyser (`gs.analyser`) for both games and `/analysis`; the endpoint analyses a position and its flipped counterpart.
- The existing `tournament.play_pair()` helper already plays `n_games` between two named players, alternating colours, and returns a net score.

## Goals

1. Add `TwoPlyNashAnalyser`: same crude equity function as `NashAnalyser`, 2-ply root evaluation, and `exact_rounds=5`.
2. Add `AdaptiveNashAnalyser`: 1-ply in the early game, 2-ply in the mid-game, exact endgame solver when few rounds remain.
3. Use the adaptive analyser for webserver analysis.
4. Keep the original `"AI (Nash, 1-ply)"` player and factory. Add a new factory `"AI (Nash, 2-ply)"` whose player uses the adaptive analyser, which delegates to `TwoPlyNashAnalyser` in the mid-game.
5. Prepare, but **do not run**, a script that plays 100 matches between the 1-ply and 2-ply Nash players to check that the 2-ply player is stronger.

## Why adaptive deployment is required

Let `n` be the number of cards per hand and unresolved missions. A raw 2-ply root builds

\[
n^2 \cdot (n-1) \cdot (n-1)^2 = n^2 (n-1)^3
\]

leaf evaluations, versus `n²` for 1-ply.

| `n` | 1-ply leaves | 2-ply raw leaves |  Ratio | With `exact_rounds=5`          |
|----:|-------------:|-----------------:|-------:|--------------------------------|
|  16 |          256 |          864,000 | 3,375× | 864,000 crude leaves           |
|  15 |          225 |          617,400 | 2,744× | 617,400 crude leaves           |
|  14 |          196 |          430,612 | 2,197× | 430,612 crude leaves           |
|  13 |          169 |          292,032 | 1,728× | 292,032 crude leaves           |
|  12 |          144 |          191,664 | 1,331× | 191,664 crude leaves           |
|  11 |          121 |          121,000 | 1,000× | 121,000 crude leaves           |
|  10 |          100 |           72,900 |   729× | 72,900 crude leaves            |
|   9 |           81 |           41,472 |   512× | 41,472 crude leaves            |
|   8 |           64 |           21,952 |   343× | 21,952 crude leaves            |
|   7 |           49 |           10,584 |   216× | 10,584 exact 5-card lookups    |
|   6 |           36 |            4,500 |   125× | 36 exact solves, no second ply |

Pure 2-ply from move 1 would mean roughly **2.65 million crude leaf evaluations and ~16,650 inner LP solves per side per game**, before the doubled `/analysis` call. That is infeasible.

Chosen policy:

- `n >= 9`: 1-ply.
- `n = 8, 7`: 2-ply. This is the affordable window where looking one extra round ahead matters.
- `n <= 6`: 2-ply for the deployed analyser, with exact DP only once the child has at most three unresolved missions (`n <= 4`). The standalone `TwoPlyNashAnalyser` defaults to `exact_rounds=5`, but that cutoff made a single game exceed five minutes, so the deployed `ADAPTIVE_ANALYSER` uses the existing `EXACT_ROUNDS = 3` instead.

Using `exact_rounds=4` would force 4,500 exact-4 lookups at `n = 6`; `exact_rounds=5` forces 36 exact-5 solves there. Neither is practical for live analysis, so the deployed cutoff remains three.

## Implementation

### 1. `src/spymaster/players/minimax/nash_players.py`

- Update the module docstring to cover 1-ply, 2-ply, and adaptive analysis.
- Add imports: `dataclasses.replace`, `math.fsum`; add `TWO_PLY_EXACT_ROUNDS = 5`.
- Leave `NashAnalyser` and `NashPlayer` logic unchanged.
- Add private `_CachingEvaluator(Evaluator)` wrapper around an evaluator:
  - `evaluate(position)` caches by immutable `Position`.
  - `clear_cache()` clears it.
  - Needed because 2-ply revisits the same terminal positions via different round orderings; roughly halves leaf work at `n = 8`.
- Add `class TwoPlyNashAnalyser(NashAnalyser)`:
  - `__init__(evaluator=None, exact_rounds=TWO_PLY_EXACT_ROUNDS, use_guarantees=True)` calls `super().__init__(...)` and creates:
    - `self._cached_evaluator = _CachingEvaluator(self.evaluator)`;
    - `self._inner = NashAnalyser(evaluator=self._cached_evaluator, exact_rounds=exact_rounds, use_guarantees=use_guarantees)`.
  - Override `_value_after_round(position, ours, theirs)`:
    1. `child = child_position(position, ours, theirs)`.
    2. Return pinned guarantee equity if `use_guarantees` and `analyse_guarantee(child).equity` is not `None`.
    3. If `exact_rounds` and `len(child.missions) <= exact_rounds`, return `exact_equity(child)`.
    4. If `not child.missions`, return `self._cached_evaluator.evaluate(child)`.
    5. Otherwise, for each `mission` in `sorted(child.missions)`, form `replace(child, current_mission=mission)` and take `self._inner.analyse(next_position).value`; return `fsum(values) / len(values)`.
  - Override `clear_cache()` and `cache_size()` to include the inner analysis cache and the leaf-value cache.
- Add `class AdaptiveNashAnalyser` implementing `Analyser`:
  - `__init__(evaluator=None, two_ply_max_cards=8, one_ply=None, two_ply=None)` creates its own `NashAnalyser` and `TwoPlyNashAnalyser` when not supplied, sharing the evaluator.
  - `analyse(position)` uses `len(position.ours)` as the hand size; if it exceeds `two_ply_max_cards`, delegate to `one_ply`, otherwise delegate to `two_ply`.
  - `clear_cache()` and `cache_size()` aggregate both delegates.
- Globals:
  - Keep `NASH_ANALYSER = NashAnalyser()` and `NASH_PLAYER_NAME = "AI (Nash, 1-ply)"` and `NASH_FACTORIES` unchanged.
  - `ADAPTIVE_ANALYSER = AdaptiveNashAnalyser(two_ply_max_cards=8)`.
  - `TWO_PLY_PLAYER_NAME = "AI (Nash, 2-ply)"`.
  - `TWO_PLY_FACTORIES = {TWO_PLY_PLAYER_NAME: partial(NashPlayer, name=TWO_PLY_PLAYER_NAME, analyser=ADAPTIVE_ANALYSER)}`.
  - The new player therefore uses `TwoPlyNashAnalyser` through the adaptive wrapper, which avoids the infeasible opening-game cost.

### 2. `src/spymaster/players/computer_players.py`

- Import `TWO_PLY_FACTORIES` and merge it into `FACTORIES` after `NASH_FACTORIES`.
- Keeps `"AI (Nash, 1-ply)"` as `next(iter(FACTORIES))`, which existing webserver tests rely on.
- CLI and tournament name lists pick up the new player automatically.

### 3. `src/spymaster/webserver/__init__.py`

- Import `ADAPTIVE_ANALYSER` instead of `NASH_ANALYSER`.
- In `GameServer.__init__`, set `self.analyser: Analyser = ADAPTIVE_ANALYSER` and update the shared-cache comment.
- Leave `/analysis` and its five-key response shape unchanged, preserving the frontend contract in `state.ts`, `Game.tsx`, and `Analysis.tsx`.

### 4. Benchmark script — `src/spymaster/benchmark_nash.py` (prepare only, do not run)

Create a runnable module using the existing `tournament.play_pair()` helper:

- Imports: `argparse`, `asyncio`, `math`, `random`, `tqdm.auto.tqdm`, `play_pair`, `NASH_PLAYER_NAME`, `TWO_PLY_PLAYER_NAME`, `NASH_ANALYSER`, `ADAPTIVE_ANALYSER`.
- `async def compare(games: int, seed: int | None) -> int`:
  - Seed `random` for reproducible mission draws and `random.choices` sampling.
  - Clear both analysers' caches before the run for a clean measurement.
  - Create a `tqdm(total=games, desc="2-ply vs 1-ply", unit="game")` progress bar.
  - `return await play_pair(TWO_PLY_PLAYER_NAME, NASH_PLAYER_NAME, n_games=games, progress=bar)`.
  - Positive net means the 2-ply player won more games than it lost; colours alternate inside `play_pair`.
- `main()`:
  - `--games` default `100`, `--seed` default `0`.
  - Print net score, mean per game, and an approximate 95% interval from the bounded-outcome standard error `sqrt((1 - mean²) / games)`.
- Guard with `if __name__ == "__main__": main()`.
- Run command later: `uv run python -m spymaster.benchmark_nash`.
- Do **not** execute this script as part of the current work.

### 5. Tests

- `tests/test_nash_players.py`
  - Import `TwoPlyNashAnalyser`, `AdaptiveNashAnalyser`, `ADAPTIVE_ANALYSER`, `TWO_PLY_PLAYER_NAME`.
  - Two-ply leaf test with `exact_rounds=0` on a small position: confirm leaf evaluations happen after two resolved rounds, not one.
  - Exact-5 test: patch `exact_equity`, use `use_guarantees=False` and a position whose child has 5 missions; assert the exact solver is used for all root children and the crude evaluator is not called.
  - Cache test: `clear_cache()` / `cache_size()` cover root, inner, and leaf caches.
  - Adaptive test: with `two_ply_max_cards=8`, a 9-card position delegates to the one-ply analyser and an 8-card position delegates to the two-ply analyser (use mocks/spies on the delegates).
  - Factory test: original 1-ply factory still returns `NASH_ANALYSER`; new factory returns `ADAPTIVE_ANALYSER` whose `two_ply` is a `TwoPlyNashAnalyser`.
- `tests/test_webserver.py`
  - Update import and `test_analysis_is_cached_on_the_shared_analyser` to assert `gs.analyser is ADAPTIVE_ANALYSER` and use its cache methods.
  - Keep API shape, strategy-sum, and error-handling assertions unchanged.
- No test should invoke the benchmark script.

## Verification

Run from repo root after implementation:

```bash
uv run -m unittest
ruff check --fix --output-format=concise
ty check --output-format=concise
```

Do **not** run the benchmark script now. When asked to evaluate strength later:

```bash
uv run python -m spymaster.benchmark_nash
```

## Notes

- The global `exact_equity` cache remains module-level and is shared by both analysers.
- `TwoPlyNashAnalyser` keeps the requested five-round exact default, but the deployed `ADAPTIVE_ANALYSER` uses the existing three-round cutoff: a five-round exact solve made a single game take over five minutes, so it is impractical for webserver analysis and the round-robin suite.
- The adaptive wrapper owns its own one-ply analyser, separate from the global `NASH_ANALYSER` used by the original player, so clearing the webserver analyser's cache does not disturb the 1-ply player.
- Adding a factory increases `tests/test_round_robin.py` coverage; measure suite runtime. Shared caches should keep this manageable, but report if it becomes excessive.
