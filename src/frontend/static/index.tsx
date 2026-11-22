import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import { render } from "preact";
import { App } from "./components/App";
import { connectWs } from "./ws";

const root = document.getElementById("app");
if (root) {
  render(<App />, root);
}

connectWs();

type CapacitorWindow = Window & {
  Capacitor?: { isNativePlatform?: () => boolean };
};

if ("serviceWorker" in navigator) {
  const native =
    (window as CapacitorWindow).Capacitor?.isNativePlatform?.() ?? false;
  if (!native) {
    // Kept non-literal so Parcel does not try to bundle the service worker;
    // it is served by the explicit /sw.js route with a root scope.
    const swUrl = "/sw" + ".js";
    window.addEventListener("load", () => {
      void navigator.serviceWorker.register(swUrl).catch(() => {
        // Registration is best-effort; the game still works without it.
      });
    });
  }
}
