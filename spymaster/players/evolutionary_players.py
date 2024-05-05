import abc
from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from spymaster import Spymaster
from spymaster.players import Player


class EvolutionaryPlayer(Player, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def create_offspring(self, mutation_rate: float) -> "EvolutionaryPlayer":
        pass


@dataclass
class SingleLayerPerceptronPlayer(EvolutionaryPlayer):
    weights_matrix: np.ndarray
    INPUTS_LENGTH: ClassVar[int] = 16 + 16 + 16 + 1 + 1 + 1

    def __post_init__(self):
        self.weights_matrix = self.weights_matrix.astype(np.float32)

        if self.weights_matrix.shape != (16, self.INPUTS_LENGTH):
            raise ValueError(f"Invalid shape: {self.weights_matrix.shape}")

    @classmethod
    def randomized(cls) -> "SingleLayerPerceptronPlayer":
        return cls(name="random", weights_matrix=np.random.normal(0, 1, (16, cls.INPUTS_LENGTH)))

    def __str__(self):
        white_weights = self.weights_matrix[:, :16]
        black_weights = self.weights_matrix[:, 16:32]
        mission_weights = self.weights_matrix[:, 32:48]
        current_mission_weight = self.weights_matrix[:, 48]
        score_weights = self.weights_matrix[:, 49:51]
        return f"""SingleLayerPerceptronPlayer(
    white_weights={white_weights},
    black_weights={black_weights},
    mission_weights={mission_weights},
    current_mission_weight={current_mission_weight},
    score_weights={score_weights},
)"""


    def create_offspring(self, mutation_rate=0.1) -> "SingleLayerPerceptronPlayer":
        new_weights = self.weights_matrix.copy()
        new_weights += np.random.normal(0, mutation_rate, self.weights_matrix.shape)
        return SingleLayerPerceptronPlayer(name=self.name, weights_matrix=new_weights)

    def to_vector(self, state: Spymaster) -> np.ndarray:
        vec = np.zeros(self.INPUTS_LENGTH, dtype=np.float32)
        for i in state.white_cards:
            vec[i] = 1
        for i in state.black_cards:
            vec[i + 16] = 1
        for i in state.remaining_missions:
            vec[i + 32] = 1

        vec[16 + 16 + 16] = state.current_mission
        vec[16 + 16 + 16 + 1] = state.white_score
        vec[16 + 16 + 16 + 2] = state.black_score
        return vec

    async def pick(self, state: Spymaster) -> int:
        vec = self.to_vector(state)
        choices_weights = self.weights_matrix @ vec
        choices_weights[vec[:16] == 0] = -np.inf
        best_choice = np.argmax(choices_weights)
        return best_choice
