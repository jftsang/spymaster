import { useEffect } from "preact/hooks";
import { HistoryStepData } from "../state";

const PlayedCard = ({ card, kind }: { card: number; kind: "you" | "opp" }) => (
  <span class={"badge " + (kind === "you" ? "bg-primary" : "bg-danger")}>
    {card > 0 ? String(card) : "👻"}
  </span>
);

const HistoryTable = ({
  history,
  opponent,
}: {
  history: HistoryStepData[];
  opponent: string;
}) => (
  <div class="history-table">
    <table class="table table-sm table-dark table-striped text-center align-middle mb-0">
      <thead>
        <tr>
          <th scope="col">Mission</th>
          <th scope="col">You</th>
          <th scope="col">{opponent}</th>
          <th scope="col">Score</th>
        </tr>
      </thead>
      <tbody>
        {history.map((step) => (
          <tr key={step.mission}>
            <td>{step.mission}</td>
            <td>
              <PlayedCard card={step.whitePlayed} kind="you" />
            </td>
            <td>
              <PlayedCard card={step.blackPlayed} kind="opp" />
            </td>
            <td>
              {step.whiteScore}–{step.blackScore}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

type HistoryProps = {
  history: HistoryStepData[];
  opponent: string;
  visible: boolean;
  sidebar?: boolean;
  onOpen?: () => void;
  onClose: () => void;
};

/**
 * On 1200px+ screens the game log is an accessory panel: fixed sidebars on
 * very wide screens or an in-flow side column on medium-wide screens. In
 * that mode it can be collapsed to its title bar instead of removed. On
 * narrower screens it is shown as a modal overlay.
 */
export const History = ({
  history,
  opponent,
  visible,
  sidebar,
  onOpen,
  onClose,
}: HistoryProps) => {
  useEffect(() => {
    if (!visible || sidebar) return;
    const handler = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [visible, sidebar, onClose]);

  return (
    <>
      <aside class="game-history" aria-label="Game log">
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
            <span>Game log (h)</span>
            {sidebar ? (
              <button
                type="button"
                class="btn btn-sm btn-link text-light p-0 lh-1 text-decoration-none accessory-toggle"
                aria-label={visible ? "Collapse game log" : "Expand game log"}
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
          {visible ? <HistoryTable history={history} opponent={opponent} /> : null}
        </div>
      </aside>

      {!sidebar && visible ? (
        <div
          class="modal d-block history-modal"
          style="background: rgba(0,0,0,0.6);"
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-label="Game log"
          onClick={onClose}
        >
          <div
            class="modal-dialog modal-dialog-centered"
            onClick={(ev) => ev.stopPropagation()}
          >
            <div class="modal-content bg-dark text-white border-secondary">
              <div class="modal-header">
                <h5 class="modal-title">Game log</h5>
                <button
                  type="button"
                  class="btn-close btn-close-white"
                  aria-label="Close"
                  onClick={onClose}
                />
              </div>
              <div class="modal-body p-0">
                <HistoryTable history={history} opponent={opponent} />
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
