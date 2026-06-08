import type {
  AdventureSceneCollection,
  Character,
  CharacterResource,
  ChatResponse,
  DiceMode,
  DiceResult,
  GameMap,
  GameState,
  MonsterCard,
  PendingAction,
  RagQueryResponse,
  SpellSlot,
  TurnState
} from "./types";

const AUTH_TOKEN_KEY = "dnd-seat-token";

export type JoinRole = "player" | "dm";

export type AuthSession = {
  token?: string;
  sessionId: string;
  userId: string;
  role: JoinRole | string;
  player?: GameState["players"][number] | null;
  state: GameState;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getAuthToken(): string | null {
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function clearAuthToken(): void {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

function setAuthToken(token: string): void {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

async function request<T>(path: string, init?: RequestInit, options?: { auth?: boolean }): Promise<T> {
  const headers = new Headers(init?.headers);
  const hasBody = init?.body !== undefined;
  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (options?.auth !== false) {
    const token = getAuthToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(path, {
    ...init,
    headers
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
    }
    throw new ApiError(payload.detail || payload.error || "request failed", response.status);
  }
  return payload as T;
}

export async function joinSession(role: JoinRole, username: string): Promise<AuthSession> {
  const session = await request<AuthSession>(
    "/api/auth/join",
    {
      method: "POST",
      body: JSON.stringify({ role, username })
    },
    { auth: false }
  );
  if (session.token) {
    setAuthToken(session.token);
  }
  return session;
}

export function me(): Promise<AuthSession> {
  return request<AuthSession>("/api/auth/me");
}

export async function logout(): Promise<void> {
  try {
    await request<{ ok: boolean }>("/api/auth/logout", { method: "POST" });
  } finally {
    clearAuthToken();
  }
}

export function getState(): Promise<GameState> {
  return request<GameState>("/api/state");
}

export function moveToken(
  tokenId: string,
  x: number,
  y: number
): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/token/move", {
    method: "POST",
    body: JSON.stringify({ tokenId, x, y })
  });
}

export function updateMap(input: {
  updates: Partial<GameMap>;
}): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/map", {
    method: "PATCH",
    body: JSON.stringify(input)
  });
}

export function updateMapLayer(input: {
  layer: string;
  items: Record<string, unknown>[];
}): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/map/layers", {
    method: "PATCH",
    body: JSON.stringify(input)
  });
}

export function updateMapBackground(input: {
  background: NonNullable<GameMap["background"]>;
}): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/map/background", {
    method: "PATCH",
    body: JSON.stringify(input)
  });
}

export function startAdventure(input: {
  moduleName?: string;
} = {}): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/adventure/start", {
    method: "POST",
    body: JSON.stringify({ moduleName: input.moduleName || "凡戴尔的失落矿坑" })
  });
}

export function setAdventureReady(input: {
  ready: boolean;
  moduleName?: string;
}): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/adventure/ready", {
    method: "POST",
    body: JSON.stringify({
      ready: input.ready,
      moduleName: input.moduleName || "凡戴尔的失落矿坑"
    })
  });
}

export function getAdventureScenes(input: {
  moduleName?: string;
} = {}): Promise<{ scenes: AdventureSceneCollection }> {
  const params = new URLSearchParams({
    moduleName: input.moduleName || "凡戴尔的失落矿坑"
  });
  return request<{ scenes: AdventureSceneCollection }>(`/api/adventure/scenes?${params.toString()}`);
}

export function jumpAdventureScene(input: {
  moduleName?: string;
  sceneId: string;
}): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/adventure/scenes/jump", {
    method: "POST",
    body: JSON.stringify({
      moduleName: input.moduleName || "凡戴尔的失落矿坑",
      sceneId: input.sceneId
    })
  });
}

