import type { Character } from "../api/types";

const text = {
  title: "\u89d2\u8272\u7b80\u8868",
  skills: "\u6280\u80fd",
  attacks: "\u653b\u51fb",
  conditions: "\u72b6\u6001",
  none: "\u65e0"
};

type CharacterSheetProps = {
  characters: Character[];
};

export function CharacterSheet({ characters }: CharacterSheetProps) {
  return (
    <aside className="sheet-panel" aria-labelledby="sheet-title">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Characters</p>
          <h2 id="sheet-title">{text.title}</h2>
        </div>
      </div>
      <div className="character-list">
        {characters.map((character) => {
          const hpPercent = Math.max(
            0,
            Math.min(100, (character.hp.current / character.hp.max) * 100)
          );
          return (
            <article className="character-card" key={character.id}>
              <div className="character-main">
                <div>
                  <h3>{character.name}</h3>
                  <p>
                    {character.race} / {character.class}
                  </p>
                </div>
                <div className="pill">AC {character.ac}</div>
                <div className="pill">{character.speed} ft</div>
              </div>
              <div className="character-body">
                <p className="stat-list">
                  HP {character.hp.current}/{character.hp.max} / Temp {character.hp.temp}
                </p>
                <div className="hp-bar">
                  <div className="hp-fill" style={{ width: `${hpPercent}%` }} />
                </div>
                <div className="stat-grid">
                  {Object.entries(character.attributes).map(([key, value]) => (
                    <div className="stat" key={key}>
                      <span>{key}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
                <p className="detail-list">
                  {text.skills}: {character.skills.join(" / ") || text.none}
                </p>
                <p className="detail-list">
                  {text.attacks}: {character.attacks.join(" / ") || text.none}
                </p>
                <p className="detail-list">
                  {text.conditions}: {character.conditions.length ? character.conditions.join(" / ") : text.none}
                </p>
              </div>
            </article>
          );
        })}
      </div>
    </aside>
  );
}
