const youButtons: HTMLButtonElement[] = [];
const oppButtons: HTMLButtonElement[] = [];
const missionButtons: HTMLButtonElement[] = [];

const missionInfoP = document.getElementById("currentMissionInfoP") as HTMLParagraphElement;
const messageP = document.getElementById("message") as HTMLParagraphElement;
const scoreP = document.getElementById("score") as HTMLParagraphElement;
const nextMissionBtn = document.getElementById("nextMissionBtn") as HTMLButtonElement;
const youPlayedDiv = document.getElementById("youPlayedDiv") as HTMLDivElement;
const oppPlayedDiv = document.getElementById("oppPlayedDiv") as HTMLDivElement;

enum State {
  SITUATION,
  WAITING_FOR_OPPONENT,
  RESULT,
  GAME_OVER,
}

enum Player {
  YOU,
  THEY,
}

let state: State = State.RESULT;

function missionButton(value: number, disabled: boolean = false) {
  const button = document.createElement("button");
  button.className = "btn btn-warning mission";
  button.dataset["mission"] = value.toString();
  button.innerHTML = value.toString();
  button.disabled = disabled;
  return button
}

function agentCard(value: number, player: Player) {
  const button = document.createElement("button");
  button.className = "btn agentcard";
  if (player === Player.YOU) {
    button.className += " btn-primary";
  } else {
    button.className += " btn-danger";
  }

  button.dataset["player"] = player.toString();
  button.dataset["card"] = value.toString();
  if (value > 0)
    button.innerHTML = value.toString();
  else
    button.innerHTML = "💣";
  return button
}

function initializeButtons() {
  const youDiv = document.getElementById("youButtonsDiv");
  const oppDiv = document.getElementById("oppButtonsDiv");

  let row = null;
  for (let i = 0; i < 16; i++) {
    if (i % 4 === 0) {
      row = document.createElement("div");
      row.className = "row justify-content-center align-items-center";
      youDiv.appendChild(row);
    }
    const button = agentCard(i, Player.YOU);
    row.appendChild(button);
    youButtons.push(button);

    button.addEventListener("click", () => {
      if (state !== State.SITUATION) {
        return;
      }
      chooseCard(Number.parseInt(button.dataset["card"]))
    })
  }

  for (let i = 0; i < 16; i++) {
    if (i % 4 === 0) {
      row = document.createElement("div");
      row.className = "row justify-content-center align-items-center";
      oppDiv.appendChild(row);
    }
    const button = agentCard(i, Player.THEY);
    row.appendChild(button);
    oppButtons.push(button);
  }

  const remainingMissionsDiv = document.getElementById("remainingMissionsDiv") as HTMLDivElement;
  for (let i = 1; i <= 16; i++) {
    const btn = missionButton(i, false);
    missionButtons.push(btn);
    remainingMissionsDiv.appendChild(btn);
  }

}

class GameState {
  white: string;
  black: string;
  whiteCards: number[];
  blackCards: number[];
  whiteScore: number;
  blackScore: number;
  currentMission: number;
  remainingMissions: number[];

  constructor(public obj : {
    white: string,
    black: string,
    whiteCards: number[],
    blackCards: number[],
    whiteScore: number,
    blackScore: number,
    currentMission: number,
    remainingMissions: number[]
  }) {
    this.white = obj.white;
    this.black = obj.black;
    this.whiteCards = obj.whiteCards;
    this.blackCards = obj.blackCards;
    this.whiteScore = obj.whiteScore;
    this.blackScore = obj.blackScore;
    this.currentMission = obj.currentMission;
    this.remainingMissions = obj.remainingMissions;
  }

}

class MissionResult {
  youPlayed: number;
  oppPlayed: number;
  mission: number;
  youScored: number;
  oppScored: number;
  gameOver: boolean;

  constructor(public obj: {
    youPlayed: number,
    oppPlayed: number,
    mission: number,
    youScored: number,
    oppScored: number,
    gameOver: boolean
  }) {
    this.youPlayed = obj.youPlayed;
    this.oppPlayed = obj.oppPlayed;
    this.mission = obj.mission;
    this.youScored = obj.youScored;
    this.oppScored = obj.oppScored;
    this.gameOver = obj.gameOver;
  }
}

