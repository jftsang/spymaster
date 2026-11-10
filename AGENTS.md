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

There will be no database on the backend. Any persistence between user
sessions, user statistics and game history, etc. must be done via the
frontend.

## Creating a new AI player

All new players need to implement the abstract class
`spymaster.players.Player`. In particular, it must implement the `.pick`
method, which decides on a card to play given the current state of the
game, which is entirely captured in the `Spymaster` class. The engine
always presents the game to the player as though they are sitting in the
White seat (the game is symmetric in both players).
