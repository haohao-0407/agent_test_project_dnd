import type { Character } from "../api/types";

type CharacterSheetProps = {
  characters: Character[];
};

export function CharacterSheet({ characters }: CharacterSheetProps) {
  return (
    <aside className="sheet-panel" aria-labelledby="sheet-title">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Characters</p>
          <h2 id="sheet-title">角色卡</h2>
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
                    {character.race} · {character.class}
                  </p>
                </div>
                <div className="pill">AC {character.ac}</div>
                <div className="pill">{character.speed} ft</div>
              </div>
              <div className="character-body">
                <p className="stat-list">
                  HP {character.hp.current}/{character.hp.max} · Temp {character.hp.temp}
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
                <p className="detail-list">技能：{character.skills.join(" / ")}</p>
                <p className="detail-list">攻击：{character.attacks.join(" / ")}</p>
                <p className="detail-list">
                  状态：{character.conditions.length ? character.conditions.join(" / ") : "无"}
                </p>
              </div>
            </article>
          );
        })}
      </div>
    </aside>
  );
}
