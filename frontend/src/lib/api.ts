const API_BASE = typeof window !== "undefined" ? window.location.origin : "";

export async function authUser(username: string, password: string) {
  const response = await fetch(`${API_BASE}/api/auth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error("Authentication failed");
  }

  return response.json();
}

export async function getBoard(userId: number) {
  const response = await fetch(`${API_BASE}/api/board?user_id=${userId}`);

  if (!response.ok) {
    throw new Error("Failed to fetch board state");
  }

  const data = await response.json();
  return JSON.parse(data.state);
}

export async function saveBoard(userId: number, state: object) {
  const response = await fetch(`${API_BASE}/api/board?user_id=${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state: JSON.stringify(state) }),
  });

  if (!response.ok) {
    throw new Error("Failed to save board state");
  }

  return response.json();
}

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export async function aiChat(userId: number, prompt: string, messages?: ChatMessage[]) {
  const response = await fetch(`${API_BASE}/api/ai/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userId, prompt, messages }),
  });

  if (!response.ok) {
    throw new Error("Failed to chat with AI");
  }

  const data = await response.json();
  return {
    message: data.message as string,
    applied: Boolean(data.applied),
    confidence: typeof data.confidence === "number" ? (data.confidence as number) : undefined,
    board: JSON.parse(data.boardState) as unknown,
  };
}
