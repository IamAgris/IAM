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

/**
 * IPLCI governance context. Set this once at the entry point (for example,
 * after a caller selects a registered source) and every API call inherits it.
 * Never invent a source id: an absent id means no rights assessment has run.
 */
export interface IPLCIGovernanceContext {
  sourceId?: string;
  datasetId?: string;
  approvalId?: string;
  agentId?: string;
  jurisdiction?: string;
}

let governanceContext: IPLCIGovernanceContext | null = null;

export function setIPLCIGovernanceContext(context: IPLCIGovernanceContext | null): void {
  governanceContext = context?.sourceId ? context : null;
}

api.interceptors.request.use((config) => {
  if (!governanceContext) return config;
  const headers = config.headers as unknown as Record<string, string>;
  const mapped: Record<string, string | undefined> = {
    "X-IPLCI-Source-Id": governanceContext.sourceId,
    "X-IPLCI-Dataset-Id": governanceContext.datasetId,
    "X-IPLCI-Approval-Id": governanceContext.approvalId,
    "X-IPLCI-Agent-Id": governanceContext.agentId,
    "X-IPLCI-Jurisdiction": governanceContext.jurisdiction,
  };
  for (const [header, value] of Object.entries(mapped)) {
    if (value) headers[header] = value;
  }
  return config;
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
  // Omitted by IAM clients so the backend applies the shared primary model.
  model?: string;
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
