import { useState } from "react";
import { startAdventure } from "../api/client";
import type { GameState, Player } from "../api/types";
import { CharacterCardsPage } from "./CharacterCardsPage";

type AdventureSetupProps = {
  state: GameState;
  currentUser: Player;
  currentUserId: string;
  onStateChange: (state: GameState) => void;
};

export function AdventureSetup({
  state,
  currentUser,
  currentUserId,
  onStateChange
}: AdventureSetupProps) {
  const [starting, setStarting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const partyPlayers = state.players.filter((player) => player.role === "player" && player.characterId);
  const isPlayer = currentUser.role !== "dm";
  const hasCharacter = !isPlayer || Boolean(currentUser.characterId);
  const canStart = partyPlayers.length > 0 && hasCharacter;

  async function handleStartAdventure() {
    setStarting(true);
    setNotice(null);
    try {
      const response = await startAdventure({ moduleName: state.adventure?.moduleName });
      onStateChange(response.state);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "冒险启动失败");
    } finally {
      setStarting(false);
    }
  }

  return (
    <section className="adventure-setup">
      <aside className="setup-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Adventure</p>
            <h2>{state.adventure?.moduleName || state.session.title}</h2>
          </div>
        </div>
        <div className="setup-body">
          <div className="setup-status">
            <span>角色</span>
            <strong>{partyPlayers.length}</strong>
          </div>
          <div className="setup-party">
            {state.players.filter((player) => player.role === "player").map((player) => {
              const character = state.characters.find((item) => item.id === player.characterId);
              return (
                <div className="setup-party-row" key={player.id}>
                  <span>{player.displayName}</span>
                  <strong>{character ? character.name : "未创建"}</strong>
                </div>
              );
            })}
          </div>
          <button type="button" disabled={!canStart || starting} onClick={() => void handleStartAdventure()}>
            {starting ? "绘制地图中" : "开始冒险"}
          </button>
          {notice ? <p className="join-error">{notice}</p> : null}
        </div>
      </aside>
      {isPlayer ? (
        <CharacterCardsPage
          state={state}
          currentUserId={currentUserId}
          currentUser={currentUser}
          onStateChange={onStateChange}
        />
      ) : (
        <section className="dm-wait-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Party</p>
              <h2>队伍准备</h2>
            </div>
          </div>
          <div className="setup-body">
            {partyPlayers.length ? (
              partyPlayers.map((player) => {
                const character = state.characters.find((item) => item.id === player.characterId);
                return (
                  <div className="setup-character-card" key={player.id}>
                    <strong>{character?.name || player.displayName}</strong>
                    <span>{character ? `${character.race} / ${character.class}` : "未创建"}</span>
                  </div>
                );
              })
            ) : (
              <p className="setup-empty">等待玩家创建角色</p>
            )}
          </div>
        </section>
      )}
    </section>
  );
}
