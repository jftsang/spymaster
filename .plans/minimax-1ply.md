# Nash 1-ply AI player

Build a family of Spymaster AI players that play a Nash-equilibrium
mixed strategy. This first version is a 1-ply minimax search, exposed as
`AI (Nash, 1-ply)`.

## Goal

Maximise expected game equity from the player's point of view:

- `+1` for a win
- `0` for a draw
- `-1` for a loss

Modelling the opponent as adversarial, solve the simultaneous-move game
at each decision as a zero-sum matrix game.

## Decisions

- Implement only the 1-ply player now; leave room for a 2-ply version
  later.
- Player name: `AI (Nash, 1-ply)`.
- Use scipy for linear programming: add `scipy>=1.16.1` (the first
  stable release with Python 3.14 wheels) and solve with
  `scipy.optimize.milp` using `LinearConstraint` and `Bounds`.
- Sample from the root equilibrium mixture. Never deterministically
  play the highest-probability action.
- Use exact dynamic programming for small endgames. Default
  `EXACT_ROUNDS = 3`, meaning a position with at most four cards per
  hand is solved exactly, because leaves at `k - 1 <= 3` are exact.
- Memoise exact DP on the score difference, not the separate White and
  Black scores, since only the remaining margin affects the outcome.
- Keep the guaranteed-winner analysis standalone and independent of the
  Nash search, so other AI players can reuse it.
- Short-circuit forced wins, forced losses, and available draws without
  solving an LP. Re-run the analysis every round so an opponent blunder
  is exploited immediately.
- Treat draws explicitly:
  - `DRAW_ONLY`: winning is impossible (`diff + total == 0`); pursue a
    draw when it can be secured.
  - `DEFENSIVE_DRAW`: a win is possible but cannot be secured, while a
    draw can be; this is a caller decision and defaults to going for the
    win (`defensive=False`).
- Make the leaf evaluation pluggable through an `Evaluator` class with
  `evaluate(situation: Spymaster) -> float`. Extra configuration belongs
  in the constructor, and subclasses should not require call-site
  changes.
- Ship a crude evaluator as the default placeholder, then improve it
  independently of the Nash machinery.
- Do not change the game engine. Registration happens in the existing
  computer-player factory.

## Rules used for analysis

Each player starts with cards `0..15`; card `0` is the assassin. Missions
are `1..16`. The mission is chosen uniformly before both players pick,
and picks are simultaneous. Both hands, all remaining missions, scores,
and history are visible; positions are presented as though the player is
White.

Scoring mirrors `Spymaster.resolve`:

- Equal cards: nobody scores.
- White plays the assassin: White scores Black's card value.
- Black plays the assassin: Black scores White's card value.
- Otherwise the higher card scores the mission value.

Let:

- `diff = white_score - black_score`
- `total` be the sum of all remaining mission values
- `P_k` be the sum of the `k` largest remaining missions
- `G` be the number of guaranteed winners in our hand, i.e. cards
  strictly greater than the opponent's highest card

Thresholds:

- Smallest winning mission count: smallest `k` with
  `2 * P_k > total - diff`.
- Smallest drawing mission count: smallest `k` with
  `2 * P_k >= total - diff`.
- A threshold is securable when its `k <= G`.
- Loss is certain when `diff + total < 0`.
- If either hand contains the assassin, the guarantee analysis returns
  `NONE`.

## Guarantee cases

| Case             | Condition                                      | Value                                      | Policy                                                          |
|------------------|------------------------------------------------|--------------------------------------------|-----------------------------------------------------------------|
| `WIN`            | winning threshold exists and is securable      | `+1`                                       | Play a guaranteed winner on a required mission; hold otherwise. |
| `DRAW_ONLY`      | `diff + total == 0`                            | `0` if draw is securable, otherwise `None` | Always pursue draw policy.                                      |
| `DEFENSIVE_DRAW` | win possible but not securable, draw securable | `None` (guaranteed at least `0`)           | Follow draw policy only when `defensive=True`.                  |
| `LOSS`           | `diff + total < 0`                             | `-1`                                       | No LP; any play.                                                |
| `NONE`           | otherwise, or either assassin is held          | `None`                                     | Continue to Nash search.                                        |

## Modules

### `spymaster.position`

- Core module; it must not depend on the minimax or `spymaster_ai`
  packages.
- `Position`: frozen dataclass with `ours`, `theirs`, `missions`,
  `current_mission`, `white_score`, and `black_score`.
- `Position.of(game_state) -> Position`.
- `Position.to_spymaster() -> Spymaster`, used for evaluator leaves.
- `Spymaster.position` is a property returning `Position.of(self)`.
- Players are presented with `Spymaster` game states, not `Position`
  objects. A player may adapt its decisions based on the game history
  or the identity of the other player, so those fields must remain
  available at the player API boundary. `Position` is for search and
  memoization only.

### `spymaster.players.minimax.evaluation`

- `Evaluator`: abstract base with `evaluate(situation) -> float`.
- `CrudeEvaluator`: deterministic default heuristic returning an
  approximate equity in `[-1, 1]`.

### `spymaster.players.minimax.guarantee`

- `GuaranteeKind`: `WIN`, `DRAW_ONLY`, `DEFENSIVE_DRAW`, `LOSS`, `NONE`.
- `Guarantee`: result object carrying kind, equity, thresholds, and the
  cards/missions needed to execute the policy.
