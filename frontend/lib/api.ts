import axios from "axios";

// Same-origin relative base — Next.js rewrites /api/* to the backend.
// This avoids CORS entirely and keeps provider keys/backend hidden from the browser.
const API_BASE_URL = "";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export interface ChatMessage {
  role: "user" | "assistant" | "system" | "tool";
  content: string;
}

export interface ModelChatRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
}

export async function chatCompletion(request: ModelChatRequest) {
  const { data } = await api.post("/api/v1/models/chat", request);
  return data;
}

export async function listModels() {
  const { data } = await api.get("/api/v1/models/");
  return data;
}

export async function healthCheck() {
  const { data } = await api.get("/health");
  return data;
}
