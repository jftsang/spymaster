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
  <button class="btn mission" disabled={disabled}>
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
  canContinue: boolean;
  onPick: (card: number) => void;
  onContinue: () => void;
};

export const Board = ({
  situation,
  result,
  ready,
  selected,
  showResult,
  canContinue,
  onPick,
  onContinue,
}: BoardProps) => {
  const opponent = situation.black;
  const missionValue = situation.currentMission ?? 0;
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
          {Array.from({ length: 16 }, (_, i) => (
            <MissionButton key={i} value={i + 1} disabled={i + 1 === missionValue} />
          ))}
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
          Mission <MissionButton value={missionValue} />
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

      {canContinue ? (
        <div class="row justify-content-center">
          <div class="col-4">
            <button
              class={"btn w-100 " + (firstMission ? "btn-warning" : "btn-success")}
              onClick={onContinue}
            >
              {firstMission ? "Start Game" : "Next Mission"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
};