function repaintUiForSituation() {
  youButtons.forEach((btn, idx) => {
    btn.disabled = (!(situation.whiteCards.includes(idx)));
  })
  oppButtons.forEach((btn, idx) => {
    btn.disabled = (!(situation.blackCards.includes(idx)));
  })
  document.getElementById("yourScore").innerHTML = `Score: ${situation.whiteScore}`;
  document.getElementById("opponentsScore").innerHTML = `Score: ${situation.blackScore}`;

  missionButtons[situation.currentMission - 1].disabled = true;
  missionInfoP.innerHTML = "Current mission: ";
  missionInfoP.appendChild(missionButton(situation.currentMission, false));
}

function updateUiForResult(result: MissionResult) {
  state = State.RESULT;

  repaintUiForSituation();

  oppButtons[result.oppPlayed].classList.add("their-selected");

  let scoreMessage;
  if (result.youScored > 0)
    scoreMessage = `You scored ${result.youScored}`;
  else if (result.oppScored > 0)
    scoreMessage = `${situation.black} scored ${result.oppScored}`;
  else
    scoreMessage = "Drawn round...";

  youPlayedDiv.innerHTML = "";
  youPlayedDiv.appendChild(agentCard(result.youPlayed, Player.YOU));

  oppPlayedDiv.innerHTML = "";
  oppPlayedDiv.appendChild(agentCard(result.oppPlayed, Player.THEY));

  messageP.innerHTML = scoreMessage;

  if (result.gameOver) {
    if (situation.whiteScore > situation.blackScore)
      scoreP.innerHTML = "You won!";
    else if (situation.whiteScore < situation.blackScore)
      scoreP.innerHTML = `${situation.black} won!`;
    else
      scoreP.innerHTML = "Draw!";
  }
}

function chooseCard(card: number) {
  if (state !== State.SITUATION) {
    messageP.innerHTML = "Please wait...";
  }
  const button = youButtons[card];
  button.classList.add("our-selected");

  ws.send(JSON.stringify({"msgType": "card", "card": card}))

  state = State.WAITING_FOR_OPPONENT;
}

initializeButtons();

let situation: GameState = null;

const url = new URL(window.location.href);
url.protocol = 'ws:';
url.pathname = '/ws';
url.searchParams.set('whoami', 'Joanna');
url.searchParams.set('white', 'yes');
const ws = new WebSocket(url.toString());

ws.addEventListener("message", (event) => {
  const data = JSON.parse(event.data);
  console.log(data);

  if (data["msgType"] === "situation") {
    // about to make a play
    situation = new GameState(data["situation"]);
    nextMissionBtn.hidden = false;

    if (situation.whiteCards.length === 16) {
      nextMissionBtn.classList.add("btn-warning");
      nextMissionBtn.innerText = "Start Game";
    } else {
      nextMissionBtn.innerText = "Next Mission";
      nextMissionBtn.classList.remove("btn-warning");
    }

    nextMissionBtn.addEventListener("click", () => {
      state = State.SITUATION;
      repaintUiForSituation();
      youPlayedDiv.innerHTML = "";
      oppPlayedDiv.innerHTML = "";
      messageP.innerHTML = "Select an agent...";
      nextMissionBtn.hidden = true;
    });

  } else if (data["msgType"] === "result") {
    // both sides have made a play, let's see the result
    situation = new GameState(data["situation"]);
    const result = new MissionResult(data["result"]);
    console.log(result);
    updateUiForResult(result);
  }
})

ws.addEventListener("close", (event) => {
  console.log(event);
  alert("You have been disconnected from the game");
})

document.addEventListener("keypress", (event) => {
  const shortcuts = "0123456789abcdef";
  if (state === State.SITUATION) {
    if (shortcuts.includes(event.key)) {
      const idx = shortcuts.indexOf(event.key);
      youButtons[idx].click();
    }
  }

  if (nextMissionBtn.hidden) {
    return;
  }
  if (event.key === "Enter") {
    nextMissionBtn.click();
  }
})
