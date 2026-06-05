export type Session = {
  id: string;
  title: string;
  mode: string;
  round: number;
  currentTurn: string;
};

export type Player = {
  id: string;
  displayName: string;
  characterId?: string | null;
  role: "player" | "dm" | string;
};

export type Terrain = {
  x: number;
  y: number;
  type: "wall" | "water" | "difficult" | string;
};

export type MapEditTool = "move" | "wall" | "water" | "difficult" | "erase";

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

export type AbilityKey = "STR" | "DEX" | "CON" | "INT" | "WIS" | "CHA";

export type AbilityDetail = {
  score: number;
  modifier: number;
  saveProficient: boolean;
};

export type ClassLevel = {
  name: string;
  subclass: string;
  level: number;
  hitDie: string;
};

export type CharacterResource = {
  name: string;
  max: number;
  current: number;
  reset: string;
};

export type SpellSlot = {
  max: number;
  current: number;
};

export type CharacterAttack = {
  name: string;
  ability: AbilityKey;
  proficient: boolean;
  extraAttackBonus: number;
  damageDice: string;
  damageAbility: boolean;
  extraDamageBonus: number;
  damageType: string;
  range: string;
  notes: string;
};

export type CharacterActionDetail = {
  name: string;
  cost: string;
  description: string;
};

export type CharacterFeatureDetail = {
  name: string;
  source: string;
  description: string;
};

export type Character = {
  id: string;
  ownerUserId?: string | null;
  name: string;
  playerName?: string;
  class: string;
  classes?: ClassLevel[];
  level?: number;
  race: string;
  subrace?: string;
  background?: string;
  alignment?: string;
  experience?: number;
  inspiration?: boolean;
  proficiencyBonus?: number;
  hp: { current: number; max: number; temp: number };
  hitDice?: { die: string; max: number; current: number }[];
  deathSaves?: { successes: number; failures: number };
  ac: number;
  initiative?: number;
  speed: number;
  attributes: Record<string, number>;
  abilities?: Record<AbilityKey, AbilityDetail>;
  savingThrows?: string[];
  skills: string[];
  skillDetails?: string[];
  attacks: string[];
  attackDetails?: CharacterAttack[];
  actions?: string[];
  actionDetails?: CharacterActionDetail[];
  conditions: string[];
  defenses?: { resistances: string[]; immunities: string[]; vulnerabilities: string[] };
  senses?: {
    passivePerception: number;
    passiveInvestigation: number;
    passiveInsight: number;
    other: string[];
  };
  proficiencies?: { armor: string[]; weapons: string[]; tools: string[] };
  languages?: string[];
  equipment?: { items: string[]; attunedItems: string[]; carryingCapacity: number };
  currency?: { cp: number; sp: number; ep: number; gp: number; pp: number };
  features?: string[];
  featureDetails?: CharacterFeatureDetail[];
  traits?: string[];
  traitDetails?: CharacterFeatureDetail[];
  spellcasting?: {
    ability: string;
    saveDc: number;
    attackBonus: number;
    slots: Record<string, SpellSlot>;
    pactSlots: { slotLevel: number; max: number; current: number };
    spellsKnown: string[];
    spellsPrepared: string[];
  };
  resources?: CharacterResource[];
  personality?: { traits: string; ideals: string; bonds: string; flaws: string };
  appearance?: { age: string; height: string; weight: string; eyes: string; skin: string; hair: string };
  notes?: string;
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
  players: Player[];
  map: GameMap;
  tokens: Token[];
  characters: Character[];
  events: EventLogEntry[];
};

export type DiceMode = "normal" | "advantage" | "disadvantage";

export type RagChunk = {
  chunkId: string;
  content: string;
  metadata: Record<string, string | number | boolean | null>;
  distance?: number | null;
};

export type RagQueryResponse = {
  chunks: RagChunk[];
};

export type ToolCall =
  | {
      name: "move_token";
      arguments: {
        token_id: string;
        x: number;
        y: number;
      };
    }
  | {
      name: "roll_dice";
      arguments: {
        expression: string;
        reason: string;
        roller_id?: string | null;
        advantage: DiceMode;
      };
    }
  | {
      name: "update_character_state";
      arguments: {
        character_id: string;
        updates: Partial<Character>;
      };
    };

export type ToolResult =
  | {
      name: "move_token";
      result: { token: Token };
    }
  | {
      name: "roll_dice";
      result: DiceResult;
    }
  | {
      name: "update_character_state";
      result: { character: Character };
    };

export type ChatResponse = {
  state: GameState;
  toolCalls: ToolCall[];
  toolResults: ToolResult[];
  dmSource?: "llm" | "fallback";
};
