import { useEffect, useState } from "preact/hooks";
import { AnalysisData, game, gameOverAcknowledged } from "../state";
import { sendWs } from "../ws";
import { Analysis } from "./Analysis";
import { Board, SHORTCUTS } from "./Board";
import { History } from "./History";

const SIDE_QUERY = "(min-width: 1200px)";
const WIDE_QUERY = "(min-width: 1600px)";
const hasSideLayout = () => window.matchMedia(SIDE_QUERY).matches;
const hasFixedSidebars = () => window.matchMedia(WIDE_QUERY).matches;

export const GameView = () => {
  const g = game.value;
  const situation = g?.situation ?? null;
  const result = g?.result ?? null;
  const turn = g?.turn ?? 0;
  const awaitingMove = g?.awaitingMove ?? false;
  const over = g?.over ?? false;
  const opponent = g?.opponent || situation?.black || "Opponent";
  const opponentIsComputer = g?.opponentIsComputer ?? false;

  const [ready, setReady] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [revealedTurn, setRevealedTurn] = useState<number | null>(null);
  const [sideLayout, setSideLayout] = useState(hasSideLayout);
  const [fixedSidebars, setFixedSidebars] = useState(hasFixedSidebars);
  const [historyVisible, setHistoryVisible] = useState(hasSideLayout);
  const [analysisVisible, setAnalysisVisible] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // The mission card stays hidden until the player acknowledges this turn.
  const missionRevealed = revealedTurn === turn;
  const historyModalOpen = !sideLayout && historyVisible;
  const analysisModalOpen =
    !sideLayout && analysisVisible && opponentIsComputer;
  const sideColumn = sideLayout && !fixedSidebars;

  // Keep the default visibility in step with the responsive breakpoints.
  useEffect(() => {
    const sideQuery = window.matchMedia(SIDE_QUERY);
    const wideQuery = window.matchMedia(WIDE_QUERY);
    const update = () => {
      const side = sideQuery.matches;
      setSideLayout(side);
      setFixedSidebars(wideQuery.matches);
      setHistoryVisible(side);
      setAnalysisVisible(false);
    };
    sideQuery.addEventListener("change", update);
    wideQuery.addEventListener("change", update);
    return () => {
      sideQuery.removeEventListener("change", update);
      wideQuery.removeEventListener("change", update);
    };
  }, []);

  // A new turn from the server resets the interaction gate.
  useEffect(() => {
    setReady(false);
    setSelected(null);
  }, [turn]);

  // Each new result is shown until the player acknowledges it.
  useEffect(() => {
    if (result) setShowResult(true);
  }, [result]);

  // Analyse each new position against a computer opponent. The turn
  // changes only when a new decision is presented, so result displays do
  // not trigger a fresh analysis.
  useEffect(() => {
    const mission = situation?.currentMission ?? null;
    if (!opponentIsComputer || situation === null || mission === null || over) {
      setAnalysis(null);
      setAnalysisLoading(false);
      setAnalysisError(null);
      return;
    }

    const controller = new AbortController();
    const missions = situation.remainingMissions.slice();
    if (!missions.includes(mission)) missions.push(mission);

    setAnalysis(null);
    setAnalysisLoading(true);
    setAnalysisError(null);

    const load = async () => {
      try {
        const response = await fetch("/analysis", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ours: situation.whiteCards,
            theirs: situation.blackCards,
            missions,
            currentMission: mission,
            whiteScore: situation.whiteScore,
            blackScore: situation.blackScore,
          }),
          signal: controller.signal,
        });
        if (!response.ok) {
          const body = await response.json().catch(() => null);
          throw new Error(
            body?.detail ?? `${response.status} ${response.statusText}`,
          );
        }
        const data = (await response.json()) as AnalysisData;
        if (!controller.signal.aborted) setAnalysis(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setAnalysisError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!controller.signal.aborted) setAnalysisLoading(false);
      }
    };
    void load();

    return () => controller.abort();
  }, [turn, opponentIsComputer, over]);

  const pick = (card: number) => {
    if (!ready || !situation || !situation.whiteCards.includes(card)) return;
    setSelected(card);
    setReady(false);
    sendWs({ msgType: "card", card });
  };

  const cont = () => {
    setShowResult(false);
    setSelected(null);
    setRevealedTurn(turn);
    setReady(true);
  };

  const acknowledgeGameOver = () => {
    gameOverAcknowledged.value = true;
  };

  const leave = () => {
    if (window.confirm("Leave the game? You will forfeit.")) {
      sendWs({ msgType: "leaveGame" });
    }
  };

  const canContinue = awaitingMove && !ready && selected === null;
  const gameOverPending =
    over && (result?.gameOver ?? false) && showResult &&
    !gameOverAcknowledged.value;

  useEffect(() => {
    const handler = (ev: KeyboardEvent) => {
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      if (ev.key === "h") {
        const next = !historyVisible;
        setHistoryVisible(next);
        if (!sideLayout && next) setAnalysisVisible(false);
        return;
      }
      if (ev.key === "y" && opponentIsComputer) {
        const next = !analysisVisible;
        setAnalysisVisible(next);
        if (!sideLayout && next) setHistoryVisible(false);
        return;
      }
      if (historyModalOpen || analysisModalOpen) return;
      if (ready && situation) {
        if (SHORTCUTS.includes(ev.key)) {
          pick(SHORTCUTS.indexOf(ev.key));
        }
      } else if (ev.key === "Enter" || ev.key === " ") {
        if (canContinue) cont();
        else if (gameOverPending) acknowledgeGameOver();
      }
    };
    document.addEventListener("keypress", handler);
    return () => document.removeEventListener("keypress", handler);
  });

  if (!g || !situation) {
    return <div class="container py-4">Waiting for game state…</div>;
  }

  const analysisPanel = opponentIsComputer ? (
    <Analysis
      data={analysis}
      loading={analysisLoading}
      error={analysisError}
      opponent={opponent}
      enabled={opponentIsComputer}
      visible={analysisVisible}
      pending={canContinue}
      sidebar={sideLayout}
      onOpen={() => setAnalysisVisible(true)}
      onClose={() => setAnalysisVisible(false)}
    />
  ) : null;
  const historyPanel = (
    <History
      history={situation.history}
      opponent={opponent}
      visible={historyVisible}
      sidebar={sideLayout}
      onOpen={() => setHistoryVisible(true)}
      onClose={() => setHistoryVisible(false)}
    />
  );

  return (
    <div class={"py-4 " + (fixedSidebars ? "container" : "container-fluid px-3 px-xl-4")}>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4 class="mb-0">
          Playing against <strong>{opponent}</strong>
        </h4>
        <div class="d-flex gap-2">
          {opponentIsComputer && (
            <button
              class="btn btn-outline-info btn-sm analysis-toggle"
              onClick={() => {
                setAnalysisVisible(true);
                if (!sideLayout) setHistoryVisible(false);
              }}
            >
              Analysis
            </button>
          )}
          <button
            class="btn btn-outline-light btn-sm history-toggle"
            onClick={() => {
              setHistoryVisible(true);
              if (!sideLayout) setAnalysisVisible(false);
            }}
          >
            Game log
          </button>
          <button class="btn btn-outline-danger btn-sm" onClick={leave}>
            Leave game
          </button>
        </div>
      </div>
      {g.opponentStatus === "disconnected" && (
        <div class="alert alert-warning">
          {opponent}'s connection was lost — 5 minute grace period.
        </div>
      )}
      <div class={sideColumn ? "game-layout" : undefined}>
        <div class={sideColumn ? "game-main" : undefined}>
          <Board
            situation={situation}
            result={result}
            ready={ready}
            selected={selected}
            showResult={showResult}
            missionRevealed={missionRevealed}
            canContinue={canContinue}
            gameOverPending={gameOverPending}
            onPick={pick}
            onContinue={cont}
            onGameOver={acknowledgeGameOver}
          />
        </div>
        {sideColumn ? (
          <div class="game-side-column">
            {analysisPanel}
            {historyPanel}
          </div>
        ) : null}
      </div>
      {!sideColumn ? (
        <>
          {analysisPanel}
          {historyPanel}
        </>
      ) : null}
    </div>
  );
};
