# How to play

The objective in Spymaster is to win more points than the opponent.
You play a sequence of 16 missions, which are worth 1 to 16 points, in
random order. Points are earned by winning a mission or by killing an
enemy agent.

At the start of the game, each player has 16 agents, numbered 0 to 15.
Each round, one of the missions is chosen at random, and the players
each choose one of their remaining agents, simultaneously revealed. The
player who plays the higher card scores the value of that mission. The
exception is that Agent 0 is an assassin who can kill the enemy agent,
and score the  value of that agent instead of the value of the mission.
If both  players play the same card, then the mission is a draw and
neither player wins any points.

Spymaster is a variation on the game [Goofspiel](https://en.wikipedia.org/wiki/Goofspiel)
created by [Richard Bartle](http://mud.co.uk/richard/), who introduced a
new strategic element in the form of the assassin. You can play the
original game [on Dr Bartle's website](https://www.youhaventlived.com/spymaster/).
This is a remake in Python and FastAPI allowing for multiplayer play and
for the development of additional strategies.
