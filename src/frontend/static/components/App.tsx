import { view } from "../state";
import { Lobby } from "./Lobby";
import { GameView } from "./Game";
import { ChallengeModal } from "./ChallengeModal";
import { GameOverOverlay } from "./GameOverOverlay";
import { ReconnectOverlay } from "./ReconnectOverlay";

export const App = () => {
  return (
    <div class="container justify-content-center align-items-center">
      {view.value === "lobby" ? <Lobby /> : <GameView />}
      <ChallengeModal />
      <GameOverOverlay />
      <ReconnectOverlay />
    </div>
  );
};
