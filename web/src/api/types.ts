export type Session = {
  id: string;
  title: string;
  mode: string;
  round: number;
  currentTurn: string;
};

export type Adventure = {
  moduleName: string;
  chapter: string;
  scene: string;
  explorationSceneId?: string;
  backgroundUrl?: string;
  combatSceneId?: string;
  combatSceneName?: string;
  source: string;
  startedAt: string;
};

export type CombatSceneResource = {
  id: string;
  name: string;
  chapter: string;
  map: string;
  trigger: string;
  monsterCount: number;
  linkedExplorationSceneIds: string[];
};

export type ExplorationSceneResource = {
  id: string;
  name: string;
  chapter: string;
  kind: string;
  background: string;
  backgroundUrl: string;
  scenePrompt: string;
  combatSceneId: string;
  combatScene?: CombatSceneResource | null;
};

export type AdventureSceneCollection = {
  moduleName: string;
  version?: string;
  openingSceneId: string;
  explorationScenes: ExplorationSceneResource[];
  combatScenes: CombatSceneResource[];
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

export type MapBackground = {
  url: string;
  width: number;
  height: number;
  opacity: number;
};

export type MapGrid = {
  size: number;
  originX: number;
  originY: number;
  scale: number;
  offsetX: number;
  offsetY: number;
};

export type MapLayers = {
  terrain: Terrain[];
  walls: Terrain[];
  doors: (Terrain & { open?: boolean })[];
  obstacles: Terrain[];
  annotations: Annotation[];
  fog: { x: number; y: number; visibility: string }[];
  effects: Record<string, unknown>[];
  dmNotes: Record<string, unknown>[];
};

export type GameMap = {
  id: string;
  name: string;
  width: number;
  height: number;
  gridSize: number;
  background?: MapBackground;
  grid?: MapGrid;
  layers?: MapLayers;
  terrain: Terrain[];
  annotations: Annotation[];
};

export type Token = {
  id: string;
  actorId?: string;
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

export type CharacterImagePurpose =
  | "combat"
  | "travel"
  | "topDown"
  | "sideView"
  | "portrait"
  | "scene"
  | "token"
  | "other";

export type CharacterImage = {
  id: string;
  purpose: CharacterImagePurpose | string;
  title: string;
  fileName: string;
  mimeType: string;
  size: number;
  path?: string;
  url?: string;
  dataUrl?: string;
  notes: string;
  createdAt: string;
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
  images?: CharacterImage[];
  notes?: string;
};

export type MonsterCard = {
  id: string;
  name: string;
  source: string;
  page: string;
  size: string;
  type: string;
  alignment: string;
  armorClass: string;
  hitPoints: string;
  speed: string;
  attributes: Record<AbilityKey, number>;
  savingThrows: string;
  skills: string;
  damageVulnerabilities: string;
  damageResistances: string;
  damageImmunities: string;
  conditionImmunities: string;
  senses: string;
  languages: string;
  challengeRating: string;
  traits: string;
  actions: string;
  bonusActions: string;
  reactions: string;
  legendaryActions: string;
  mythicActions: string;
  lairActions: string;
  regionalEffects: string;
  environment: string;
  treasure: string;
  notes: string;
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
  adventure?: Adventure;
  players: Player[];
  map: GameMap;
  combat: CombatState;
  pendingActions: PendingAction[];
  tokens: Token[];
  characters: Character[];
  events: EventLogEntry[];
};

export type InitiativeEntry = {
  actorId: string;
  name?: string;
  initiative: number;
  roll?: number;
  dexModifier?: number;
};

export type TurnState = {
  actorId: string;
  actionAvailable: boolean;
  bonusActionAvailable: boolean;
  reactionAvailable: boolean;
  objectInteractionAvailable: boolean;
  movementUsed: number;
  movementMax: number;
};

export type ReactionWindow = {
  id: string;
  trigger: string;
  actorId: string;
  sourceId: string;
  status: string;
  availableReactions: { id: string; label: string }[];
  createdAt: string;
};

export type CombatState = {
  active: boolean;
  round: number;
  turnIndex: number;
  initiativeOrder: InitiativeEntry[];
  turnState: Record<string, TurnState>;
  reactionWindows: ReactionWindow[];
  participants: string[];
};

export type PendingAction = {
  id: string;
  type: string;
  actorId: string;
  requestedBy?: string;
  status: "pending" | "confirmed" | "declined" | "resolved" | string;
  summary?: string;
  payload?: Record<string, unknown>;
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
      name: "spend_spell_slot" | "restore_spell_slot";
      arguments: {
        character_id: string;
        level: number;
        amount?: number;
      };
    }
  | {
      name: "spend_resource" | "restore_resource";
      arguments: {
        character_id: string;
        resource_name: string;
        amount?: number;
      };
    }
  | {
      name: string;
      arguments: Record<string, unknown>;
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
      name: "spend_spell_slot" | "restore_spell_slot";
      result: { character: Character; level: string; amount: number; slot: SpellSlot };
    }
  | {
      name: "spend_resource" | "restore_resource";
      result: { character: Character; amount: number; resource: CharacterResource };
    }
  | {
      name: string;
      result: Record<string, unknown>;
    };

export type ChatResponse = {
  state: GameState;
  toolCalls: ToolCall[];
  toolResults: ToolResult[];
  pendingActions?: PendingAction[];
  dmSource?: "llm" | "fallback";
};
