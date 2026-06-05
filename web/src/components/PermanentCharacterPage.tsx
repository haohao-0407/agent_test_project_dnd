import { useEffect, useState } from "react";
import { getPermanentCharacters } from "../api/client";
import type { Character } from "../api/types";
import { CharacterCardsPage } from "./CharacterCardsPage";

export function PermanentCharacterPage() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPermanentCharacters()
      .then((payload) => setCharacters(payload.characters))
      .catch((apiError: Error) => setError(apiError.message));
  }, []);

  if (error) {
    return <main className="app-shell">{error}</main>;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Character Library</p>
          <h1>永久角色卡</h1>
        </div>
        <div className="session-strip">
          <a className="nav-link" href="/">返回战棋</a>
        </div>
      </header>
      <CharacterCardsPage
        mode="permanent"
        characters={characters}
        currentUserId="library"
        onCharactersChange={setCharacters}
      />
    </main>
  );
}
