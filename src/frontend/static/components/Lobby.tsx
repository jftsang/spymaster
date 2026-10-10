import { useState } from "preact/hooks";
import { JSX } from "preact";
import {
  username,
  players,
  pendingChallengeTo,
  toast,
  setUsername,
  PlayerStatus,
} from "../state";
import { sendWs } from "../ws";

const LoginForm = () => {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const submit = (ev: Event) => {
    ev.preventDefault();
    const value = name.trim();
    if (!value) {
      setError("Please choose a username");
      return;
    }
    setSubmitted(true);
    setUsername(value);
    sendWs({ msgType: "login", username: value });
  };

  return (
    <form class="row g-2 align-items-center mb-3" onSubmit={submit}>
      <div class="col-auto">
        <input
          class="form-control"
          placeholder="Username"
          value={name}
          onInput={(ev) => setName((ev.target as HTMLInputElement).value)}
        />
      </div>
      <div class="col-auto">
        <button class="btn btn-primary" type="submit">
          {submitted ? "Logging in…" : "Log in"}
        </button>
      </div>
      {error && <div class="col-auto text-danger">{error}</div>}
    </form>
  );
};

const PlayerRow = ({ player, me }: { player: PlayerStatus; me: string | null }) => {
  const isMe = player.name === me;
  const pending = pendingChallengeTo.value === player.name;
  const disabled = isMe || player.inGame || pending;

  let status: JSX.Element | null = null;
  if (player.inGame) status = <span class="badge bg-warning text-dark">In game</span>;
  else if (player.isComputer)
    status = <span class="badge bg-info text-dark">Computer</span>;

  const challenge = () => {
    if (disabled) return;
    sendWs({ msgType: "challenge", target: player.name });
  };

  return (
    <li class="list-group-item bg-dark text-light d-flex justify-content-between align-items-center">
      <span>
        {player.name} {isMe && <span class="text-muted">(you)</span>} {status}
      </span>
      {!isMe && (
        <button
          class="btn btn-sm btn-success"
          disabled={disabled}
          onClick={challenge}
        >
          {pending ? "Challenging…" : "Challenge"}
        </button>
      )}
    </li>
  );
};

export const Lobby = () => {
  const me = username.value;
  return (
    <div class="container py-4">
      <h2 class="mb-3">Spymaster Lobby</h2>
      {!me && <LoginForm />}
      {toast.value && <div class="alert alert-info">{toast.value}</div>}
      {me && (
        <div class="card bg-dark border-secondary">
          <div class="card-header">Players online</div>
          <ul class="list-group list-group-flush">
            {players.value.map((p) => (
              <PlayerRow key={p.name} player={p} me={me} />
            ))}
          </ul>
        </div>
      )}
      <div class="mt-3">
        <a href="/help" target="_blank" class="link-light">
          How to play
        </a>
      </div>
    </div>
  );
};