export function startCombat(input: {
  participantIds?: string[] | null;
  sceneId?: string | null;
}): Promise<{ combat: GameState["combat"]; state: GameState }> {
  return request<{ combat: GameState["combat"]; state: GameState }>("/api/combat/start", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function endCombat(): Promise<{ combat: GameState["combat"]; state: GameState }> {
  return request<{ combat: GameState["combat"]; state: GameState }>("/api/combat/end", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function endTurn(input: {
  actorId?: string | null;
}): Promise<{ combat: GameState["combat"]; state: GameState }> {
  return request<{ combat: GameState["combat"]; state: GameState }>("/api/combat/end-turn", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function advanceTurn(): Promise<{ combat: GameState["combat"]; state: GameState }> {
  return request<{ combat: GameState["combat"]; state: GameState }>("/api/combat/advance-turn", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function advanceToPlayerTurn(): Promise<{ combat: GameState["combat"]; state: GameState }> {
  return request<{ combat: GameState["combat"]; state: GameState }>("/api/combat/advance-to-player-turn", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function spendSpellSlot(input: {
  characterId: string;
  level: number;
  amount?: number;
}): Promise<{ result: { character: Character; level: string; amount: number; slot: SpellSlot }; state: GameState }> {
  return request<{ result: { character: Character; level: string; amount: number; slot: SpellSlot }; state: GameState }>(
    "/api/combat/spend-spell-slot",
    {
      method: "POST",
      body: JSON.stringify(input)
    }
  );
}

export function restoreSpellSlot(input: {
  characterId: string;
  level: number;
  amount?: number;
}): Promise<{ result: { character: Character; level: string; amount: number; slot: SpellSlot }; state: GameState }> {
  return request<{ result: { character: Character; level: string; amount: number; slot: SpellSlot }; state: GameState }>(
    "/api/combat/restore-spell-slot",
    {
      method: "POST",
      body: JSON.stringify(input)
    }
  );
}

export function spendResource(input: {
  characterId: string;
  resourceName: string;
  amount?: number;
}): Promise<{ result: { character: Character; amount: number; resource: CharacterResource }; state: GameState }> {
  return request<{ result: { character: Character; amount: number; resource: CharacterResource }; state: GameState }>(
    "/api/combat/spend-resource",
    {
      method: "POST",
      body: JSON.stringify(input)
    }
  );
}

export function restoreResource(input: {
  characterId: string;
  resourceName: string;
  amount?: number;
}): Promise<{ result: { character: Character; amount: number; resource: CharacterResource }; state: GameState }> {
  return request<{ result: { character: Character; amount: number; resource: CharacterResource }; state: GameState }>(
    "/api/combat/restore-resource",
    {
      method: "POST",
      body: JSON.stringify(input)
    }
  );
}

export function restoreActionEconomy(input: {
  actorId: string;
  actionType: "action" | "bonus_action" | "reaction" | "object_interaction" | "movement" | "all" | string;
  amount?: number;
  reason?: string;
}): Promise<{
  result: { actorId: string; actionType: string; amount: number; reason: string; turnState: TurnState };
  state: GameState;
}> {
  return request<{
    result: { actorId: string; actionType: string; amount: number; reason: string; turnState: TurnState };
    state: GameState;
  }>("/api/combat/restore-action-economy", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function confirmPendingAction(input: {
  actionId: string;
}): Promise<{ pendingAction: PendingAction; state: GameState }> {
  return request<{ pendingAction: PendingAction; state: GameState }>(
    `/api/pending-actions/${input.actionId}/confirm`,
    {
      method: "POST",
      body: JSON.stringify({})
    }
  );
}

export function declinePendingAction(input: {
  actionId: string;
}): Promise<{ pendingAction: PendingAction; state: GameState }> {
  return request<{ pendingAction: PendingAction; state: GameState }>(
    `/api/pending-actions/${input.actionId}/decline`,
    {
      method: "POST",
      body: JSON.stringify({})
    }
  );
}

export function createCharacter(input: {
  character: Character;
}): Promise<{ character: Character; state: GameState }> {
  return request<{ character: Character; state: GameState }>("/api/characters", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function updateCharacter(input: {
  characterId: string;
  updates: Partial<Character>;
}): Promise<{ character: Character; state: GameState }> {
  return request<{ character: Character; state: GameState }>(`/api/characters/${input.characterId}`, {
    method: "PATCH",
    body: JSON.stringify({ updates: input.updates })
  });
}

export function getPermanentCharacters(): Promise<{ characters: Character[] }> {
  return request<{ characters: Character[] }>("/api/permanent-characters");
}

export function createPermanentCharacter(input: {
  character: Character;
}): Promise<{ character: Character; characters: Character[] }> {
  return request<{ character: Character; characters: Character[] }>("/api/permanent-characters", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function updatePermanentCharacter(input: {
  characterId: string;
  updates: Partial<Character>;
}): Promise<{ character: Character; characters: Character[] }> {
  return request<{ character: Character; characters: Character[] }>(
    `/api/permanent-characters/${input.characterId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ updates: input.updates })
    }
  );
}

export function getPermanentMonsters(): Promise<{ monsters: MonsterCard[] }> {
  return request<{ monsters: MonsterCard[] }>("/api/permanent-monsters");
}

export function createPermanentMonster(input: {
  monster: MonsterCard;
}): Promise<{ monster: MonsterCard; monsters: MonsterCard[] }> {
  return request<{ monster: MonsterCard; monsters: MonsterCard[] }>("/api/permanent-monsters", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function updatePermanentMonster(input: {
  monsterId: string;
  updates: Partial<MonsterCard>;
}): Promise<{ monster: MonsterCard; monsters: MonsterCard[] }> {
  return request<{ monster: MonsterCard; monsters: MonsterCard[] }>(
    `/api/permanent-monsters/${input.monsterId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ updates: input.updates })
    }
  );
}

export function rollDice(input: {
  expression: string;
  reason: string;
  rollerId?: string | null;
  advantage: DiceMode;
}): Promise<{ result: DiceResult; state: GameState }> {
  return request<{ result: DiceResult; state: GameState }>("/api/dice", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function sendChat(input: {
  speaker: string;
  message: string;
}): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function queryRules(input: {
  query: string;
  k: number;
}): Promise<RagQueryResponse> {
  return request<RagQueryResponse>("/api/rag/query", {
    method: "POST",
    body: JSON.stringify(input)
  });
}
