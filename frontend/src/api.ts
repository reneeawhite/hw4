import type { Product } from "./types";

export const API_BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? `API request failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
}

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    name: string;
    email: string;
    first_name: string | null;
    last_name: string | null;
  };
};

export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
  product_ids?: string[];
};

export type ChatResponse = {
  reply: string;
  products: Product[];
};

export type PageContext = {
  path: string;
  current_product_id?: string;
};

export type ChatHistoryResponse = {
  messages: Array<ChatTurn & { products?: Product[] }>;
};

export function fetchProducts(): Promise<Product[]> {
  return request<Product[]>("/api/products");
}

export function fetchProduct(productId: string): Promise<Product> {
  return request<Product>(`/api/products/${encodeURIComponent(productId)}`);
}

export function registerUser(payload: {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  confirm_password: string;
}): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function loginUser(payload: { email: string; password: string }): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function sendChatMessage(payload: {
  message: string;
  history?: ChatTurn[];
  page_context: PageContext;
}, accessToken?: string): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify(payload),
  });
}

export function fetchChatHistory(accessToken: string): Promise<ChatHistoryResponse> {
  return request<ChatHistoryResponse>("/api/chat/history", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function productImageUrl(path: string): string {
  if (path.startsWith("http")) return path;
  const separator = path.includes("?") ? "&" : "?";
  return `${API_BASE_URL}${path}${separator}v=hw4-p10-mask-v2`;
}
