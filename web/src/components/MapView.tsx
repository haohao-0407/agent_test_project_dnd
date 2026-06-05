import type { CSSProperties } from "react";
import type { GameMap, MapEditTool, Token } from "../api/types";

type MapViewProps = {
  map: GameMap;
  tokens: Token[];
  selectedTokenId: string | null;
  controlledTokenIds: string[];
  mapEditTool: MapEditTool;
  canEditMap: boolean;
  onSelectToken: (tokenId: string | null) => void;
  onMoveToken: (x: number, y: number) => void;
  onEditMapCell: (x: number, y: number) => void;
  onMapEditToolChange: (tool: MapEditTool) => void;
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
  controlledTokenIds,
  mapEditTool,
  canEditMap,
  onSelectToken,
  onMoveToken,
  onEditMapCell,
  onMapEditToolChange
}: MapViewProps) {
  const cells = [];
  const terrainLayer = map.layers?.terrain || map.terrain;
  const wallLayer = map.layers?.walls || map.terrain.filter((item) => item.type === "wall");
  const doorLayer = map.layers?.doors || [];
  const obstacleLayer = map.layers?.obstacles || [];
  const annotationLayer = map.layers?.annotations || map.annotations;
  const fogLayer = map.layers?.fog || [];
  for (let y = 0; y < map.height; y += 1) {
    for (let x = 0; x < map.width; x += 1) {
      const terrain = terrainLayer.find((item) => item.x === x && item.y === y);
      const wall = wallLayer.find((item) => item.x === x && item.y === y);
      const door = doorLayer.find((item) => item.x === x && item.y === y);
      const obstacle = obstacleLayer.find((item) => item.x === x && item.y === y);
      const annotation = annotationLayer.find((item) => item.x === x && item.y === y);
      const fog = fogLayer.find((item) => item.x === x && item.y === y);
      const token = tokens.find((item) => item.x === x && item.y === y);
      const canControlToken = token ? controlledTokenIds.includes(token.id) : false;
      const classes = ["cell"];
      if (terrain) classes.push(terrainClass[terrain.type] || terrain.type);
      if (wall) classes.push("wall");
      if (door) classes.push(door.open ? "door-open" : "door");
      if (obstacle) classes.push("obstacle");
      if (fog) classes.push(`fog-${fog.visibility}`);
      if (selectedTokenId && terrain?.type !== "wall" && !wall) classes.push("selected");
      if (token && !canControlToken) classes.push("locked");

      cells.push(
        <button
          aria-label={`grid ${x}, ${y}`}
          className={classes.join(" ")}
          key={`${x}-${y}`}
          onClick={() => {
            if (canEditMap && mapEditTool !== "move") {
              onEditMapCell(x, y);
              return;
            }
            if (token) {
              if (canControlToken) {
                onSelectToken(token.id === selectedTokenId ? null : token.id);
              }
              return;
            }
            if (selectedTokenId) {
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
        {canEditMap ? (
          <div className="map-tools" aria-label="map editor">
            {(["move", "wall", "water", "difficult", "erase"] as MapEditTool[]).map((tool) => (
              <button
                className={mapEditTool === tool ? "active" : ""}
                key={tool}
                onClick={() => onMapEditToolChange(tool)}
                title={tool}
                type="button"
              >
                {tool}
              </button>
            ))}
          </div>
        ) : null}
      </div>
      <div className="map-grid-frame">
        <div
          className="map-grid"
          style={
            {
              "--cols": map.width,
              "--rows": map.height,
              "--map-background": map.background?.url ? `url(${map.background.url})` : "none",
              "--map-background-opacity": map.background?.opacity ?? 1
            } as CSSProperties
          }
          aria-label="battle map"
        >
          {cells}
        </div>
      </div>
    </section>
  );
}
