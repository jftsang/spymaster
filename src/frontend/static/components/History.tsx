import { useEffect } from "preact/hooks";
import { HistoryStepData } from "../state";

const PlayedCard = ({ card, kind }: { card: number; kind: "you" | "opp" }) => (
  <span class={"badge " + (kind === "you" ? "bg-primary" : "bg-danger")}>
    {card > 0 ? String(card) : "💣"}
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
  open: boolean;
  onClose: () => void;
};

/**
 * Wide screens show the game log in a fixed sidebar on the right, leaving
 * the board itself centered. Narrow screens hide it behind the Game log
 * button and show it as a modal overlay instead (see the CSS breakpoint).
 */
export const History = ({ history, opponent, open, onClose }: HistoryProps) => {
  useEffect(() => {
    if (!open) return;
    const handler = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (history.length === 0) return null;

  return (
    <>
      <aside class="game-history" aria-label="Game log">
        <div class="card bg-dark border-secondary">
          <div class="card-header small py-1">Game log</div>
          <HistoryTable history={history} opponent={opponent} />
        </div>
      </aside>

      {open ? (
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
            <div class="modal-content bg-dark text-light border-secondary">
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
