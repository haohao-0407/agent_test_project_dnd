import { FormEvent, useMemo, useState } from "react";
import type { Character, EventLogEntry, GameState, Player } from "../api/types";
import { DmSceneBrowser } from "./DmSceneBrowser";

type ExplorationSceneProps = {
  state: GameState;
  currentUser: Player;
  onStateChange: (state: GameState) => void;
  onSend: (message: string) => Promise<void>;
};

export function ExplorationScene({ state, currentUser, onStateChange, onSend }: ExplorationSceneProps) {
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const visibleCharacters = useMemo(() => explorationCharacters(state), [state]);
  const currentDialogue = [...state.events].reverse().find((event) => event.type === "dm" || event.type === "player");
  const recentDialogue = state.events.filter((event) => event.type === "dm" || event.type === "player").slice(-5);
  const backgroundImage = state.adventure?.backgroundUrl ? `url(${state.adventure.backgroundUrl})` : undefined;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (!text) return;
    setIsSending(true);
    setSendError(null);
    try {
      await onSend(text);
      setMessage("");
    } catch (error) {
      setSendError(error instanceof Error ? error.message : "发送失败");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className="exploration-scene" aria-label="探索场景">
      <div
        className="exploration-backdrop"
        style={{ backgroundImage }}
      >
        <div className="exploration-stage">
          <div className="portrait-row" aria-label="party portraits">
            {visibleCharacters.map((character) => (
              <CharacterPortrait
                character={character}
                isCurrent={character.id === currentUser.characterId}
                key={character.id}
              />
            ))}
          </div>
          {currentUser.role === "dm" ? (
            <DmSceneBrowser state={state} currentUser={currentUser} onStateChange={onStateChange} />
          ) : null}

          <div className="dialogue-stack">
            <div className="dialogue-history">
              {recentDialogue.map((event, index) => (
                <DialogueLine event={event} key={`${event.time}-${index}`} />
              ))}
            </div>
            <div className={`dialogue-box ${currentDialogue?.type || "dm"}`}>
              <div className="dialogue-speaker">
                <span>{currentDialogue?.speaker || "DM"}</span>
                <strong>{state.adventure?.scene || state.session.title}</strong>
              </div>
              <p>{currentDialogue?.text || "队伍在旅途中短暂停下，等待下一步行动。"}</p>
              <form className="dialogue-form" onSubmit={handleSubmit}>
                {sendError ? <p className="chat-error">{sendError}</p> : null}
                <input
                  autoComplete="off"
                  name="message"
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="描述你的行动"
                  value={message}
                />
                <button disabled={isSending} type="submit">
                  发送
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function explorationCharacters(state: GameState): Character[] {
  const playerCharacterIds = new Set(
    state.players
      .filter((player) => player.role === "player" && player.characterId)
      .map((player) => player.characterId)
  );
  return state.characters.filter((character) => playerCharacterIds.has(character.id));
}

function CharacterPortrait({ character, isCurrent }: { character: Character; isCurrent: boolean }) {
  const image = (character.images || []).find((item) => item.purpose === "portrait")
    || (character.images || []).find((item) => item.purpose === "token")
    || character.images?.[0];
  const imageSource = image?.dataUrl || image?.url || "";

  return (
    <article className={`character-portrait ${isCurrent ? "current" : ""}`}>
      <div className="portrait-image">
        {imageSource ? (
          <img src={imageSource} alt={character.name} />
        ) : (
          <span>{character.name.slice(0, 1)}</span>
        )}
      </div>
      <div className="portrait-label">
        <strong>{character.name}</strong>
        <span>{character.race} / {character.class}</span>
      </div>
    </article>
  );
}

function DialogueLine({ event }: { event: EventLogEntry }) {
  return (
    <article className={`dialogue-line ${event.type}`}>
      <strong>{event.speaker}</strong>
      <span>{event.text}</span>
    </article>
  );
}
