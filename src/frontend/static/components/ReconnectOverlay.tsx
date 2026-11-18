import { wsConnected } from "../state";

export const ReconnectOverlay = () => {
  if (wsConnected.value) return null;
  return (
    <div
      class="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center"
      style="background: rgba(0,0,0,0.75); z-index: 1050;"
    >
      <div class="text-center">
        <div class="spinner-border mb-3" role="status" />
        <p>Connection lost — reconnecting…</p>
        <p class="text-muted small">
          Games against another player have a 5 minute grace period.
          Against a computer, your game will wait on this device until you return.
        </p>
      </div>
    </div>
  );
};
