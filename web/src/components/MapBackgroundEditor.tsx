import { FormEvent, useEffect, useState } from "react";
import { updateMap, updateMapBackground } from "../api/client";
import type { GameMap, GameState, MapBackground, MapGrid } from "../api/types";

type MapBackgroundEditorProps = {
  map: GameMap;
  onStateChange: (state: GameState) => void;
};

type UploadedMapImage = {
  url: string;
  width: number;
  height: number;
};

function defaultBackground(): MapBackground {
  return { url: "", width: 0, height: 0, opacity: 1 };
}

function defaultGrid(map: GameMap): MapGrid {
  return {
    size: map.gridSize,
    originX: 0,
    originY: 0,
    scale: 1,
    offsetX: 0,
    offsetY: 0
  };
}

export function MapBackgroundEditor({ map, onStateChange }: MapBackgroundEditorProps) {
  const [backgroundDraft, setBackgroundDraft] = useState<MapBackground>(map.background || defaultBackground());
  const [gridDraft, setGridDraft] = useState<MapGrid>(map.grid || defaultGrid(map));
  const [status, setStatus] = useState<string>("");
  const [isSavingBackground, setIsSavingBackground] = useState(false);
  const [isSavingGrid, setIsSavingGrid] = useState(false);

  useEffect(() => {
    setBackgroundDraft(map.background || defaultBackground());
    setGridDraft(map.grid || defaultGrid(map));
  }, [map]);

  async function saveBackground(nextBackground = normalizeBackground(backgroundDraft)) {
    setIsSavingBackground(true);
    setStatus("");
    try {
      const response = await updateMapBackground({
        background: nextBackground
      });
      onStateChange(response.state);
      setStatus("Background saved");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Background save failed");
    } finally {
      setIsSavingBackground(false);
    }
  }

  async function handleBackgroundSubmit(event: FormEvent) {
    event.preventDefault();
    const nextBackground = await resolveUrlDimensions(normalizeBackground(backgroundDraft));
    setBackgroundDraft(nextBackground);
    await saveBackground(nextBackground);
  }

  async function handleUpload(files: FileList | null) {
    const file = files?.[0];
    if (!file || !file.type.startsWith("image/")) {
      return;
    }
    setStatus("");
    try {
      const image = await readMapImage(file);
      const nextBackground = normalizeBackground({
        ...backgroundDraft,
        url: image.url,
        width: image.width,
        height: image.height
      });
      setBackgroundDraft(nextBackground);
      await saveBackground(nextBackground);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Image upload failed");
    }
  }

  async function clearBackground() {
    const nextBackground = defaultBackground();
    setBackgroundDraft(nextBackground);
    await saveBackground(nextBackground);
  }

  async function handleGridSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSavingGrid(true);
    setStatus("");
    try {
      const response = await updateMap({
        updates: { grid: normalizeGrid(gridDraft, map) }
      });
      onStateChange(response.state);
      setStatus("Grid saved");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Grid save failed");
    } finally {
      setIsSavingGrid(false);
    }
  }

  function resetGrid() {
    setGridDraft(defaultGrid(map));
  }

  return (
    <section className="tool-panel map-background-editor" aria-labelledby="map-background-title">
      <div className="panel-header compact">
        <div>
          <p className="eyebrow">DM Map</p>
          <h2 id="map-background-title">Background</h2>
        </div>
        <label className="upload-button">
          Upload
          <input
            type="file"
            accept="image/*"
            onChange={(event) => {
              void handleUpload(event.target.files);
              event.target.value = "";
            }}
          />
        </label>
      </div>

      <form className="map-background-form" onSubmit={handleBackgroundSubmit}>
        <label className="field">
          <span>Image URL</span>
          <input
            value={backgroundDraft.url}
            onChange={(event) => setBackgroundDraft({ ...backgroundDraft, url: event.target.value })}
            placeholder="https://... or data:image/..."
          />
        </label>
        <div className="form-grid three">
          <label className="field">
            <span>Width</span>
            <input
              type="number"
              min="0"
              value={backgroundDraft.width}
              onChange={(event) =>
                setBackgroundDraft({ ...backgroundDraft, width: nonNegativeInteger(event.target.value) })
              }
            />
          </label>
          <label className="field">
            <span>Height</span>
            <input
              type="number"
              min="0"
              value={backgroundDraft.height}
              onChange={(event) =>
                setBackgroundDraft({ ...backgroundDraft, height: nonNegativeInteger(event.target.value) })
              }
            />
          </label>
          <label className="field">
            <span>Opacity {Math.round(backgroundDraft.opacity * 100)}%</span>
            <input
              type="range"
              min="0"
              max="100"
              value={Math.round(backgroundDraft.opacity * 100)}
              onChange={(event) =>
                setBackgroundDraft({
                  ...backgroundDraft,
                  opacity: clamp(Number(event.target.value) / 100, 0, 1)
                })
              }
            />
          </label>
        </div>
        <div className="map-editor-actions">
          <button disabled={isSavingBackground} type="submit">
            Save background
          </button>
          <button disabled={isSavingBackground} type="button" onClick={() => void clearBackground()}>
            Clear
          </button>
        </div>
      </form>

      <form className="map-background-form" onSubmit={handleGridSubmit}>
        <div className="form-grid three">
          <label className="field">
            <span>Cell px</span>
            <input
              type="number"
              min="1"
              value={gridDraft.size}
              onChange={(event) => setGridDraft({ ...gridDraft, size: positiveInteger(event.target.value, map.gridSize) })}
            />
          </label>
          <label className="field">
            <span>Origin X</span>
            <input
              type="number"
              value={gridDraft.originX}
              onChange={(event) => setGridDraft({ ...gridDraft, originX: integerValue(event.target.value) })}
            />
          </label>
          <label className="field">
            <span>Origin Y</span>
            <input
              type="number"
              value={gridDraft.originY}
              onChange={(event) => setGridDraft({ ...gridDraft, originY: integerValue(event.target.value) })}
            />
          </label>
          <label className="field">
            <span>Offset X</span>
            <input
              type="number"
              value={gridDraft.offsetX}
              onChange={(event) => setGridDraft({ ...gridDraft, offsetX: integerValue(event.target.value) })}
            />
          </label>
          <label className="field">
            <span>Offset Y</span>
            <input
              type="number"
              value={gridDraft.offsetY}
              onChange={(event) => setGridDraft({ ...gridDraft, offsetY: integerValue(event.target.value) })}
            />
          </label>
          <label className="field">
            <span>Scale</span>
            <input
              type="number"
              min="0.1"
              step="0.05"
              value={gridDraft.scale}
              onChange={(event) => setGridDraft({ ...gridDraft, scale: positiveNumber(event.target.value, 1) })}
            />
          </label>
        </div>
        <div className="map-editor-actions">
          <button disabled={isSavingGrid} type="submit">
            Save grid
          </button>
          <button disabled={isSavingGrid} type="button" onClick={resetGrid}>
            Reset
          </button>
        </div>
        {status ? <p className="map-editor-status">{status}</p> : null}
      </form>
    </section>
  );
}

