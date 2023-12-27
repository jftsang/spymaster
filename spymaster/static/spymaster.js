const youDiv = document.getElementById("youButtonsDiv");
const youButtons = [];

let row = null;
for (let i = 0; i < 16; i++) {
  if (i % 4 === 0) {
    row = document.createElement("div");
    row.className = "row justify-content-center align-items-center";
    youDiv.appendChild(row);
  }
  const button = document.createElement("button");
  button.className = "btn btn-primary agentcard";
  button.innerHTML = i.toString();
  row.appendChild(button);
  youButtons.push(button);
}

const oppDiv = document.getElementById("oppButtonsDiv");
const oppButtons = [];

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

const url = new URL(window.location.href);
url.protocol = 'ws:';
url.pathname = '/ws';
const ws = new WebSocket(url.toString());

function updateUiForSituation(situation) {
  youButtons.forEach((btn) => {
    btn.disabled = true;
  })
  situation.yourCards.forEach((card) => {
    youButtons[card].disabled = false;
  })
  oppButtons.forEach((btn) => {
    btn.disabled = true;
  })
  situation.opponentsCards.forEach((card) => {
    oppButtons[card].disabled = false;
  })
}

ws.addEventListener("message", (event) => {
  const data = JSON.parse(event.data);
  if (data["situation"] !== null) {
    const situation = data["situation"]
    console.log(situation);
    updateUiForSituation(situation);
  }
  console.log(data);
})