- `analyse_guarantee(position)`: computes the case table above from a
  `Position`.

### `spymaster.players.minimax.exact`

- `EXACT_ROUNDS = 3`.
- `exact_equity(position)`: exact value of an endgame position.
- Cache on `(ours, theirs, missions, current_mission, diff)`.
- Chance nodes average over a uniformly drawn next mission.
- Guaranteed `WIN`, `LOSS`, and securable `DRAW_ONLY` positions are
  short-circuited before recursion.

### `spymaster.players.minimax.moves`

- `child_position(position, ours, theirs)`: resolve the current mission
  and return the successor `Position`.
- `resolve_score(ours, theirs, mission)`: mirror the engine's scoring.

### `spymaster.players.minimax.matrix_game`

- `solve_matrix_game(A) -> (row_strategy, value)` using `milp`:
  minimise `-v` subject to `A^T x >= v`, `sum(x) == 1`, `x >= 0`, with
  `v` free.
- Add pure-Python shortcuts for `1x1`, `m x 1`, and `1 x n` games.
- Normalise near-zero probabilities and sample according to the result.

### `spymaster.players.minimax.nash_players`

- `NashPlayer`, registered as `AI (Nash, 1-ply)`.
- Constructor: `NashPlayer(name, evaluator=None, exact_rounds=3,
  use_guarantees=True)`; the evaluator defaults to `CrudeEvaluator()`.
- Root move evaluation:
  1. Short-circuit pinned guarantees without solving an LP.
  2. Build the payoff matrix over our cards versus the opponent's cards
     for the current mission.
  3. For each pair, resolve the mission and evaluate the successor in
     this order: pinned guarantee, exact DP when within `exact_rounds`,
     otherwise the evaluator.
  4. Solve the matrix game and sample our root action from the
     equilibrium mixture.
- `use_guarantees=False` and `exact_rounds=0` are test controls for
  isolating the matrix/evaluator behavior.

## Exact endgame

Use the core `spymaster.position.Position` dataclass:

- Constructible from a `Spymaster` through the static factory method
  `Position.of(game_state) -> Position`, or through the
  `Spymaster.position` property.
- Convertible back to an evaluator leaf state with `to_spymaster()`.
- `ours: frozenset[AgentCard]`
- `theirs: frozenset[AgentCard]`
- `missions: frozenset[MissionCard]`
- `current_mission: MissionCard | None`
- `white_score: int`
- `black_score: int`

The current mission is included in `missions` at the root and is also
identified by `current_mission`. Memoise on
`(ours, theirs, missions, current_mission, diff)`, since a constant score
offset does not change future decisions and only the score difference
matters.

`exact_equity(position)`:

- If no missions remain, return `+1`, `0`, or `-1` from the sign of
  `diff`.
- If `current_mission` is None but missions remain, average over each
  possible next mission, which is drawn uniformly.
- Otherwise short-circuit a pinned guarantee and solve the current
  mission's matrix game recursively.

Leaf evaluation order:

1. Use the guarantee equity when it is pinned.
2. Use exact DP when the remaining state is small enough.
3. Otherwise call `evaluator.evaluate(position.to_spymaster())`.

When deriving an evaluator leaf position, use
`current_mission=None`, put every unresolved mission in
`remaining_missions`, and leave history empty. This is at most about
256 evaluator calls per pick in the 1-ply version.

Optional clipping:

- `DRAW_ONLY`: `min(estimate, 0.0)`
- `DEFENSIVE_DRAW`: `max(estimate, 0.0)`

## Future: 2-ply at eight cards

Do not implement yet. After the exact endgame and evaluator work, add a
2-ply variant for positions where each hand has eight cards (and eight
missions remain).

- A ply is one mission round: both players pick simultaneously, then the
  next mission is drawn uniformly from the remaining missions.
- Root payoff entries are the expected equilibrium value of the next
  mission over all possible next missions, not direct evaluator calls.
- Reuse `NashPlayer` with a `depth` argument: `depth=1` preserves current
  behavior, while `depth=2` adds one more round plus a chance node.
- Register separately as `AI (Nash, 2-ply)`; do not replace the 1-ply
  player.
- The worst case at eight cards per hand is about
  `8^2 * 7 * 7^2 = 21,952` evaluator calls per pick. Use caching and do
  not run this search outside the eight-card threshold.
- Exact DP remains preferable when the remaining position is small
  enough. Compare 2-ply against exact endgame and the 1-ply player
  before adopting it.

## Tests

- `tests/test_position.py`: property construction, state changes, and
  hashability.
- `tests/test_evaluation.py`: evaluator ordering and bounds.
- `tests/test_exact.py`: terminal values, exact mission resolution,
  next-mission chance nodes, guarantee pruning, and diff-keyed caching.
- `tests/test_guarantee.py`: threshold arithmetic, assassin disabling,
  and draw cases.
- `tests/test_matrix_game.py`: known matrix games, pure strategies,
  probabilities summing to one, value bounds.
- `tests/test_nash_players.py`: legal picks, child resolution, sampling
  from mixtures, and deterministic seeded matches.

## Verification

Run before committing:

```sh
ruff check --fix --output-format=concise
ty check --output-format=concise
uv run -m unittest
```