function normalizeBackground(background: MapBackground): MapBackground {
  return {
    url: background.url.trim(),
    width: Math.max(0, Math.trunc(background.width || 0)),
    height: Math.max(0, Math.trunc(background.height || 0)),
    opacity: clamp(background.opacity, 0, 1)
  };
}

function normalizeGrid(grid: MapGrid, map: GameMap): MapGrid {
  return {
    size: Math.max(1, Math.trunc(grid.size || map.gridSize)),
    originX: Math.trunc(grid.originX || 0),
    originY: Math.trunc(grid.originY || 0),
    scale: Math.max(0.01, Number.isFinite(grid.scale) ? grid.scale : 1),
    offsetX: Math.trunc(grid.offsetX || 0),
    offsetY: Math.trunc(grid.offsetY || 0)
  };
}

async function resolveUrlDimensions(background: MapBackground): Promise<MapBackground> {
  if (!background.url || (background.width > 0 && background.height > 0)) {
    return background;
  }
  try {
    const dimensions = await loadImageDimensions(background.url);
    return { ...background, ...dimensions };
  } catch {
    return background;
  }
}

function readMapImage(file: File): Promise<UploadedMapImage> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const dataUrl = typeof reader.result === "string" ? reader.result : "";
      if (!dataUrl) {
        reject(new Error("image file could not be read"));
        return;
      }
      loadImageDimensions(dataUrl)
        .then((dimensions) => resolve({ url: dataUrl, ...dimensions }))
        .catch((error) => reject(error instanceof Error ? error : new Error("image file could not be read")));
    });
    reader.addEventListener("error", () => reject(reader.error || new Error("image file could not be read")));
    reader.readAsDataURL(file);
  });
}

function loadImageDimensions(url: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => {
      resolve({
        width: image.naturalWidth || 0,
        height: image.naturalHeight || 0
      });
    });
    image.addEventListener("error", () => reject(new Error("image dimensions could not be read")));
    image.src = url;
  });
}

function integerValue(value: string): number {
  const next = Number(value);
  return Number.isFinite(next) ? Math.trunc(next) : 0;
}

function positiveInteger(value: string, fallback: number): number {
  const next = Number(value);
  return Number.isFinite(next) && next > 0 ? Math.trunc(next) : fallback;
}

function nonNegativeInteger(value: string): number {
  return Math.max(0, integerValue(value));
}

function positiveNumber(value: string, fallback: number): number {
  const next = Number(value);
  return Number.isFinite(next) && next > 0 ? next : fallback;
}

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, value));
}
