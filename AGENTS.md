# Instructions for agents

## Working in this repository

### Repo structure

Sources are in `src/frontend` for the Preact frontend, and
`src/spymaster` for the Python backend.

The backend contains the core engine, the webserver, as well as code
that defines or trains AI players. The latter will be separated out in
the future.

### Code style and quality

Check and fix before committing with

    ruff check --fix --output-format=concise
    ty check --output-format=concise

### Running tests

Run with 

    uv run -m unittest

### Frontend and responsive layout

The frontend uses Preact and Bootstrap 5.3.2 (loaded from CDN in
`src/frontend/main.html`). Prefer Bootstrap utility classes and existing
patterns over custom CSS where possible.

There are two independent sets of breakpoints; do not conflate them.

Sidebar/accessory-panel layout is driven by `SIDE_QUERY` and
`WIDE_QUERY` in `src/frontend/static/components/Game.tsx`, mirrored in
`src/frontend/static/spymaster.css`:

- `< 1200px` (Bootstrap `xl`): analysis and game log/history are
  available via toggles/modals rather than sidebars, leaving the right
  edge of the page free.
- `1200px–1599.98px` (`SIDE_QUERY`, `min-width: 1200px`): medium-wide
  screens (e.g. 13" laptops). Analysis/history render in an in-flow
  right column alongside the board.
- `>= 1600px` (`WIDE_QUERY`, `min-width: 1600px`): very wide screens.
  Analysis and history render as fixed sidebars flanking the board.

Layout *inside* the board uses the `md` breakpoint (768px), because
that is where the two agent-card columns switch between stacked and
side-by-side:

- `< 768px`: the card grids stack, so the remaining-missions list turns
  into a vertical strip on the right of the board and its label is
  hidden.
- `>= 768px`: the card grids are side-by-side, so the remaining-missions
  list is a labelled horizontal row above them.

Keep these structures intact: accessory panels stay in their
breakpoint-appropriate positions, and the missions display changes
layout only when the card grids stack.

The agent cards in each hand must always remain a 4x4 grid — never let
rows wrap. Card rows use `flex-nowrap` and the grid columns are
`col-md-4`, which leaves room for four cards per row even at 768px.

## Out-of-scope

There will be no database in the main game engine or webserver. However,
individual `Player` instances may use external resources such as
databases or files. In particular, human players who play through a web
browser may store persistent information in browser storage. 

## Creating a new AI player

All new players need to implement the abstract class
`spymaster.players.Player`. In particular, it must implement the `.pick`
method, which decides on a card to play given the current state of the
game, which is entirely captured in the `Spymaster` class. The engine
always presents the game to the player as though they are sitting in the
White seat (the game is symmetric in both players). The `Player`
implementation may also implement the `.receive` method which responds
to the result of the previous round.

The `Spymaster` class contains full information about the current game
state (current mission, remaining missions in unspecified order, 
the cards that each player holds, the current score, and the history up
until the current point. The player may use any of this information, as
well as any other resources it wants (such as memories about its
opponent or from previous games) to decide what to play.
