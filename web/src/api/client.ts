import type { ChatResponse, DiceMode, DiceResult, GameState } from "./types";

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

export function moveToken(tokenId: string, x: number, y: number): Promise<{ state: GameState }> {
  return request<{ state: GameState }>("/api/token/move", {
    method: "POST",
    body: JSON.stringify({ tokenId, x, y })
  });
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
