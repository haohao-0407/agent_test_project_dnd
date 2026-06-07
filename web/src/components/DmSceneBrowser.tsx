import { useEffect, useMemo, useState } from "react";
import { getAdventureScenes, jumpAdventureScene, startCombat } from "../api/client";
import type { AdventureSceneCollection, ExplorationSceneResource, GameState, Player } from "../api/types";

type DmSceneBrowserProps = {
  state: GameState;
  currentUser: Player;
  onStateChange: (state: GameState) => void;
};

export function DmSceneBrowser({ state, currentUser, onStateChange }: DmSceneBrowserProps) {
  const [collection, setCollection] = useState<AdventureSceneCollection | null>(null);
  const [activeChapter, setActiveChapter] = useState("");
  const [query, setQuery] = useState("");
  const [pendingSceneId, setPendingSceneId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const moduleName = state.adventure?.moduleName || "凡戴尔的失落矿坑";

  useEffect(() => {
    if (currentUser.role !== "dm") return;
    let ignore = false;
    getAdventureScenes({ moduleName })
      .then((response) => {
        if (ignore) return;
        setCollection(response.scenes);
        setActiveChapter((current) => current || response.scenes.explorationScenes[0]?.chapter || "");
        setError(null);
      })
      .catch((apiError: Error) => {
        if (!ignore) setError(apiError.message);
      });
    return () => {
      ignore = true;
    };
  }, [currentUser.role, moduleName]);

  const chapters = useMemo(() => {
    const names = new Set<string>();
    for (const scene of collection?.explorationScenes || []) {
      names.add(scene.chapter || "未分章");
    }
    return [...names];
  }, [collection]);

  const visibleScenes = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return (collection?.explorationScenes || []).filter((scene) => {
      const inChapter = !activeChapter || scene.chapter === activeChapter;
      const matchesQuery = !normalizedQuery
        || `${scene.name} ${scene.id} ${scene.kind} ${scene.scenePrompt}`.toLowerCase().includes(normalizedQuery);
      return inChapter && matchesQuery;
    });
  }, [activeChapter, collection, query]);

  if (currentUser.role !== "dm") {
    return null;
  }

  async function jumpToExploration(scene: ExplorationSceneResource) {
    setPendingSceneId(scene.id);
    try {
      const response = await jumpAdventureScene({ moduleName, sceneId: scene.id });
      onStateChange(response.state);
      setError(null);
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Scene jump failed");
    } finally {
      setPendingSceneId(null);
    }
  }

  async function jumpToCombat(sceneId: string) {
    setPendingSceneId(sceneId);
    try {
      const response = await startCombat({ sceneId, participantIds: null });
      onStateChange(response.state);
      setError(null);
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Combat jump failed");
    } finally {
      setPendingSceneId(null);
    }
  }

  const activeExplorationId = state.adventure?.explorationSceneId || "";
  const activeCombatId = state.adventure?.combatSceneId || "";

  return (
    <section className="scene-browser" aria-labelledby="scene-browser-title">
      <div className="panel-header compact">
        <div>
          <p className="eyebrow">DM Scenes</p>
          <h2 id="scene-browser-title">{collection?.moduleName || moduleName}</h2>
        </div>
        <input
          aria-label="Search scenes"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索"
          value={query}
        />
      </div>
      <div className="scene-browser-tabs" aria-label="chapters">
        {chapters.map((chapter) => (
          <button
            className={chapter === activeChapter ? "active" : ""}
            key={chapter}
            onClick={() => setActiveChapter(chapter)}
            type="button"
          >
            {chapter}
          </button>
        ))}
      </div>
      {error ? <p className="scene-browser-error">{error}</p> : null}
      <div className="scene-browser-list">
        {visibleScenes.map((scene) => {
          const combatScene = scene.combatScene;
          const isCurrent = scene.id === activeExplorationId;
          const isCombatCurrent = combatScene?.id === activeCombatId && state.session.mode === "combat";
          return (
            <article className={`scene-row ${isCurrent ? "active" : ""}`} key={scene.id}>
              <button
                className="scene-row-main"
                disabled={pendingSceneId === scene.id}
                onClick={() => void jumpToExploration(scene)}
                type="button"
              >
                <span>{scene.kind || scene.chapter}</span>
                <strong>{scene.name}</strong>
              </button>
              {combatScene ? (
                <button
                  className={isCombatCurrent ? "scene-combat active" : "scene-combat"}
                  disabled={pendingSceneId === combatScene.id}
                  onClick={() => void jumpToCombat(combatScene.id)}
                  title={combatScene.trigger}
                  type="button"
                >
                  战斗
                  <span>{combatScene.monsterCount}</span>
                </button>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
