import { useEffect, useState } from "react";
import {
  advanceToPlayerTurn,
  confirmPendingAction,
  declinePendingAction,
  endTurn,
  getState,
  moveToken,
  sendChat,
  startCombat,
  updateMap
} from "../api/client";
import type { GameState, MapEditTool, Terrain } from "../api/types";
import { CharacterCardsPage } from "./CharacterCardsPage";
import { CharacterSheet } from "./CharacterSheet";
import { ChatPanel } from "./ChatPanel";
import { CombatPanel } from "./CombatPanel";
import { MapView } from "./MapView";

export function TabletopApp() {
  const [state, setState] = useState<GameState | null>(null);
  const [selectedTokenId, setSelectedTokenId] = useState<string | null>(null);
  const [currentUserId, setCurrentUserId] = useState("player-kael");
  const [mapEditTool, setMapEditTool] = useState<MapEditTool>("move");
  const [activePage, setActivePage] = useState<"tabletop" | "characters">("tabletop");
  const [isAutoAdvancing, setIsAutoAdvancing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getState()
      .then((nextState) => {
        setState(nextState);
        if (nextState.players.length > 0) {
          setCurrentUserId(nextState.players[0].id);
        }
      })
      .catch((apiError: Error) => setError(apiError.message));
  }, []);

  useEffect(() => {
    if (!state || isAutoAdvancing || !state.combat.active) return;
    const currentUser = state.players.find((player) => player.id === currentUserId) || state.players[0];
    if (!currentUser || currentUser.role === "dm") return;

    const currentActorId = state.combat.initiativeOrder[state.combat.turnIndex]?.actorId;
    const currentToken = state.tokens.find(
      (token) => token.actorId === currentActorId || token.id === currentActorId
    );
    if (!currentToken || currentToken.kind === "player") return;

    setIsAutoAdvancing(true);
    advanceToPlayerTurn({ userId: currentUserId })
      .then((response) => setState(response.state))
      .catch((apiError: Error) => setError(apiError.message))
      .finally(() => setIsAutoAdvancing(false));
  }, [currentUserId, isAutoAdvancing, state]);

  async function handleMoveToken(x: number, y: number) {
    if (!selectedTokenId) return;
    const response = await moveToken(selectedTokenId, x, y, currentUserId);
    setState(response.state);
    setSelectedTokenId(null);
  }

  async function handleSend(message: string) {
    const response = await sendChat({
      speaker: currentUser?.displayName || currentUserId,
      userId: currentUserId,
      message
    });
    setState(response.state);
  }

  async function handleEditMapCell(x: number, y: number) {
    if (!state || currentUser?.role !== "dm" || mapEditTool === "move") return;
    const terrain = state.map.terrain.filter((item) => item.x !== x || item.y !== y);
    const nextTerrain: Terrain[] =
      mapEditTool === "erase" ? terrain : [...terrain, { x, y, type: mapEditTool }];
    const response = await updateMap({
      userId: currentUserId,
      updates: { terrain: nextTerrain }
    });
    setState(response.state);
  }

  async function handleStartCombat() {
    const response = await startCombat({
      userId: currentUserId,
      participantIds: state?.tokens.map((token) => token.actorId || token.id) || null
    });
    setState(response.state);
  }

  async function handleEndTurn() {
    const response = await endTurn({
      userId: currentUserId,
      actorId: state?.combat.active ? state.combat.initiativeOrder[state.combat.turnIndex]?.actorId : null
    });
    setState(response.state);
  }

  async function handleConfirmPending(actionId: string) {
    const response = await confirmPendingAction({ actionId, userId: currentUserId });
    setState(response.state);
  }

  async function handleDeclinePending(actionId: string) {
    const response = await declinePendingAction({ actionId, userId: currentUserId });
    setState(response.state);
  }

  if (error) {
    return <main className="app-shell">{error}</main>;
  }

  if (!state) {
    return <main className="app-shell">Loading tabletop...</main>;
  }

  const current = state.tokens.find((token) => token.id === state.session.currentTurn);
  const currentUser = state.players.find((player) => player.id === currentUserId) || state.players[0];
  const controlledTokenIds =
    currentUser?.role === "dm"
      ? state.tokens.map((token) => token.id)
      : currentUser?.characterId
        ? [currentUser.characterId]
        : [];

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
          <button
            type="button"
            className={activePage === "tabletop" ? "active" : ""}
            onClick={() => setActivePage("tabletop")}
          >
            战棋
          </button>
          <button
            type="button"
            className={activePage === "characters" ? "active" : ""}
            onClick={() => setActivePage("characters")}
          >
            角色卡
          </button>
          <a className="nav-link" href="/characters/permanent">
            永久库
          </a>
          <a className="nav-link" href="/rules">
            Rules
          </a>
          <label className="user-switcher">
            <span>User</span>
            <select
              value={currentUserId}
              onChange={(event) => {
                setCurrentUserId(event.target.value);
                setSelectedTokenId(null);
              }}
            >
              {state.players.map((player) => (
                <option key={player.id} value={player.id}>
                  {player.displayName}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {activePage === "characters" ? (
        <CharacterCardsPage
          state={state}
          currentUserId={currentUserId}
          currentUser={currentUser}
          onStateChange={setState}
        />
      ) : (
        <section className="workspace">
          <MapView
            map={state.map}
            tokens={state.tokens}
            selectedTokenId={selectedTokenId}
            controlledTokenIds={controlledTokenIds}
            mapEditTool={mapEditTool}
            canEditMap={currentUser?.role === "dm"}
            onSelectToken={setSelectedTokenId}
            onMoveToken={handleMoveToken}
            onEditMapCell={handleEditMapCell}
            onMapEditToolChange={setMapEditTool}
          />
          <div className="sheet-stack">
            <CombatPanel
              combat={state.combat}
              pendingActions={state.pendingActions}
              tokens={state.tokens}
              currentUser={currentUser}
              currentUserId={currentUserId}
              onStartCombat={handleStartCombat}
              onEndTurn={handleEndTurn}
              onConfirmPending={handleConfirmPending}
              onDeclinePending={handleDeclinePending}
            />
            <CharacterSheet characters={state.characters} />
          </div>
          <ChatPanel events={state.events} onSend={handleSend} />
        </section>
      )}
    </main>
  );
}
