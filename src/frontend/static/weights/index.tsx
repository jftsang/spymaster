import { render } from "preact";
import { WeightsView } from "./WeightsView";

const root = document.getElementById("weights-app");
if (root) {
  render(<WeightsView />, root);
}
