import "bootstrap/dist/css/bootstrap.min.css";
import { render } from "preact";
import { TournamentsView } from "./TournamentsView";

const root = document.getElementById("tournaments-app");
if (root) {
  render(<TournamentsView />, root);
}
