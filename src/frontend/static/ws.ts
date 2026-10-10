import { wsConnected } from "./state";
import { handleWsMessage } from "./messages";

let ws: WebSocket | null = null;
let reconnectTimer: number | null = null;
let backoff = 500;
const MAX_BACKOFF = 5000;

const resolveWsUrl = () => {
  const url = new URL(window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws";
  return url.toString();
};

const clearTimer = () => {
  if (reconnectTimer != null) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
};

const scheduleReconnect = () => {
  clearTimer();
  reconnectTimer = window.setTimeout(() => {
    connectWs();
  }, backoff);
  backoff = Math.min(backoff * 2, MAX_BACKOFF);
};

export const sendWs = (msg: any) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
};

export const connectWs = () => {
  clearTimer();
  try {
    ws = new WebSocket(resolveWsUrl());
  } catch (e) {
    scheduleReconnect();
    return;
  }

  ws.addEventListener("open", () => {
    wsConnected.value = true;
    backoff = 500;
    // If username is already known, auto-login on reconnect
    try {
      const stored = localStorage.getItem("username");
      if (stored) {
        sendWs({ msgType: "login", username: stored });
      }
    } catch (_) {
      // ignore
    }
  });

  ws.addEventListener("message", (ev) => {
    try {
      const data = JSON.parse(ev.data as string);
      handleWsMessage(data);
    } catch (_) {
      // ignore malformed
    }
  });

  ws.addEventListener("close", () => {
    wsConnected.value = false;
    scheduleReconnect();
  });

  ws.addEventListener("error", () => {
    try {
      ws?.close();
    } catch (_) {
      // ignore
    }
  });
};
