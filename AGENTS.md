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
