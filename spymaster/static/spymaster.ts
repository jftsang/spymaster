const youButtons: HTMLButtonElement[] = [];
const oppButtons: HTMLButtonElement[] = [];

const missionInfoP = document.getElementById("missionInfo") as HTMLParagraphElement;
const messageP = document.getElementById("message") as HTMLParagraphElement;
const scoreP = document.getElementById("score") as HTMLParagraphElement;
const nextMissionBtn = document.getElementById("nextMissionBtn") as HTMLButtonElement;

enum State {
  SITUATION,
  WAITING_FOR_OPPONENT,
  RESULT,
  GAME_OVER,
}

let state: State = State.RESULT;

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
    const button = document.createElement("button");
    button.className = "btn btn-primary agentcard";
    button.dataset["card"] = i.toString();
    button.innerHTML = i.toString();
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
    const button = document.createElement("button");
    button.className = "btn btn-danger agentcard";
    button.innerHTML = i.toString();
    row.appendChild(button);
    oppButtons.push(button);
  }

  nextMissionBtn.classList.add("btn-warning");
  nextMissionBtn.innerText = "Start Game";
}

class Situation {
  yourCards: number[];
  opponentsCards: number[];
  yourScore: number;
  opponentsScore: number;
  currentMission: number;
  remainingMissions: Set<number>;

  constructor(public obj: {
    yourCards: number[],
    opponentsCards: number[],
    yourScore: number,
    opponentsScore: number,
    currentMission: number,
    remainingMissions: Set<number>
  }) {
    this.yourCards = obj.yourCards;
    this.opponentsCards = obj.opponentsCards;
    this.yourScore = obj.yourScore;
    this.opponentsScore = obj.opponentsScore;
    this.currentMission = obj.currentMission;
    this.remainingMissions = obj.remainingMissions;
  }

  toString() {
    return `Mission value: ${this.currentMission}`;
  }
}

class MissionResult {
  youPlayed: number;
  oppPlayed: number;
  mission: number;
  youScored: number;
  oppScored: number;

  constructor(public obj: {
    youPlayed: number,
    oppPlayed: number,
    mission: number,
    youScored: number,
    oppScored: number
  }) {
    this.youPlayed = obj.youPlayed;
    this.oppPlayed = obj.oppPlayed;
    this.mission = obj.mission;
    this.youScored = obj.youScored;
    this.oppScored = obj.oppScored;
  }

  toString(): string {
    if (this.youScored > 0)
      return `You scored ${this.youScored}`;
    else if (this.oppScored > 0)
      return `Opponent scored ${this.oppScored}`;
    else
      return "Drawn round";
  }
}

function updateUiForSituation(situation: Situation) {
  state = State.SITUATION;
  youButtons.forEach((btn, idx) => {
    btn.disabled = (!(situation.yourCards.includes(idx)));
  })
  oppButtons.forEach((btn, idx) => {
    btn.disabled = (!(situation.opponentsCards.includes(idx)));
  })
  document.getElementById("yourScore").innerHTML = `Score: ${situation.yourScore}`;
  document.getElementById("opponentsScore").innerHTML = `Score: ${situation.opponentsScore}`;

  missionInfoP.innerHTML = situation.toString();
  messageP.innerHTML = "Select an agent...";
  nextMissionBtn.hidden = true;
}

function updateUiForResult(result: MissionResult) {
  state = State.RESULT;
  oppButtons[result.oppPlayed].classList.add("their-selected");
  messageP.innerHTML = result.toString();


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


const url = new URL(window.location.href);
url.protocol = 'ws:';
url.pathname = '/ws';
const ws = new WebSocket(url.toString());

ws.addEventListener("message", (event) => {
  const data = JSON.parse(event.data);
  console.log(data);

  if (data["msgType"] === "situation") {
    // about to make a play
    const situation = new Situation(data["situation"]);
    console.log(situation);
    nextMissionBtn.hidden = false;
    nextMissionBtn.innerText = "Next Mission";
    nextMissionBtn.classList.remove("btn-warning");

    nextMissionBtn.addEventListener("click", () => {
      updateUiForSituation(situation);
    });
  } else if (data["msgType"] === "result") {
    // both sides have made a play, let's see the result
    const result = new MissionResult(data["result"]);
    console.log(result);
    updateUiForResult(result);
  }
})

ws.addEventListener("close", (event) => {
  console.log(event);
  // alert("Disconnected");
})
