import { render } from "preact";
import { App } from "./components/App";
import { connectWs } from "./ws";

const root = document.getElementById("app");
if (root) {
  render(<App />, root);
}

connectWs();
