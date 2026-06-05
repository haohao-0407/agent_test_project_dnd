import type {
  Character,
  ChatResponse,
  DiceMode,
  DiceResult,
  GameMap,
  GameState,
  RagQueryResponse
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
