import { signal } from "@preact/signals";

export type PlayerStatus = {
  name: string;
  online: boolean;
  inGame: boolean;
  isComputer: boolean;
};

export type MissionResultData = {
  youPlayed: number;
  oppPlayed: number;
  mission: number;
  youScored: number;
  oppScored: number;
  gameOver: boolean;
};

export type GameStateData = {
  white: string;
  black: string;
  whiteCards: number[];
  blackCards: number[];
  whiteScore: number;
  blackScore: number;
  currentMission: number | null;
  remainingMissions: number[];
};

export type GameSignal = {
  opponent: string | null;
  situation: GameStateData | null;
  result: MissionResultData | null;
  over: boolean;
  winner: string | null;
  reason: string | null;
  opponentStatus: "online" | "disconnected" | null;
  turn: number;
  awaitingMove: boolean;
};

export const username = signal<string | null>(
  typeof localStorage === "undefined" ? null : localStorage.getItem("username"),
);
export const players = signal<PlayerStatus[]>([]);
export const pendingChallengeTo = signal<string | null>(null);
export const incomingChallenge = signal<string | null>(null);
export const toast = signal<string | null>(null);
export const view = signal<"lobby" | "game">("lobby");
export const wsConnected = signal(false);
export const game = signal<GameSignal | null>(null);

export const showToast = (msg: string) => {
  toast.value = msg;
  window.setTimeout(() => {
    if (toast.value === msg) toast.value = null;
  }, 4000);
};

export const newGame = (opponent: string | null): GameSignal => ({
  opponent,
  situation: null,
  result: null,
  over: false,
  winner: null,
  reason: null,
  opponentStatus: null,
  turn: 0,
  awaitingMove: false,
});

export const setUsername = (name: string | null) => {
  username.value = name;
  try {
    if (name) localStorage.setItem("username", name);
    else localStorage.removeItem("username");
  } catch (_) {
    // ignore
  }
};
