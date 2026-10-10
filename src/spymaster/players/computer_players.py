from random import choice, randint, random

from spymaster.players import Player
from spymaster.spymaster import MissionResult, Spymaster

from .aim import aim, chuck, mx, prefer


class RandomPlayer(Player):
    """Naive player that just plays cards at random."""

    async def pick(self, state: Spymaster) -> int:
        return choice(state.white_cards)


class SimpleAimingPlayer(Player):
    """Player that tries to aim for a few points above the value of each
    mission.
    """

    def __init__(self, name: str, variance: int = 2):
        super().__init__(name=name)
        self.variance = variance

    async def pick(self, state: Spymaster) -> int:
        current = state.current_mission if state.current_mission is not None else 1
        target = current + randint(1, self.variance)
        return aim(state.white_cards, target)


class AmericaPlayer(Player):
    """A computer player that aims just above the mission and adjusts
    its target in response to the opponent's previous overbid.
    """

    def __init__(self, name: str):
        super().__init__(name=name)
        self.diff = randint(0, 2)

    async def pick(self, state: Spymaster) -> int:
        current = state.current_mission if state.current_mission is not None else 1
        target = current + self.diff + 1
        return aim(state.white_cards, target)

    async def receive(self, state, result: MissionResult) -> None:
        if result.opp_played >= result.mission:
            self.diff = result.opp_played - result.mission


def check(probability: float) -> bool:
    return random() < probability


class RussiaPlayer(Player):
    """A computer player that adapts to different mission conditions.

    @param stabbiness: willingness to use the assassin against a
        high-value target.
    @param paranoia: fear that the opponent will play the assassin.
    @param idleness: likelihood of aiming low on a high-value mission.
    """

    def __init__(
        self,
        name: str,
        stabbiness: float = 0.5,
        paranoia: float = 0.5,
        idleness: float = 0.33,
    ):
        super().__init__(name=name)
        self.stabbiness = stabbiness
        self.paranoia = paranoia
        self.idleness = idleness
        self.diff = randint(0, 2)

    async def pick(self, state: Spymaster) -> int:
        p = state.current_mission if state.current_mission is not None else 1
        mine = state.white_cards
        theirs = state.black_cards

        def _mx(low, high):
            return mx(mine, theirs, low, high)

        def _aim(target):
            return aim(mine, target)

        if p < 5:
            # Try to win in the range if we can, otherwise discard
            return prefer(_mx(p, p + 4), chuck(mine))
        elif p < 9:
            # Try to win in the range if we can, otherwise aim just above
            return prefer(_mx(p, p + 3), _aim(randint(p + 1, p + 3)))
        elif p < 13:
            # If the assassin is available, play it with 50% chance
            return prefer(
                _mx(p, p + 2),
                0 if (0 in mine and check(self.stabbiness)) else None,
                _aim(randint(p + 1, p + 2)),
            )
        else:
            # For really high value missions, follow a similar strategy...
            # e is the card we intend to play
            e = prefer(
                _mx(13, 15),
                0 if (0 in mine and check(self.stabbiness)) else None,
                _aim(randint(p, 16)),
            )
            # ...but if we are about to play a high-value card, then...

            if e > 13 and 0 in theirs and check(self.paranoia):
                # Worried the opponent will play the assassin
                e = chuck(mine)
            elif e > 13 and check(self.idleness):
                # Conservatively save the high card for later
                e = _aim(randint(5, 7))

            return e


def new_computer_player(name: str) -> Player:
    """Create a fresh AI player instance. Fresh instances can play many
    games simultaneously without sharing mutable state."""
    factories = {
        "AI (Easiest)": lambda: RandomPlayer(name="AI (Easiest)"),
        "AI (Easy)": lambda: SimpleAimingPlayer(name="AI (Easy)", variance=2),
        "AI (Medium)": lambda: SimpleAimingPlayer(name="AI (Medium)", variance=4),
        "AI (Hard)": lambda: AmericaPlayer(name="AI (Hard)"),
        "AI (Hardest)": lambda: RussiaPlayer(
            name="AI (Hardest)", stabbiness=0.5, paranoia=0.5, idleness=0.33
        ),
    }
    try:
        return factories[name]()
    except KeyError:
        raise KeyError(f"Unknown computer player: {name}")


china = RandomPlayer(name="AI (Easiest)")
france = SimpleAimingPlayer(name="AI (Easy)", variance=2)
britain = SimpleAimingPlayer(name="AI (Medium)", variance=4)
america = AmericaPlayer(name="AI (Hard)")
russia = RussiaPlayer(name="AI (Hardest)", stabbiness=0.5, paranoia=0.5, idleness=0.33)

computer_players = {p.name: p for p in [china, france, britain, america, russia]}
