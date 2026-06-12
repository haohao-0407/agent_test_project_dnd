import { useEffect, useState } from "react";
import {
  advanceToPlayerTurn,
  ApiError,
  confirmPendingAction,
  declinePendingAction,
  endCombat,
  endTurn,
  logout,
  me,
  moveToken,
  sendChat,
  startCombat,
  stateSocketUrl,
  updateMap
} from "../api/client";
import type { AuthSession } from "../api/client";
import type { GameState, MapEditTool, Player, Terrain } from "../api/types";
import { AdventureSetup } from "./AdventureSetup";
import { CharacterCardsPage } from "./CharacterCardsPage";
import { CharacterSheet } from "./CharacterSheet";
import { ChatPanel } from "./ChatPanel";
import { CombatPanel } from "./CombatPanel";
import { DmSceneBrowser } from "./DmSceneBrowser";
import { ExplorationScene } from "./ExplorationScene";
import { JoinScreen } from "./JoinScreen";
import { MapBackgroundEditor } from "./MapBackgroundEditor";
import { MapView } from "./MapView";

type Identity = {
  userId: string;
  role: string;
  player?: Player | null;
};

export function TabletopApp() {
  const [state, setState] = useState<GameState | null>(null);
  const [selectedTokenId, setSelectedTokenId] = useState<string | null>(null);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [mapEditTool, setMapEditTool] = useState<MapEditTool>("move");
  const [activePage, setActivePage] = useState<"tabletop" | "characters">("tabletop");
  const [isAutoAdvancing, setIsAutoAdvancing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentUser = state && identity
    ? state.players.find((player) => player.id === identity.userId) || identity.player || state.players[0]
    : null;
  const currentUserId = identity?.userId || "";

  useEffect(() => {
    me()
      .then(applySession)
      .catch((apiError: Error) => {
        if (apiError instanceof ApiError && apiError.status === 401) {
          setIdentity(null);
          setState(null);
          return;
        }
        setError(apiError.message);
      })
      .finally(() => setAuthChecked(true));
  }, []);

  useEffect(() => {
    if (!identity) return;
    let stopped = false;
    let retryId: number | null = null;
    let socket: WebSocket | null = null;

    const connect = () => {
      const url = stateSocketUrl();
      if (!url) return;
      socket = new WebSocket(url);
      socket.onmessage = (event) => {
        if (stopped) return;
        try {
          const payload = JSON.parse(String(event.data)) as { type?: string; state?: GameState };
          if (payload.type === "state" && payload.state) {
            setState(payload.state);
          }
        } catch {
          // Ignore malformed socket payloads; the next state message will recover the UI.
        }
      };
      socket.onclose = (event) => {
        if (stopped) return;
        if (event.code === 1008) {
          setIdentity(null);
          setState(null);
          return;
        }
        retryId = window.setTimeout(connect, 1500);
      };
      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();
    return () => {
      stopped = true;
      if (retryId !== null) {
        window.clearTimeout(retryId);
      }
      socket?.close();
    };
  }, [identity?.userId]);

  useEffect(() => {
    if (!identity || !state || isAutoAdvancing || !state.combat.active) return;
    const currentUser = state.players.find((player) => player.id === identity.userId) || identity.player || state.players[0];
    if (!currentUser || currentUser.role === "dm") return;

    const currentActorId = state.combat.initiativeOrder[state.combat.turnIndex]?.actorId;
    const currentToken = state.tokens.find(
      (token) => token.actorId === currentActorId || token.id === currentActorId
    );
    if (!currentToken || currentToken.kind === "player") return;

    setIsAutoAdvancing(true);
    advanceToPlayerTurn()
      .then((response) => setState(response.state))
      .catch((apiError: Error) => setError(apiError.message))
      .finally(() => setIsAutoAdvancing(false));
  }, [identity, isAutoAdvancing, state]);

  function applySession(session: AuthSession) {
    setIdentity({
      userId: session.userId,
      role: session.role,
      player: session.player
    });
    setState(session.state);
    setSelectedTokenId(null);
    setError(null);
  }

  async function handleLogout() {
    await logout();
    setIdentity(null);
    setState(null);
    setSelectedTokenId(null);
  }

  async function handleMoveToken(x: number, y: number) {
    if (!selectedTokenId) return;
    const response = await moveToken(selectedTokenId, x, y);
    setState(response.state);
    setSelectedTokenId(null);
  }

  async function handleSend(message: string) {
    try {
      const response = await sendChat({
        speaker: currentUser?.displayName || identity?.userId || "player",
        message
      });
      setState(response.state);
    } catch (apiError) {
      if (apiError instanceof ApiError && apiError.status === 401) {
        setIdentity(null);
        setState(null);
      }
      throw apiError;
    }
  }

  async function handleEditMapCell(x: number, y: number) {
    if (!state || currentUser?.role !== "dm" || mapEditTool === "move") return;
    const terrain = state.map.terrain.filter((item) => item.x !== x || item.y !== y);
    const nextTerrain: Terrain[] =
      mapEditTool === "erase" ? terrain : [...terrain, { x, y, type: mapEditTool }];
    const response = await updateMap({
      updates: { terrain: nextTerrain }
    });
    setState(response.state);
  }

  async function handleStartCombat() {
    const response = await startCombat({
      participantIds: state?.tokens.map((token) => token.actorId || token.id) || null
    });
    setState(response.state);
  }

  async function handleEndTurn() {
    const response = await endTurn({
      actorId: state?.combat.active ? state.combat.initiativeOrder[state.combat.turnIndex]?.actorId : null
    });
    setState(response.state);
  }

  async function handleEndCombat() {
    const response = await endCombat();
    setState(response.state);
    setSelectedTokenId(null);
  }

  async function handleConfirmPending(actionId: string) {
    const response = await confirmPendingAction({ actionId });
    setState(response.state);
  }

  async function handleDeclinePending(actionId: string) {
    const response = await declinePendingAction({ actionId });
    setState(response.state);
  }

  if (error) {
    return <main className="app-shell">{error}</main>;
  }

  if (!authChecked) {
    return <main className="app-shell">Loading tabletop...</main>;
  }

  if (!identity || !state) {
    return <JoinScreen onJoined={applySession} />;
  }

  if (!currentUser) {
    return <main className="app-shell">No seat is available for this session.</main>;
  }

  if (state.session.mode === "character_creation") {
    return (
      <main className="app-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">DND Agent</p>
            <h1>{state.session.title}</h1>
          </div>
          <div className="session-strip" aria-label="session status">
            <span>角色创建</span>
            <div className="identity-chip">
              <span>{currentUser?.displayName || currentUserId}</span>
              <strong>{identity.role}</strong>
            </div>
            <button type="button" onClick={() => void handleLogout()}>
              Logout
            </button>
          </div>
        </header>
        <AdventureSetup
          state={state}
          currentUser={currentUser}
          currentUserId={currentUserId}
          onStateChange={setState}
        />
      </main>
    );
  }

  const current = state.tokens.find((token) => token.id === state.session.currentTurn);
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
          {state.session.mode === "combat" ? (
            <span>Turn {current?.name || state.session.currentTurn}</span>
          ) : (
            <span>{state.adventure?.scene || "探索"}</span>
          )}
          <button
            type="button"
            className={activePage === "tabletop" ? "active" : ""}
            onClick={() => setActivePage("tabletop")}
          >
            {state.session.mode === "combat" ? "战斗" : "探索"}
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
          <a className="nav-link" href="/monsters">
            怪物库
          </a>
          <a className="nav-link" href="/rules">
            Rules
          </a>
          <div className="identity-chip">
            <span>{currentUser?.displayName || currentUserId}</span>
            <strong>{identity.role}</strong>
          </div>
          <button type="button" onClick={() => void handleLogout()}>
            Logout
          </button>
        </div>
      </header>

      {activePage === "characters" ? (
        <CharacterCardsPage
          state={state}
          currentUserId={currentUserId}
          currentUser={currentUser}
          onStateChange={setState}
        />
      ) : state.session.mode !== "combat" ? (
        <ExplorationScene
          state={state}
          currentUser={currentUser}
          onStateChange={setState}
          onSend={handleSend}
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
            <div className="dm-panel-stack">
              {currentUser?.role === "dm" ? (
                <>
                  <DmSceneBrowser state={state} currentUser={currentUser} onStateChange={setState} />
                  <MapBackgroundEditor map={state.map} onStateChange={setState} />
                </>
              ) : null}
              <CombatPanel
                combat={state.combat}
                pendingActions={state.pendingActions}
                tokens={state.tokens}
                currentUser={currentUser}
                onStartCombat={handleStartCombat}
                onEndCombat={handleEndCombat}
                onEndTurn={handleEndTurn}
                onConfirmPending={handleConfirmPending}
                onDeclinePending={handleDeclinePending}
              />
            </div>
            <CharacterSheet characters={state.characters} />
          </div>
          <ChatPanel events={state.events} onSend={handleSend} />
        </section>
      )}
    </main>
  );
}
