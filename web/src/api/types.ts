export type Session = {
  id: string;
  title: string;
  mode: string;
  round: number;
  currentTurn: string;
};

export type Terrain = {
  x: number;
  y: number;
  type: "wall" | "water" | "difficult" | string;
};

export type Annotation = {
  x: number;
  y: number;
  label: string;
};

export type GameMap = {
  id: string;
  name: string;
  width: number;
  height: number;
  gridSize: number;
  terrain: Terrain[];
  annotations: Annotation[];
};

export type Token = {
  id: string;
  name: string;
  kind: "player" | "monster" | string;
  x: number;
  y: number;
};

export type Character = {
  id: string;
  name: string;
  class: string;
  race: string;
  hp: { current: number; max: number; temp: number };
  ac: number;
  speed: number;
  attributes: Record<string, number>;
  skills: string[];
  attacks: string[];
  conditions: string[];
};

export type DiceResult = {
  expression: string;
  rolls: number[];
  kept: number[];
  modifier: number;
  total: number;
  reason: string;
  rollerId?: string | null;
  advantage: "normal" | "advantage" | "disadvantage";
  time: string;
};

export type EventLogEntry = {
  type: "dm" | "player" | "dice" | "system" | string;
  speaker: string;
  text: string;
  time: string;
  result?: DiceResult;
};

export type GameState = {
  session: Session;
  map: GameMap;
  tokens: Token[];
  characters: Character[];
  events: EventLogEntry[];
};

export type DiceMode = "normal" | "advantage" | "disadvantage";
