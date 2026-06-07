import { useEffect, useState } from "react";
import { ApiError, getPermanentCharacters, logout, me, type AuthSession } from "../api/client";
import type { Character } from "../api/types";
import { CharacterCardsPage } from "./CharacterCardsPage";
import { JoinScreen } from "./JoinScreen";

export function PermanentCharacterPage() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [identity, setIdentity] = useState<AuthSession | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    me()
      .then((session) => {
        setIdentity(session);
        return loadCharacters();
      })
      .catch((apiError: Error) => {
        if (apiError instanceof ApiError && apiError.status === 401) {
          setIdentity(null);
          return;
        }
        setError(apiError.message);
      })
      .finally(() => setAuthChecked(true));
  }, []);

  async function loadCharacters() {
    const payload = await getPermanentCharacters();
    setCharacters(payload.characters);
  }

  async function handleJoined(session: AuthSession) {
    setIdentity(session);
    await loadCharacters();
  }

  async function handleLogout() {
    await logout();
    setIdentity(null);
    setCharacters([]);
  }

  if (error) {
    return <main className="app-shell">{error}</main>;
  }

  if (!authChecked) {
    return <main className="app-shell">Loading library...</main>;
  }

  if (!identity) {
    return <JoinScreen title="Join to edit the library" onJoined={(session) => void handleJoined(session)} />;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Character Library</p>
          <h1>永久角色卡</h1>
        </div>
        <div className="session-strip">
          <span>{identity.player?.displayName || identity.userId}</span>
          <a className="nav-link" href="/">返回战棋</a>
          <button type="button" onClick={() => void handleLogout()}>
            Logout
          </button>
        </div>
      </header>
      <CharacterCardsPage
        mode="permanent"
        characters={characters}
        currentUserId={identity.userId}
        currentUser={identity.player || undefined}
        onCharactersChange={setCharacters}
      />
    </main>
  );
}
