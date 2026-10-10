import { view } from "../state";
import { Lobby } from "./Lobby";
import { GameView } from "./Game";
import { ChallengeModal } from "./ChallengeModal";
import { GameOverOverlay } from "./GameOverOverlay";
import { ReconnectOverlay } from "./ReconnectOverlay";
import { NotificationPrompt } from "./NotificationPrompt";

export const App = () => {
  return (
    <div class="container justify-content-center align-items-center">
      <NotificationPrompt />
      {view.value === "lobby" ? <Lobby /> : <GameView />}
      <ChallengeModal />
      <GameOverOverlay />
      <ReconnectOverlay />
    </div>
  );
};
