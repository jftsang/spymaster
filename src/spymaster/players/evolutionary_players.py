import abc

from spymaster.players import Player


class EvolutionaryPlayer(Player, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def create_offspring(self, mutation_rate: float = 0.1) -> EvolutionaryPlayer:
        pass
