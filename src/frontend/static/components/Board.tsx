import { GameStateData, MissionResultData } from "../state";
import { MissionButton, RemainingMissions } from "./Missions";

export const SHORTCUTS = "`123qwerasdfzxcv";

type AgentCardProps = {
  value: number;
  kind: "you" | "opp";
  disabled?: boolean;
  selected?: boolean;
  played?: boolean;
  shortcut?: string;
  onClick?: () => void;
};

const AgentCard = ({
  value,
  kind,
  disabled,
  selected,
  played,
  shortcut,
  onClick,
}: AgentCardProps) => {
  let cls = "btn agentcard " + (kind === "you" ? "btn-primary" : "btn-danger");
  if (selected) cls += " our-selected";
  if (played) cls += " their-selected";
  const icon = kind === "you" ? "spyb" : "spyr";
  const inHand = shortcut !== undefined;
  const waitingForTurn = kind === "you" && inHand && disabled;
  const visuallyDisabled = disabled && !waitingForTurn;
  const key =
    kind === "you" && !visuallyDisabled
      ? (shortcut ?? SHORTCUTS[value])
      : undefined;
  return (
    <button
      class={cls}
      disabled={visuallyDisabled}
      aria-label={value > 0 ? `Agent ${value}` : "Ghost"}
      onClick={waitingForTurn ? undefined : onClick}
    >
      <img src={`/static/icons/${icon}${value}.gif`} alt="" />
      {key ? <span class="card-shortcut">{key}</span> : null}
    </button>
  );
};

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
      const inHand = cards.includes(card);
      cells.push(
        <AgentCard
          key={card}
          value={card}
          kind={kind}
          disabled={disabled || !inHand}
          selected={selected === card}
          played={played === card}
          shortcut={kind === "you" && inHand ? SHORTCUTS[card] : undefined}
          onClick={
            kind === "you" && onPick ? () => onPick(card) : undefined
          }
        />,
      );
    }
    rows.push(
      <div key={r} class="row flex-nowrap justify-content-center align-items-center">
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

  let gameOverLabel = "";
  let gameOverClass = "";
  if (gameOverPending) {
    if (situation.whiteScore > situation.blackScore) {
      gameOverLabel = "You won!";
      gameOverClass = "btn-primary";
    } else if (situation.whiteScore < situation.blackScore) {
      gameOverLabel = `${opponent} won!`;
      gameOverClass = "btn-danger";
    } else {
      gameOverLabel = "Draw!";
      gameOverClass = "btn-secondary";
    }
  }

  return (
    <div>
      <div class="d-flex flex-row-reverse flex-md-column gap-3 gap-md-0">
        <RemainingMissions
          remainingMissions={situation.remainingMissions}
          currentMission={situation.currentMission}
          missionRevealed={missionRevealed}
        />
        <div class="flex-grow-1" style={{ minWidth: 0 }}>
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
        </div>
      </div>

      <div class="d-flex flex-wrap flex-md-nowrap justify-content-center align-items-center gap-3 mt-3">
        {showResult && result ? (
          <div class="order-1">
            <AgentCard value={result.youPlayed} kind="you" />
          </div>
        ) : null}
        <div class="order-3 order-md-2 result-message text-center">
          <p class="text-nowrap mb-0">{message}</p>
        </div>
        {showResult && result ? (
          <div class="order-2 order-md-3">
            <AgentCard value={result.oppPlayed} kind="opp" />
          </div>
        ) : null}
      </div>

      {canContinue || gameOverPending ? (
        <div class="row justify-content-center">
          <div class="col-12 d-flex justify-content-center">
            <button
              class={
                "btn w-auto text-nowrap px-4 " +
                (gameOverPending
                  ? gameOverClass
                  : firstMission
                    ? "btn-warning"
                    : "btn-success")
              }
              onClick={gameOverPending ? onGameOver : onContinue}
            >
              {gameOverPending
                ? gameOverLabel
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
