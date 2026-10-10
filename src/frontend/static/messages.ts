import {
  username,
  players,
  pendingChallengeTo,
  incomingChallenge,
  toast,
  view,
  game,
  gameOverAcknowledged,
  newGame,
  showToast,
  setUsername,
  PlayerStatus,
  GameStateData,
  MissionResultData,
} from "./state";
import { notify } from "./notifications";

export const handleWsMessage = (data: any) => {
  const st: GameStateData | null = data.situation ?? null;
  const res: MissionResultData | null = data.result ?? null;

  switch (data.msgType) {
    case "loginOk":
      setUsername(data.username);
      view.value = "lobby";
      toast.value = null;
      return;

    case "loginFailed":
      setUsername(null);
      showToast(data.reason ?? "Login failed");
      return;

    case "players":
      players.value = (data.players ?? []) as PlayerStatus[];
      return;

    case "challenge":
      incomingChallenge.value = data.from ?? null;
      notify("New challenge", `${data.from} challenged you to a game.`);
      return;

    case "challengeDeclined":
      pendingChallengeTo.value = null;
      showToast(`${data.from} declined the challenge`);
      notify("Challenge declined", `${data.from} declined your challenge.`);
      return;

    case "challengeWithdrawn":
      if (incomingChallenge.value === data.from) incomingChallenge.value = null;
      showToast(`${data.from} withdrew the challenge`);
      return;

    case "challengeRefused":
      pendingChallengeTo.value = null;
      showToast(data.reason ?? `${data.from} cannot play right now`);
      return;

    case "gameStart": {
      const accepted = pendingChallengeTo.value;
      game.value = newGame(data.opponent ?? null);
      gameOverAcknowledged.value = false;
      view.value = "game";
      toast.value = null;
      pendingChallengeTo.value = null;
      incomingChallenge.value = null;
      if (accepted) {
        notify("Challenge accepted", `${accepted} accepted your challenge.`);
      }
      return;
    }

    case "situation": {
      const base = game.value ?? newGame(st?.black ?? null);
      game.value = {
        ...base,
        situation: st,
        over: false,
        turn: base.turn + 1,
        awaitingMove: true,
      };
      view.value = "game";
      return;
    }

    case "result": {
      const base = game.value ?? newGame(st?.black ?? null);
      game.value = {
        ...base,
        situation: st,
        result: res,
        over: res?.gameOver ?? base.over,
        awaitingMove: false,
      };
      view.value = "game";
      if (res) {
        const opponent = st?.black ?? base.opponent ?? "Your opponent";
        let scored: string;
        if (res.youScored > 0) scored = `You scored ${res.youScored}.`;
        else if (res.oppScored > 0) scored = `${opponent} scored ${res.oppScored}.`;
        else scored = "Drawn round.";
        notify(
          "Mission result",
          `You played ${res.youPlayed}. ${opponent} played ${res.oppPlayed}. ${scored}.`,
        );
      }
      return;
    }

    case "gameOver": {
      const base = game.value ?? newGame(null);
      game.value = {
        ...base,
        over: true,
        winner: data.winner ?? null,
        reason: data.reason ?? null,
        awaitingMove: false,
        opponentStatus: null,
      };
      view.value = "game";
      return;
    }

    case "opponentDisconnected":
      if (game.value) {
        game.value = { ...game.value, opponentStatus: "disconnected" };
      }
      return;

    case "opponentReconnected":
      if (game.value) {
        game.value = { ...game.value, opponentStatus: "online" };
      }
      return;

    default:
      return;
  }
};
