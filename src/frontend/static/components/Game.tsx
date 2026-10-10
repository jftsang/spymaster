import { useEffect, useState } from "preact/hooks";
import { game } from "../state";
import { sendWs } from "../ws";
import { Board } from "./Board";

export const GameView = () => {
  const g = game.value;
  const situation = g?.situation ?? null;
  const result = g?.result ?? null;
  const turn = g?.turn ?? 0;
  const awaitingMove = g?.awaitingMove ?? false;

  const [ready, setReady] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);

  // A new turn from the server resets the interaction gate.
  useEffect(() => {
    setReady(false);
    setSelected(null);
  }, [turn]);

  // Each new result is shown until the player acknowledges it.
  useEffect(() => {
    if (result) setShowResult(true);
  }, [result]);

  const pick = (card: number) => {
    if (!ready || !situation || !situation.whiteCards.includes(card)) return;
    setSelected(card);
    setReady(false);
    sendWs({ msgType: "card", card });
  };

  const cont = () => {
    setShowResult(false);
    setSelected(null);
    setReady(true);
  };

  const leave = () => {
    if (window.confirm("Leave the game? You will forfeit.")) {
      sendWs({ msgType: "leaveGame" });
    }
  };

  const canContinue = awaitingMove && !ready && selected === null;

  useEffect(() => {
    const handler = (ev: KeyboardEvent) => {
      if (ready && situation) {
        const shortcuts = "0123456789abcdef";
        if (shortcuts.includes(ev.key)) {
          pick(shortcuts.indexOf(ev.key));
        }
      } else if (canContinue && ev.key === "Enter") {
        cont();
      }
    };
    document.addEventListener("keypress", handler);
    return () => document.removeEventListener("keypress", handler);
  });

  if (!g || !situation) {
    return <div class="container py-4">Waiting for game state…</div>;
  }

  const opponent = g.opponent || situation.black;

  return (
    <div class="container py-4">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4 class="mb-0">
          Playing against <strong>{opponent}</strong>
        </h4>
        <button class="btn btn-outline-danger btn-sm" onClick={leave}>
          Leave game
        </button>
      </div>
      {g.opponentStatus === "disconnected" && (
        <div class="alert alert-warning">
          {opponent}'s connection was lost — 5 minute grace period.
        </div>
      )}
      <Board
        situation={situation}
        result={result}
        ready={ready}
        selected={selected}
        showResult={showResult}
        canContinue={canContinue}
        onPick={pick}
        onContinue={cont}
      />
    </div>
  );
};
