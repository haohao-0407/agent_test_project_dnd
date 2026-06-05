import type {
  Character,
  CharacterResource,
  ChatResponse,
  DiceMode,
  DiceResult,
  GameMap,
  GameState,
  PendingAction,
  RagQueryResponse,
  SpellSlot
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || "request failed");
  }
  return payload as T;
}

export function getState(): Promise<GameState> {
  return request<GameState>("/api/state");
}

export function moveToken(
  tokenId: string,
  x: number,
  y: number,
  userId: string
): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/token/move", {
    method: "POST",
    body: JSON.stringify({ tokenId, x, y, userId })
  });
}

export function updateMap(input: {
  userId: string;
  updates: Partial<GameMap>;
}): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/map", {
    method: "PATCH",
    body: JSON.stringify(input)
  });
}

export function updateMapLayer(input: {
  userId: string;
  layer: string;
  items: Record<string, unknown>[];
}): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/map/layers", {
    method: "PATCH",
    body: JSON.stringify(input)
  });
}

export function updateMapBackground(input: {
  userId: string;
  background: NonNullable<GameMap["background"]>;
}): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/map/background", {
    method: "PATCH",
    body: JSON.stringify(input)
  });
}

export function startCombat(input: {
  userId: string;
  participantIds?: string[] | null;
}): Promise<{ combat: GameState["combat"]; state: GameState }> {
  return request<{ combat: GameState["combat"]; state: GameState }>("/api/combat/start", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function endTurn(input: {
  userId: string;
  actorId?: string | null;
}): Promise<{ combat: GameState["combat"]; state: GameState }> {
  return request<{ combat: GameState["combat"]; state: GameState }>("/api/combat/end-turn", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function advanceTurn(input: {
  userId: string;
}): Promise<{ combat: GameState["combat"]; state: GameState }> {
  return request<{ combat: GameState["combat"]; state: GameState }>("/api/combat/advance-turn", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function advanceToPlayerTurn(input: {
  userId: string;
}): Promise<{ combat: GameState["combat"]; state: GameState }> {
  return request<{ combat: GameState["combat"]; state: GameState }>("/api/combat/advance-to-player-turn", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function spendSpellSlot(input: {
  userId: string;
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
  userId: string;
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
  userId: string;
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
  userId: string;
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

export function confirmPendingAction(input: {
  actionId: string;
  userId: string;
}): Promise<{ pendingAction: PendingAction; state: GameState }> {
  return request<{ pendingAction: PendingAction; state: GameState }>(
    `/api/pending-actions/${input.actionId}/confirm`,
    {
      method: "POST",
      body: JSON.stringify({ userId: input.userId })
    }
  );
}

export function declinePendingAction(input: {
  actionId: string;
  userId: string;
}): Promise<{ pendingAction: PendingAction; state: GameState }> {
  return request<{ pendingAction: PendingAction; state: GameState }>(
    `/api/pending-actions/${input.actionId}/decline`,
    {
      method: "POST",
      body: JSON.stringify({ userId: input.userId })
    }
  );
}

export function createCharacter(input: {
  userId: string;
  character: Character;
}): Promise<{ character: Character; state: GameState }> {
  return request<{ character: Character; state: GameState }>("/api/characters", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function updateCharacter(input: {
  characterId: string;
  userId: string;
  updates: Partial<Character>;
}): Promise<{ character: Character; state: GameState }> {
  return request<{ character: Character; state: GameState }>(`/api/characters/${input.characterId}`, {
    method: "PATCH",
    body: JSON.stringify({ userId: input.userId, updates: input.updates })
  });
}

export function getPermanentCharacters(): Promise<{ characters: Character[] }> {
  return request<{ characters: Character[] }>("/api/permanent-characters");
}

export function createPermanentCharacter(input: {
  userId: string;
  character: Character;
}): Promise<{ character: Character; characters: Character[] }> {
  return request<{ character: Character; characters: Character[] }>("/api/permanent-characters", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function updatePermanentCharacter(input: {
  characterId: string;
  userId: string;
  updates: Partial<Character>;
}): Promise<{ character: Character; characters: Character[] }> {
  return request<{ character: Character; characters: Character[] }>(
    `/api/permanent-characters/${input.characterId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ userId: input.userId, updates: input.updates })
    }
  );
}

export function rollDice(input: {
  expression: string;
  reason: string;
  rollerId?: string | null;
  advantage: DiceMode;
  userId: string;
}): Promise<{ result: DiceResult; state: GameState }> {
  return request<{ result: DiceResult; state: GameState }>("/api/dice", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function sendChat(input: {
  speaker: string;
  userId: string;
  message: string;
}): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function queryRules(input: {
  query: string;
  userId: string;
  k: number;
}): Promise<RagQueryResponse> {
  return request<RagQueryResponse>("/api/rag/query", {
    method: "POST",
    body: JSON.stringify(input)
  });
}
