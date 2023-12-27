const youButtons: HTMLButtonElement[] = [];
const oppButtons: HTMLButtonElement[] = [];

const messageP = document.getElementById("message") as HTMLParagraphElement;
const scoreP = document.getElementById("score") as HTMLParagraphElement;

enum State {
  SITUATION,
  RESULT,
}

let state = State.SITUATION;

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
      button.classList.add("our-selected");
      sendCard(Number.parseInt(button.dataset["card"]))
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
}

class Situation {
  yourCards: number[];
  opponentsCards: number[];
  yourScore: number;
  opponentsScore: number;
  currentMission: number;
  remainingMissions: Set<number>;
}

class MissionResult {
  youPlayed: number;
  oppPlayed: number;
  mission: number;
  youScored: number;
  oppScored: number;

  constructor(public obj : {youPlayed: number, oppPlayed: number, mission: number, youScored: number, oppScored: number}) {
    this.youPlayed = obj.youPlayed;
    this.oppPlayed = obj.oppPlayed;
    this.mission = obj.mission;
    this.youScored = obj.youScored;
    this.oppScored = obj.oppScored;
  }

  toString(): string {
    return `You played ${this.youPlayed}, Opponent played ${this.oppPlayed}, mission ${this.mission}, you scored ${this.youScored}, opponent scored ${this.oppScored}`
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
}

function updateUiForResult(result: MissionResult) {
  state = State.RESULT;
  messageP.innerHTML = result.toString();

}

function sendCard(card) {
  ws.send(JSON.stringify({"msgType": "card", "card": card}))
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
    const situation = data["situation"] as Situation;
    console.log(situation);
    updateUiForSituation(situation);
  } else if (data["msgType"] === "result") {
    const result = new MissionResult(data["result"]);
    console.log(result);
    updateUiForResult(result);
  }
})
