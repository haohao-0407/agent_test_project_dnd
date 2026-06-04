import type { CSSProperties } from "react";
import type { GameMap, Token } from "../api/types";

type MapViewProps = {
  map: GameMap;
  tokens: Token[];
  selectedTokenId: string | null;
  onSelectToken: (tokenId: string | null) => void;
  onMoveToken: (x: number, y: number) => void;
};

const terrainClass: Record<string, string> = {
  wall: "wall",
  water: "water",
  difficult: "difficult"
};

export function MapView({
  map,
  tokens,
  selectedTokenId,
  onSelectToken,
  onMoveToken
}: MapViewProps) {
  const cells = [];
  for (let y = 0; y < map.height; y += 1) {
    for (let x = 0; x < map.width; x += 1) {
      const terrain = map.terrain.find((item) => item.x === x && item.y === y);
      const annotation = map.annotations.find((item) => item.x === x && item.y === y);
      const token = tokens.find((item) => item.x === x && item.y === y);
      const classes = ["cell"];
      if (terrain) classes.push(terrainClass[terrain.type] || terrain.type);
      if (selectedTokenId && terrain?.type !== "wall") classes.push("selected");

      cells.push(
        <button
          aria-label={`grid ${x + 1}, ${y + 1}`}
          className={classes.join(" ")}
          key={`${x}-${y}`}
          onClick={() => {
            if (token) {
              onSelectToken(token.id === selectedTokenId ? null : token.id);
            } else if (selectedTokenId) {
              onMoveToken(x, y);
            }
          }}
          type="button"
        >
          {annotation ? <span className="annotation">{annotation.label}</span> : null}
          {token ? (
            <span
              className={`token ${token.kind} ${token.id === selectedTokenId ? "active" : ""}`}
              title={token.name}
            >
              {token.name.slice(0, 1)}
            </span>
          ) : null}
        </button>
      );
    }
  }

  return (
    <section className="map-panel" aria-labelledby="map-title">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Map</p>
          <h2 id="map-title">{map.name}</h2>
        </div>
        <button
          className="icon-button"
          type="button"
          title="取消选择"
          aria-label="取消选择"
          onClick={() => onSelectToken(null)}
        >
          X
        </button>
      </div>
      <div
        className="map-grid"
        style={{ "--cols": map.width, "--rows": map.height } as CSSProperties}
        aria-label="battle map"
      >
        {cells}
      </div>
    </section>
  );
}
