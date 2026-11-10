from abc import ABC, abstractmethod

from spymaster import AgentCard, MissionResult, Spymaster


class Player(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def pick(self, state: Spymaster) -> AgentCard:
        """Choose which card (0 up to 15) to play, given the state of
        the game, always presented as though this player is White.
        """
        raise NotImplementedError

    async def receive(self, state: Spymaster, result: MissionResult) -> None:
        """Do something with the result from a round. For AI players
        this might mean updating some state. For human players this
        means acknowledging the result.
        """

    async def warn_illegal_choice(
        self, situation: Spymaster, picked: AgentCard
    ) -> None:
        """Warn the player that she picked an illegal card. For AI
        players this should raise an exception; for human players it
        should result in them being given an error message and invited
        to try again.
        """
        raise ValueError("Illegal choice")


Spymaster.model_rebuild()
