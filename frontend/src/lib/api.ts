const API_BASE = typeof window !== "undefined" ? window.location.origin : "";

type FetchOptions = RequestInit & { json?: unknown };

async function request<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { json, headers, ...rest } = options;
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : undefined,
    ...rest,
  });

  if (!response.ok) {
    const detail = await response
      .json()
      .then((data) => data.detail)
      .catch(() => null);
    throw new Error(typeof detail === "string" ? detail : `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export type SessionUser = {
  user_id: number;
  username: string;
};

export async function signup(username: string, password: string): Promise<SessionUser> {
  return request("/api/auth/signup", { method: "POST", json: { username, password } });
}

export async function login(username: string, password: string): Promise<SessionUser> {
  return request("/api/auth/login", { method: "POST", json: { username, password } });
}

export async function logout(): Promise<void> {
  await request("/api/auth/logout", { method: "POST" });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await request("/api/auth/change-password", {
    method: "POST",
    json: { currentPassword, newPassword },
  });
}

export async function me(): Promise<SessionUser> {
  return request("/api/auth/me");
}

export type BoardRole = "owner" | "editor";

export type BoardSummary = {
  id: number;
  name: string;
  role: BoardRole;
  updated_at: string;
};

export async function listBoards(): Promise<BoardSummary[]> {
  return request("/api/boards");
}

export async function createBoard(name: string): Promise<BoardSummary> {
  return request("/api/boards", { method: "POST", json: { name } });
}

export async function renameBoard(boardId: number, name: string): Promise<{ id: number; name: string }> {
  return request(`/api/boards/${boardId}`, { method: "PATCH", json: { name } });
}

export async function deleteBoard(boardId: number): Promise<void> {
  await request(`/api/boards/${boardId}`, { method: "DELETE" });
}

export type BoardMember = {
  user_id: number;
  username: string;
  role: BoardRole;
};

export async function listBoardMembers(boardId: number): Promise<BoardMember[]> {
  return request(`/api/boards/${boardId}/members`);
}

export async function addBoardMember(
  boardId: number,
  username: string,
  role: BoardRole = "editor"
): Promise<BoardMember> {
  return request(`/api/boards/${boardId}/members`, { method: "POST", json: { username, role } });
}

export async function removeBoardMember(boardId: number, userId: number): Promise<void> {
  await request(`/api/boards/${boardId}/members/${userId}`, { method: "DELETE" });
}

export async function getBoardState(boardId: number) {
  const data = await request<{ state: string }>(`/api/boards/${boardId}/state`);
  try {
    return JSON.parse(data.state);
  } catch {
    throw new Error("Failed to parse board state");
  }
}

export async function saveBoardState(boardId: number, state: object): Promise<void> {
  await request(`/api/boards/${boardId}/state`, {
    method: "POST",
    json: { state: JSON.stringify(state) },
  });
}

export type ActivityEntry = {
  id: number;
  board_id: number;
  user_id: number | null;
  username: string | null;
  action: string;
  details: unknown;
  created_at: string;
};

export async function getActivity(boardId: number): Promise<ActivityEntry[]> {
  return request(`/api/boards/${boardId}/activity`);
}

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export async function aiChat(boardId: number, prompt: string, messages?: ChatMessage[]) {
  const data = await request<{
    message: string;
    boardState: string;
    applied: boolean;
    confidence?: number;
  }>("/api/ai/chat", {
    method: "POST",
    json: { boardId, prompt, messages },
  });

  let board: unknown;
  try {
    board = JSON.parse(data.boardState);
  } catch {
    board = null;
  }
  return {
    message: data.message,
    applied: Boolean(data.applied),
    confidence: typeof data.confidence === "number" ? data.confidence : undefined,
    board,
  };
}
