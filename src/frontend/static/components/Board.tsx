import { GameStateData, MissionResultData } from "../state";

type AgentCardProps = {
  value: number;
  kind: "you" | "opp";
  disabled?: boolean;
  selected?: boolean;
  played?: boolean;
  onClick?: () => void;
};

const AgentCard = ({
  value,
  kind,
  disabled,
  selected,
  played,
  onClick,
}: AgentCardProps) => {
  let cls = "btn agentcard " + (kind === "you" ? "btn-primary" : "btn-danger");
  if (selected) cls += " our-selected";
  if (played) cls += " their-selected";
  return (
    <button class={cls} disabled={disabled} onClick={onClick}>
      {value > 0 ? String(value) : "💣"}
    </button>
  );
};

const MissionButton = ({ value, disabled }: { value: number; disabled?: boolean }) => (
  <button class="btn btn-warning mission" disabled={disabled}>
    {String(value)}
  </button>
);

type CardGridProps = {
  cards: number[];
  kind: "you" | "opp";
  disabled?: boolean;
  selected?: number | null;
  played?: number | null;
  onPick?: (card: number) => void;
};

const CardGrid = ({
  cards,
  kind,
  disabled,
  selected,
  played,
  onPick,
}: CardGridProps) => {
  const rows = [];
  for (let r = 0; r < 4; r++) {
    const cells = [];
    for (let c = 0; c < 4; c++) {
      const card = r * 4 + c;
      cells.push(
        <AgentCard
          key={card}
          value={card}
          kind={kind}
          disabled={disabled || !cards.includes(card)}
          selected={selected === card}
          played={played === card}
          onClick={
            kind === "you" && onPick ? () => onPick(card) : undefined
          }
        />,
      );
    }
    rows.push(
      <div key={r} class="row justify-content-center align-items-center">
        {cells}
      </div>,
    );
  }
  return <div>{rows}</div>;
};

const scoreMessage = (result: MissionResultData, opponent: string): string => {
  if (result.youScored > 0) return `You scored ${result.youScored}`;
  if (result.oppScored > 0) return `${opponent} scored ${result.oppScored}`;
  return "Drawn round…";
};

type BoardProps = {
  situation: GameStateData;
  result: MissionResultData | null;
  ready: boolean;
  selected: number | null;
  showResult: boolean;
  missionRevealed: boolean;
  canContinue: boolean;
  gameOverPending: boolean;
  onPick: (card: number) => void;
  onContinue: () => void;
  onGameOver: () => void;
};

export const Board = ({
  situation,
  result,
  ready,
  selected,
  showResult,
  missionRevealed,
  canContinue,
  gameOverPending,
  onPick,
  onContinue,
  onGameOver,
}: BoardProps) => {
  const opponent = situation.black;
  // Until the player acknowledges the new turn, keep showing the mission
  // that has just been played (nothing at all on the first mission).
  const missionShown = missionRevealed
    ? (situation.currentMission ?? null)
    : (result?.mission ?? null);
  const firstMission = situation.whiteCards.length === 16;

  let message: string;
  if (showResult && result) message = scoreMessage(result, opponent);
  else if (ready) message = "Select an agent…";
  else if (selected != null) message = "Waiting for opponent…";
  else if (firstMission) message = "Press Start Game to begin";
  else message = "Press Next Mission to continue";

  let scoreLine = "";
  if (showResult && result && result.gameOver) {
    if (situation.whiteScore > situation.blackScore) scoreLine = "You won!";
    else if (situation.whiteScore < situation.blackScore)
      scoreLine = `${opponent} won!`;
    else scoreLine = "Draw!";
  }

  return (
    <div>
      <div class="row justify-content-center align-items-center mb-3">
        Remaining missions
        <div class="row d-flex justify-content-center">
          {Array.from({ length: 16 }, (_, i) => {
            const value = i + 1;
            const remaining = situation.remainingMissions.includes(value);
            // Keep the drawn mission looking like it is still to come
            // until the player acknowledges it.
            const hiddenCurrent =
              !missionRevealed && value === situation.currentMission;
            return (
              <MissionButton
                key={i}
                value={value}
                disabled={!remaining && !hiddenCurrent}
              />
            );
          })}
        </div>
      </div>

      <div class="row justify-content-center">
        <div class="col-md-4 justify-content-center align-items-center">
          <div class="row justify-content-center">You</div>
          <CardGrid
            cards={situation.whiteCards}
            kind="you"
            disabled={!ready}
            selected={selected}
            onPick={onPick}
          />
          <div class="row justify-content-center align-items-center">
            {`Score: ${situation.whiteScore}`}
          </div>
        </div>
        <div class="col-md-2 align-self-center text-center">
          {missionShown != null ? (
            <>
              Mission <MissionButton value={missionShown} />
            </>
          ) : null}
        </div>
        <div class="col-md-4 justify-content-center align-items-center">
          <div class="row justify-content-center">{opponent}</div>
          <CardGrid
            cards={situation.blackCards}
            kind="opp"
            played={showResult && result ? result.oppPlayed : null}
          />
          <div class="row justify-content-center align-items-center">
            {`Score: ${situation.blackScore}`}
          </div>
        </div>
      </div>

      <div class="row justify-content-center mt-3">
        <div class="col d-flex justify-content-end align-items-center">
          {showResult && result ? (
            <AgentCard value={result.youPlayed} kind="you" />
          ) : null}
        </div>
        <div class="col d-flex justify-content-center align-items-center">
          <p class="text-center mb-0">{message}</p>
        </div>
        <div class="col d-flex justify-content-start align-items-center">
          {showResult && result ? (
            <AgentCard value={result.oppPlayed} kind="opp" />
          ) : null}
        </div>
      </div>

      {scoreLine ? <p class="text-center">{scoreLine}</p> : null}

      {canContinue || gameOverPending ? (
        <div class="row justify-content-center">
          <div class="col-4">
            <button
              class={
                "btn w-100 " +
                (gameOverPending
                  ? "btn-danger"
                  : firstMission
                    ? "btn-warning"
                    : "btn-success")
              }
              onClick={gameOverPending ? onGameOver : onContinue}
            >
              {gameOverPending
                ? "Game over"
                : firstMission
                  ? "Start Game"
                  : "Next Mission"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
};
