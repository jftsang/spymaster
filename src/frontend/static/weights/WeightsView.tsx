import { useEffect, useState } from "preact/hooks";
import "./weights.css";

type PlayerWeights = {
  name: string;
  file: string;
  weights: number[][];
};

type Payload = {
  inputs: number;
  players: PlayerWeights[];
};

const ROWS = 16;

const GROUPS: { label: string; start: number; count: number }[] = [
  { label: "My hand", start: 0, count: 16 },
  { label: "Opponent's hand", start: 16, count: 16 },
  { label: "Missions still in play", start: 32, count: 16 },
  { label: "Context", start: 48, count: 3 },
];

const CONTEXT_LABELS = ["Mission", "My score", "Opp score"];

const POSITIVE: [number, number, number] = [214, 45, 45];
const NEGATIVE: [number, number, number] = [45, 90, 214];

const cardName = (card: number) => (card === 0 ? "the assassin (💣)" : String(card));

const columnTitle = (index: number): string => {
  if (index < 16) return `while I still hold card ${cardName(index)}`;
  if (index < 32) return `while the opponent still holds card ${cardName(index - 16)}`;
  if (index < 48) return `on mission ${index - 32 + 1} (still in play)`;
  return `scaled by my ${CONTEXT_LABELS[index - 48].toLowerCase()}`;
};

const columnLabel = (index: number): string => {
  if (index < 16) return index === 0 ? "💣" : String(index);
  if (index < 32) return index - 16 === 0 ? "💣" : String(index - 16);
  if (index < 48) return String(index - 32 + 1);
  return CONTEXT_LABELS[index - 48];
};

const intensity = (value: number, maxAbs: number): number =>
  maxAbs <= 0 ? 0 : Math.min(1, Math.abs(value) / maxAbs);

const mix = (value: number, maxAbs: number): string => {
  const t = intensity(value, maxAbs);
  if (t < 0.02) return "rgb(255, 255, 255)";
  const target = value >= 0 ? POSITIVE : NEGATIVE;
  const [r, g, b] = target.map((c) => Math.round(255 - t * (255 - c)));
  return `rgb(${r}, ${g}, ${b})`;
};

const textColor = (value: number, maxAbs: number): string =>
  intensity(value, maxAbs) > 0.5 ? "#ffffff" : "#212529";

const groupStart = new Set(GROUPS.map((g) => g.start));

export const WeightsView = () => {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);
  const [showValues, setShowValues] = useState(false);

  useEffect(() => {
    fetch("/api/weights")
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return res.json();
      })
      .then((json: Payload) => setData(json))
      .catch((err) => setError(String(err)));
  }, []);

  let body;
  if (error) {
    body = <div class="alert alert-danger">Could not load weights: {error}</div>;
  } else if (data === null) {
    body = <div class="text-muted">Loading weights…</div>;
  } else if (data.players.length === 0) {
    body = (
      <div class="alert alert-warning">
        No trained linear weights found. Train a player first (see{" "}
        <code>gene_pool.py</code>).
      </div>
    );
  } else {
    const player = data.players[Math.min(selected, data.players.length - 1)];
    const maxAbs = player.weights.reduce(
      (m, row) => row.reduce((rm, v) => Math.max(rm, Math.abs(v)), m),
      0,
    );

    body = (
      <>
        <div class="d-flex flex-wrap align-items-center gap-3 mb-2">
          <div class="btn-group" role="group">
            {data.players.map((p, i) => (
              <button
                key={p.file}
                class={"btn btn-sm " + (i === selected ? "btn-primary" : "btn-outline-primary")}
                onClick={() => setSelected(i)}
              >
                {p.name}
              </button>
            ))}
          </div>
          <div class="form-check form-switch">
            <input
              class="form-check-input"
              type="checkbox"
              id="show-values"
              checked={showValues}
              onChange={() => setShowValues((v) => !v)}
            />
            <label class="form-check-label" for="show-values">
              Show values
            </label>
          </div>
          <div class="d-flex align-items-center gap-2 small text-muted">
            <span>-{maxAbs.toFixed(1)}</span>
            <span class="legend-gradient" />
            <span>+{maxAbs.toFixed(1)}</span>
          </div>
        </div>

        <div class="weights-scroll">
          <table class="weights-table">
            <thead>
              <tr>
                <th class="row-head" rowspan={2}>
                  Play
                </th>
                {GROUPS.map((g) => (
                  <th key={g.label} class="group-head" colspan={g.count}>
                    {g.label}
                  </th>
                ))}
              </tr>
              <tr>
                {Array.from({ length: player.weights[0].length }, (_, j) => (
                  <th key={j} class={"col-head" + (groupStart.has(j) ? " group-start" : "")}>
                    {columnLabel(j)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {player.weights.map((row, c) => (
                <tr key={c}>
                  <th class="row-head" title={`Score for playing card ${cardName(c)}`}>
                    {c === 0 ? "💣" : c}
                  </th>
                  {row.map((value, j) => (
                    <td
                      key={j}
                      class={groupStart.has(j) ? "group-start" : undefined}
                      style={{
                        backgroundColor: mix(value, maxAbs),
                        color: textColor(value, maxAbs),
                      }}
                      title={`${value.toFixed(3)} — playing ${cardName(c)} ${columnTitle(j)}`}
                    >
                      {showValues ? value.toFixed(1) : ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    );
  }

  return (
    <div class="container-fluid py-3">
      <h1 class="h3 mb-1">Weight explorer</h1>
      <p class="text-muted mb-3">
        Each row is the candidate card to play; each column is an input to the
        linear layer. The cell is that weight: <span class="text-danger">red</span>{" "}
        pushes the score up, <span style="color: #2d5ad6">blue</span> pulls it
        down, white is neutral. The player's chosen card is the one with the
        highest row total.
      </p>
      {body}
    </div>
  );
};
