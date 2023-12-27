const youDiv = document.getElementById("youButtonsDiv");
const youButtons = [];

for (let i = 0; i < 16; i++) {
  if (i % 4 === 0) {
    const row = document.createElement("div");
    row.className = "row";
    youDiv.appendChild(row);
  }
  const button = document.createElement("button");
  button.className = "btn btn-primary agentcard";
  button.innerHTML = i.toString();
  youDiv.appendChild(button);
  youButtons.push(button);
}

const oppDiv = document.getElementById("oppButtonsDiv");
const oppButtons = [];

for (let i = 0; i < 16; i++) {
  if (i % 4 === 0) {
    const row = document.createElement("div");
    row.className = "row";
    oppDiv.appendChild(row);
  }
  const button = document.createElement("button");
  button.className = "btn btn-danger agentcard";
  button.innerHTML = i.toString();
  oppDiv.appendChild(button);
  oppButtons.push(button);
}
