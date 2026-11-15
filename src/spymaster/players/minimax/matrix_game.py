"""Zero-sum matrix-game solving for minimax players."""

from collections.abc import Sequence
from math import inf, isfinite

from scipy.optimize import Bounds, LinearConstraint, milp

Matrix = Sequence[Sequence[float]]


def solve_matrix_game(matrix: Matrix) -> tuple[list[float], float]:
    """Return the row player's equilibrium strategy and game value.

    The row player maximises and the column player minimises. The
    returned strategy is a probability distribution over rows.
    """
    rows = [[float(value) for value in row] for row in matrix]
    if not rows or not rows[0]:
        raise ValueError("Matrix game must have at least one row and column")
    if any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("Matrix game must be rectangular")
    if not all(isfinite(value) for row in rows for value in row):
        raise ValueError("Matrix game must contain only finite values")

    row_count = len(rows)
    column_count = len(rows[0])

    if row_count == 1:
        return [1.0], min(rows[0])

    if column_count == 1:
        best_row = max(range(row_count), key=lambda row: rows[row][0])
        return _one_hot(best_row, row_count), rows[best_row][0]

    result = milp(
        c=[0.0] * row_count + [-1.0],
        constraints=[
            LinearConstraint(
                [
                    [-rows[row][column] for row in range(row_count)] + [1.0]
                    for column in range(column_count)
                ],
                lb=[-inf] * column_count,
                ub=[0.0] * column_count,
            ),
            LinearConstraint(
                [[1.0] * row_count + [0.0]],
                lb=[1.0],
                ub=[1.0],
            ),
        ],
        bounds=Bounds(
            lb=[0.0] * row_count + [-inf],
            ub=[inf] * (row_count + 1),
        ),
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"Could not solve matrix game: {result.message}")

    strategy = _normalise([float(value) for value in result.x[:row_count]])
    value = min(
        sum(strategy[row] * rows[row][column] for row in range(row_count))
        for column in range(column_count)
    )
    return strategy, float(value)


def _one_hot(index: int, length: int) -> list[float]:
    strategy = [0.0] * length
    strategy[index] = 1.0
    return strategy


def _normalise(probabilities: Sequence[float]) -> list[float]:
    cleaned = [max(0.0, float(value)) for value in probabilities]
    cleaned = [0.0 if value < 1e-12 else value for value in cleaned]
    total = sum(cleaned)
    if total <= 0.0:
        return [1.0 / len(cleaned)] * len(cleaned)
    return [value / total for value in cleaned]
