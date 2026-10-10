"""The players from the original Spymaster website."""
from random import choice, randint

from spymaster.players import Player
from spymaster.spymaster import MissionResult, Spymaster

from .aim import aim, check, chuck, mx, prefer


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

class RussiaPlayer(Player):
    """A computer player that adapts to different mission scores, and
    sometimes ducks on high-value missions.

    @param bloodthirst: willingness to use the assassin against a
        high-value target.
    @param paranoia: fear that the opponent will play the assassin.
    @param idleness: likelihood of aiming low on a high-value mission.
    """

    def __init__(
        self,
        name: str,
        bloodthirst: float = 0.5,
        paranoia: float = 0.5,
        idleness: float = 0.33,
        mission_value_thresholds: tuple[int, int, int]  = (5, 9, 13),
        high_card: int = 13,
        conservative_interval: tuple[int, int] = (5, 7),
    ):
        super().__init__(name=name)
        self.bloodthirst = bloodthirst
        self.paranoia = paranoia
        self.idleness = idleness
        self.mission_value_thresholds: tuple[int, int, int] = mission_value_thresholds
        self.high_card = high_card
        self.conservative_interval = conservative_interval

    async def pick(self, state: Spymaster) -> int:
        p = state.current_mission if state.current_mission is not None else 1
        mine = state.white_cards
        theirs = state.black_cards

        def _mx(low, high):
            return mx(mine, theirs, low, high)

        def _aim(target):
            return aim(mine, target)

        th_low, th_mid, th_high = self.mission_value_thresholds

        if p < th_low:
            # Try to win in the range if we can, otherwise discard
            return prefer(_mx(p, p + 4), chuck(mine))
        elif p < th_mid:
            # Try to win in the range if we can, otherwise aim just above
            return prefer(_mx(p, p + 3), _aim(randint(p + 1, p + 3)))
        elif p < th_high:  # Highish-value mission
            # If the assassin is available, consider using it
            return prefer(
                _mx(p, p + 2),
                0 if (0 in mine and check(self.bloodthirst)) else None,
                _aim(randint(p + 1, p + 2)),
            )
        else:  # Very high value mission
            # Start by following a similar strategy...
            e = prefer(
                _mx(th_high, 15),
                0 if (0 in mine and check(self.bloodthirst)) else None,
                _aim(randint(p, 16)),
            )

            # Check ourselves before playing a high-value card - maybe
            # we want to duck instead.
            if e > self.high_card and 0 in theirs and check(self.paranoia):
                # Worried the opponent will play the assassin
                e = chuck(mine)
            elif e > self.high_card and check(self.idleness):
                # Conservatively save the high card for later
                e = _aim(randint(*self.conservative_interval))

            return e

china = RandomPlayer(name="AI (Easiest)")
france = SimpleAimingPlayer(name="AI (Easy)", variance=2)
britain = SimpleAimingPlayer(name="AI (Medium)", variance=4)
america = AmericaPlayer(name="AI (Hard)")
russia = RussiaPlayer(name="AI (Hardest)", bloodthirst=0.5, paranoia=0.5, idleness=0.33)

default_computer_players = [china, france, britain, america, russia]
default_computer_player_names = [p.name for p in default_computer_players]
