# How to play

The objective in Spymaster is to win more points than the opponent.
You play a sequence of 16 missions, worth 1 to 16 points, in random
order. Points are earned by winning a mission or by killing an enemy
agent.

At the start of the game, each player has 16 agents (cards), numbered 0
to 15. Each round, one of the remaining missions is chosen at random,
and both players choose one of their remaining agents; the choices are
then revealed simultaneously.

The player who plays the higher card scores the value of that mission.
Agent 0 is an assassin: it kills the enemy agent and scores the value of
that agent instead of the value of the mission. If both players play the
same card, the mission is a draw and neither player scores any points
for that round.

Spymaster was created by [Richard Bartle][bartle] as a variation on the
game [Goofspiel][goofspiel]. It introduces a new strategic element in
the form of the assassin. You can play the original game [on Dr Bartle's
website][upstream]. This website is a remake with support for
multiplayer, a mobile-responsive UI, and a number of new AI players.
Assets and flavour text are offered by kind permission of Dr Bartle.

[bartle]: http://mud.co.uk/richard/
[goofspiel]: https://en.wikipedia.org/wiki/Goofspiel
[upstream]: https://www.youhaventlived.com/spymaster/


## About the AI players

The **Benchmark** players ([src][benchmark-src]) are the five that
appear on the original Spymaster website, at different levels of
difficulty.

[benchmark-src]: https://github.com/jftsang/spymaster/blob/main/src/spymaster/players/benchmarks.py

The **Nash, 1-ply** player ([src][nash-src]) plays the Nash equilibrium
in the endgame and otherwise uses a 1-ply minimax search with an
evaluation function. It does very well against most other AIs, except
for...

[nash-src]: https://github.com/jftsang/spymaster/blob/main/src/spymaster/players/minimax/nash_players.py

...the **Adaptive** players ([src][adaptive-src]), which are variants of
the benchmark "Russia" player. Their different personalities control how
they use the assassin card and whether they will duck (deliberately play
a low card to avoid contesting a mission).

[adaptive-src]: https://github.com/jftsang/spymaster/blob/main/src/spymaster/players/adaptive.py

The **Linear Layer** players ([src][linear-src]) construct a strategy by
encoding the current position as a vector and applying linear transforms
whose weights are chosen by a genetic algorithm. They were a bit of an
experiment; they were trained to perform well against the benchmarks but
ended up being cripplingly overspecialised.

[linear-src]: https://github.com/jftsang/spymaster/blob/main/src/spymaster/players/linear.py
