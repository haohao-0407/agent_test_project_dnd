import { useState } from "react";
import { joinSession, type AuthSession, type JoinRole } from "../api/client";

type JoinScreenProps = {
  title?: string;
  onJoined: (session: AuthSession) => void;
};

export function JoinScreen({ title = "Join table", onJoined }: JoinScreenProps) {
  const [joiningRole, setJoiningRole] = useState<JoinRole | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleJoin(role: JoinRole) {
    setJoiningRole(role);
    setError(null);
    try {
      const session = await joinSession(role);
      onJoined(session);
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Could not join the table.");
    } finally {
      setJoiningRole(null);
    }
  }

  return (
    <main className="app-shell join-shell">
      <section className="join-panel">
        <p className="eyebrow">DND Agent</p>
        <h1>{title}</h1>
        <div className="join-actions">
          <button type="button" disabled={joiningRole !== null} onClick={() => void handleJoin("player")}>
            {joiningRole === "player" ? "Joining..." : "Join as player"}
          </button>
          <button type="button" disabled={joiningRole !== null} onClick={() => void handleJoin("dm")}>
            {joiningRole === "dm" ? "Joining..." : "Join as DM"}
          </button>
        </div>
        {error ? <p className="join-error">{error}</p> : null}
      </section>
    </main>
  );
}
