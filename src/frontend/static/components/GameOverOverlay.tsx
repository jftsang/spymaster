import { game, username, view } from "../state";

export const GameOverOverlay = () => {
  const g = game.value;
  if (!g || !g.over || view.value !== "game") return null;

  const me = username.value;
  const winner = g.winner;

  let title: string;
  if (!winner) title = "Draw!";
  else if (winner === me) title = "You won!";
  else title = `${winner} won!`;

  let detail = "";
  if (g.reason === "forfeit") {
    detail =
      winner === me
        ? "Your opponent forfeited (connection lost)."
        : "You forfeited (connection lost).";
  } else if (g.reason === "left") {
    detail = winner === me ? "Your opponent left the game." : "You left the game.";
  }

  return (
    <div class="modal d-block" style="background: rgba(0,0,0,0.6);" tabIndex={-1}>
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content bg-dark text-light border-secondary">
          <div class="modal-header">
            <h5 class="modal-title">Game over</h5>
          </div>
          <div class="modal-body">
            <h3>{title}</h3>
            {detail && <p class="text-muted">{detail}</p>}
          </div>
          <div class="modal-footer">
            <button
              class="btn btn-primary"
              onClick={() => {
                view.value = "lobby";
              }}
            >
              Back to lobby
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
