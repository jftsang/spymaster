import { incomingChallenge } from "../state";
import { sendWs } from "../ws";

export const ChallengeModal = () => {
  const from = incomingChallenge.value;
  if (!from) return null;

  const respond = (accept: boolean) => {
    sendWs({ msgType: accept ? "accept" : "decline", from });
    incomingChallenge.value = null;
  };

  return (
    <div class="modal d-block" style="background: rgba(0,0,0,0.6);" tabIndex={-1}>
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content bg-dark text-light border-secondary">
          <div class="modal-header">
            <h5 class="modal-title">Challenge</h5>
          </div>
          <div class="modal-body">
            <p>
              <strong>{from}</strong> has challenged you to a game.
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" onClick={() => respond(false)}>
              Decline
            </button>
            <button class="btn btn-success" onClick={() => respond(true)}>
              Accept
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
