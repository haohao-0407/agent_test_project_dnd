import { useEffect, useState } from "react";
import { getState, moveToken, rollDice, sendChat } from "../api/client";
import type { DiceResult, GameState } from "../api/types";
import { CharacterSheet } from "./CharacterSheet";
import { ChatPanel } from "./ChatPanel";
import { DicePanel } from "./DicePanel";
import { MapView } from "./MapView";

export function TabletopApp() {
  const [state, setState] = useState<GameState | null>(null);
  const [selectedTokenId, setSelectedTokenId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getState()
      .then(setState)
      .catch((apiError: Error) => setError(apiError.message));
  }, []);

  async function handleMoveToken(x: number, y: number) {
    if (!selectedTokenId) return;
    const response = await moveToken(selectedTokenId, x, y);
    setState(response.state);
    setSelectedTokenId(null);
  }

  async function handleRoll(input: Parameters<typeof rollDice>[0]): Promise<DiceResult> {
    const response = await rollDice(input);
    setState(response.state);
    return response.result;
  }

  async function handleSend(message: string) {
    const response = await sendChat({ speaker: "player", message });
    setState(response.state);
  }

  if (error) {
    return <main className="app-shell">{error}</main>;
  }

  if (!state) {
    return <main className="app-shell">Loading tabletop...</main>;
  }

  const current = state.tokens.find((token) => token.id === state.session.currentTurn);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">DND Agent</p>
          <h1>{state.session.title}</h1>
        </div>
        <div className="session-strip" aria-label="session status">
          <span>{state.session.mode}</span>
          <span>Round {state.session.round}</span>
          <span>Turn {current?.name || state.session.currentTurn}</span>
        </div>
      </header>

      <section className="workspace">
        <MapView
          map={state.map}
          tokens={state.tokens}
          selectedTokenId={selectedTokenId}
          onSelectToken={setSelectedTokenId}
          onMoveToken={handleMoveToken}
        />
        <CharacterSheet characters={state.characters} />
        <ChatPanel events={state.events} onSend={handleSend} />
        <DicePanel selectedTokenId={selectedTokenId} onRoll={handleRoll} />
      </section>
    </main>
  );
}
