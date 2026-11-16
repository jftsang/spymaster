import { useEffect, useState } from "preact/hooks";
import "./tournaments.css";

type Payload = {
  players: string[];
  evaluators: string[];
  scores: number[][];
};

const POSITIVE: [number, number, number] = [25, 135, 84];
const NEGATIVE: [number, number, number] = [220, 53, 69];

const intensity = (value: number, maxAbs: number): number =>
  maxAbs <= 0 ? 0 : Math.min(1, Math.abs(value) / maxAbs);

const mix = (value: number, maxAbs: number): string => {
  const t = intensity(value, maxAbs);
  if (t < 0.02) return "rgb(248, 249, 250)";
  const target = value >= 0 ? POSITIVE : NEGATIVE;
  const [r, g, b] = target.map((c) => Math.round(248 - t * (248 - c)));
  return `rgb(${r}, ${g}, ${b})`;
};

const textColor = (value: number, maxAbs: number): string =>
  intensity(value, maxAbs) > 0.5 ? "#ffffff" : "#212529";

const quantile = (sorted: number[], q: number): number => {
  if (sorted.length === 0) return 0;
  const position = (sorted.length - 1) * q;
  const base = Math.floor(position);
  const remainder = position - base;
  const next = base + 1 < sorted.length ? sorted[base + 1] : sorted[base];
  return sorted[base] + remainder * (next - sorted[base]);
};

const formatScore = (value: number): string =>
  value > 0 ? `+${value}` : String(value);

type SortBy = "order" | "total";

export const TournamentsView = () => {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortBy>("order");

  useEffect(() => {
    fetch("/api/tournaments")
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail ?? `${res.status} ${res.statusText}`);
        }
        return res.json();
      })
      .then((json: Payload) => setData(json))
      .catch((err) => setError(String(err)));
  }, []);

  let body;
  if (error) {
    body = <div class="alert alert-danger">Could not load results: {error}</div>;
  } else if (data === null) {
    body = <div class="text-muted">Loading tournament results…</div>;
  } else if (data.players.length === 0) {
    body = (
      <div class="alert alert-warning">
        No tournament results found. Run{" "}
        <code>python -m spymaster tournament</code> to generate them.
      </div>
    );
  } else {
    const totals = data.players.map((_, i) =>
      data.scores[i].reduce((sum, value) => sum + value, 0),
    );
    const sameSets =
      data.players.length === data.evaluators.length &&
      data.players.every((name, i) => name === data.evaluators[i]);
    const rowOrder = data.players.map((_, i) => i);
    if (sortBy === "total") {
      rowOrder.sort((a, b) => totals[b] - totals[a]);
    }
    const columnOrder = sameSets
      ? rowOrder
      : data.evaluators.map((_, i) => i);
    const allValues = data.scores.reduce(
      (values, row) => values.concat(row),
      [] as number[],
    );
    const maxAbs = Math.max(1, ...allValues.map((v) => Math.abs(v)));

    const sortedTotals = [...totals].sort((a, b) => a - b);
    const q1 = quantile(sortedTotals, 0.25);
    const q3 = quantile(sortedTotals, 0.75);
    const iqr = q3 - q1;
    const lowFence = q1 - 1.5 * iqr;
    const highFence = q3 + 1.5 * iqr;
    const isOutlier = (total: number) =>
      total < lowFence || total > highFence;

    body = (
      <>
        <div class="d-flex flex-wrap align-items-center gap-3 mb-3 small text-muted">
          <label class="d-flex align-items-center gap-2">
            Sort by
            <select
              class="form-select form-select-sm w-auto"
              value={sortBy}
              onChange={(e) =>
                setSortBy((e.target as HTMLSelectElement).value as SortBy)
              }
            >
              <option value="order">Player order</option>
              <option value="total">Total score</option>
            </select>
          </label>
          <span>
            <span class="legend-swatch legend-positive" /> positive
          </span>
          <span>
            <span class="legend-swatch legend-negative" /> negative
          </span>
          <span>Rows outside the Tukey fences are marked as outliers.</span>
        </div>

        <div class="tournaments-scroll">
          <table class="table table-sm table-bordered align-middle tournaments-table">
            <thead class="table-dark">
              <tr>
                <th scope="col" class="player-head">Player</th>
                {columnOrder.map((j) => (
                  <th key={j} scope="col" class="text-center">
                    {data.evaluators[j]}
                  </th>
                ))}
                <th scope="col" class="text-center">Total</th>
              </tr>
            </thead>
            <tbody>
              {rowOrder.map((i) => {
                const total = totals[i];
                const outlier = isOutlier(total);
                return (
                  <tr key={i} class={outlier ? "outlier-row" : undefined}>
                    <th scope="row" class="player-head">
                      {data.players[i]}
                      {outlier && (
                        <span class="badge text-bg-warning ms-2">outlier</span>
                      )}
                    </th>
                    {columnOrder.map((j) => {
                      const value = data.scores[i][j];
                      const self = sameSets && i === j;
                      return (
                        <td
                          key={j}
                          class="text-center score-cell"
                          style={
                            self
                              ? undefined
                              : {
                                  backgroundColor: mix(value, maxAbs),
                                  color: textColor(value, maxAbs),
                                }
                          }
                          title={`${data.players[i]} vs ${data.evaluators[j]}: ${formatScore(value)}`}
                        >
                          {self ? "—" : formatScore(value)}
                        </td>
                      );
                    })}
                    <td class="text-center fw-semibold">
                      {formatScore(total)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </>
    );
  }

  return (
    <div class="container-fluid py-3">
      <h1 class="h3 mb-1">Tournament results</h1>
      <p class="text-muted mb-2">
        Round-robin results for every pair of computer players. Each cell is the
        row player's net score over 100 games against the column player:{" "}
        <strong>+1</strong> for a win, <strong>0</strong> for a draw, and{" "}
        <strong>-1</strong> for a loss. Rows are sorted by the selected option.
      </p>
      {body}
    </div>
  );
};
