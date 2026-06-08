import { useState } from "react";
import { setAdventureReady } from "../api/client";
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
  const [updatingReady, setUpdatingReady] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const joinedPlayers = state.players.filter((player) => player.role === "player" && player.joined);
  const readyPlayers = joinedPlayers.filter((player) => player.ready && player.characterId);
  const isPlayer = currentUser.role !== "dm";
  const hasCharacter = !isPlayer || Boolean(currentUser.characterId);
  const isReady = Boolean(currentUser.ready);
  const canReady = isPlayer && hasCharacter;

  async function handleReadyToggle() {
    if (!isPlayer) return;
    setUpdatingReady(true);
    setNotice(null);
    try {
      const response = await setAdventureReady({
        ready: !isReady,
        moduleName: state.adventure?.moduleName
      });
      onStateChange(response.state);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "准备状态更新失败");
    } finally {
      setUpdatingReady(false);
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
            <span>已加入</span>
            <strong>{joinedPlayers.length}</strong>
          </div>
          <div className="setup-status">
            <span>已准备</span>
            <strong>{readyPlayers.length}</strong>
          </div>
          <div className="setup-party">
            {joinedPlayers.length ? joinedPlayers.map((player) => {
              const character = state.characters.find((item) => item.id === player.characterId);
              return (
                <div className="setup-party-row" key={player.id}>
                  <span>{player.displayName}</span>
                  <strong>{character ? character.name : "未创建"}</strong>
                  <span>{player.ready ? "已准备" : "未准备"}</span>
                </div>
              );
            }) : <p className="setup-empty">等待玩家加入</p>}
          </div>
          {isPlayer ? (
            <button type="button" disabled={!canReady || updatingReady} onClick={() => void handleReadyToggle()}>
              {updatingReady ? "同步中" : isReady ? "取消准备" : hasCharacter ? "准备" : "创建角色后准备"}
            </button>
          ) : (
            <p className="setup-empty">所有已加入玩家准备后自动开始冒险</p>
          )}
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
            {joinedPlayers.length ? (
              joinedPlayers.map((player) => {
                const character = state.characters.find((item) => item.id === player.characterId);
                return (
                  <div className="setup-character-card" key={player.id}>
                    <strong>{character?.name || player.displayName}</strong>
                    <span>
                      {character ? `${character.race} / ${character.class}` : "未创建"} / {player.ready ? "已准备" : "未准备"}
                    </span>
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
