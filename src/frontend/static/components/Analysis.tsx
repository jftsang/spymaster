import { useEffect } from "preact/hooks";
import { AnalysisData } from "../state";

type StrategyOption = {
  card: number;
  probability: number;
};

const topThree = (cards: number[], strategy: number[]): StrategyOption[] =>
  cards
    .map((card, index) => ({ card, probability: strategy[index] ?? 0 }))
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 3);

const cardLabel = (card: number): string => (card > 0 ? String(card) : "👻");

const EquityBar = ({ equity }: { equity: number }) => {
  const width = `${Math.min(1, Math.abs(equity)) * 50}%`;
  return (
    <div class="equity-bar" aria-label={`Equity ${equity.toFixed(2)}`}>
      {equity >= 0 ? (
        <div class="equity-positive" style={{ width }} />
      ) : (
        <div class="equity-negative" style={{ width }} />
      )}
    </div>
  );
};

const Options = ({
  title,
  cards,
  strategy,
  kind,
}: {
  title: string;
  cards: number[];
  strategy: number[];
  kind: "you" | "opp";
}) => {
  const options = topThree(cards, strategy);
  const badge = kind === "you" ? "bg-primary" : "bg-danger";
  const bar = kind === "you" ? "bg-primary" : "bg-danger";
  return (
    <div class="mb-2">
      <div class="small fw-bold mb-1">{title}</div>
      {options.map((option) => (
        <div key={option.card} class="d-flex align-items-center gap-2 mb-1">
          <span class={"badge " + badge}>{cardLabel(option.card)}</span>
          <div class="progress flex-grow-1 analysis-probability">
            <div
              class={"progress-bar " + bar}
              style={{ width: `${option.probability * 100}%` }}
            />
          </div>
          <span class="small text-end analysis-percentage">
            {(option.probability * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  );
};

const AnalysisPanel = ({
  data,
  loading,
  error,
  opponent,
}: {
  data: AnalysisData | null;
  loading: boolean;
  error: string | null;
  opponent: string;
}) => (
  <div class="card bg-dark border-secondary">
    <div class="card-header small py-1">Analysis</div>
    <div class="card-body p-2">
      {loading ? <p class="small mb-2">Analysing…</p> : null}
      {error ? <p class="small text-danger mb-2">{error}</p> : null}
      {data ? (
        <>
          <div class="d-flex justify-content-between align-items-baseline mb-1">
            <span class="small">Equity</span>
            <span
              class={
                "small fw-bold " +
                (data.equity >= 0 ? "text-primary" : "text-danger")
              }
            >
              {data.equity > 0 ? "+" : ""}
              {data.equity.toFixed(2)}
            </span>
          </div>
          <EquityBar equity={data.equity} />
          <div class="d-flex justify-content-between analysis-scale mb-2">
            <span>+</span>
            <span>0</span>
            <span>−</span>
          </div>
          <Options
            title="Your best options"
            cards={data.ourCards}
            strategy={data.ourStrategy}
            kind="you"
          />
          <Options
            title={`${opponent}'s best options`}
            cards={data.theirCards}
            strategy={data.theirStrategy}
            kind="opp"
          />
        </>
      ) : null}
    </div>
  </div>
);

type AnalysisProps = {
  data: AnalysisData | null;
  loading: boolean;
  error: string | null;
  opponent: string;
  enabled: boolean;
  visible: boolean;
  sidebar?: boolean;
  onOpen?: () => void;
  onClose: () => void;
};

/**
 * On 1200px+ screens analysis is an accessory panel (sidebar or side column)
 * that collapses to its title bar. On narrower screens it is a modal.
 */
export const Analysis = ({
  data,
  loading,
  error,
  opponent,
  enabled,
  visible,
  sidebar,
  onOpen,
  onClose,
}: AnalysisProps) => {
  useEffect(() => {
    if (!visible || sidebar) return;
    const handler = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [visible, sidebar, onClose]);

  if (!enabled) return null;

  return (
    <>
      <aside class="game-analysis" aria-label="Analysis">
        <div class="card bg-dark border-secondary">
          <div
            class={
              "card-header small py-1 d-flex justify-content-between align-items-center accessory-header" +
              (sidebar && !visible ? " accessory-header-collapsed" : "")
            }
            onClick={sidebar && !visible ? onOpen : undefined}
            role={sidebar && !visible ? "button" : undefined}
            tabIndex={sidebar && !visible ? 0 : undefined}
            onKeyDown={
              sidebar && !visible && onOpen
                ? (ev) => {
                    if (ev.key === "Enter" || ev.key === " ") {
                      ev.preventDefault();
                      onOpen();
                    }
                  }
                : undefined
            }
          >
            <span>Analysis (y)</span>
            {sidebar ? (
              <button
                type="button"
                class="btn btn-sm btn-link text-light p-0 lh-1 text-decoration-none accessory-toggle"
                aria-label={visible ? "Collapse analysis" : "Expand analysis"}
                aria-expanded={visible}
                onClick={(ev) => {
                  ev.stopPropagation();
                  (visible ? onClose : onOpen)?.();
                }}
              >
                {visible ? "▾" : "▸"}
              </button>
            ) : null}
          </div>
          {visible ? (
            <div class="card-body p-2">
              {loading ? <p class="small mb-2">Analysing…</p> : null}
              {error ? <p class="small text-danger mb-2">{error}</p> : null}
              {data ? (
                <>
                  <div class="d-flex justify-content-between align-items-baseline mb-1">
                    <span class="small">Equity</span>
                    <span
                      class={
                        "small fw-bold " +
                        (data.equity >= 0 ? "text-primary" : "text-danger")
                      }
                    >
                      {data.equity > 0 ? "+" : ""}
                      {data.equity.toFixed(2)}
                    </span>
                  </div>
                  <EquityBar equity={data.equity} />
                  <div class="d-flex justify-content-between analysis-scale mb-2">
                    <span>+</span>
                    <span>0</span>
                    <span>−</span>
                  </div>
                  <Options
                    title="Your best options"
                    cards={data.ourCards}
                    strategy={data.ourStrategy}
                    kind="you"
                  />
                  <Options
                    title={`${opponent}'s best options`}
                    cards={data.theirCards}
                    strategy={data.theirStrategy}
                    kind="opp"
                  />
                </>
              ) : null}
            </div>
          ) : null}
        </div>
      </aside>

      {!sidebar && visible ? (
        <div
          class="modal d-block analysis-modal"
          style="background: rgba(0,0,0,0.6);"
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-label="Analysis"
          onClick={onClose}
        >
          <div
            class="modal-dialog modal-dialog-centered"
            onClick={(ev) => ev.stopPropagation()}
          >
            <div class="modal-content bg-dark text-white border-secondary">
              <div class="modal-header">
                <h5 class="modal-title">Analysis</h5>
                <button
                  type="button"
                  class="btn-close btn-close-white"
                  aria-label="Close"
                  onClick={onClose}
                />
              </div>
              <div class="modal-body p-2">
                <AnalysisPanel
                  data={data}
                  loading={loading}
                  error={error}
                  opponent={opponent}
                />
              </div>
              <div class="modal-footer">
                <button class="btn btn-secondary" onClick={onClose}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
};
