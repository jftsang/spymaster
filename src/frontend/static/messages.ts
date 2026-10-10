import {
  username,
  players,
  pendingChallengeTo,
  incomingChallenge,
  toast,
  view,
  game,
  newGame,
  showToast,
  setUsername,
  PlayerStatus,
  GameStateData,
  MissionResultData,
} from "./state";

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
      return;

    case "challengeDeclined":
      pendingChallengeTo.value = null;
      showToast(`${data.from} declined the challenge`);
      return;

    case "challengeRefused":
      pendingChallengeTo.value = null;
      showToast(data.reason ?? `${data.from} cannot play right now`);
      return;

    case "gameStart":
      game.value = newGame(data.opponent ?? null);
      view.value = "game";
      toast.value = null;
      pendingChallengeTo.value = null;
      incomingChallenge.value = null;
      return;

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
