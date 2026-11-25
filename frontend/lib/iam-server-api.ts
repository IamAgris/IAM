/**
 * Server-only Data Access Layer for IAM backend reads.
 *
 * The API credential is read from a server environment variable and never
 * reaches the browser. Only Server Components should import this module.
 */

const API_URL = process.env.IAM_API_URL || "http://localhost:8000";
const API_KEY = process.env.IAM_USER_API_KEY || "";

export const iamConfigured = Boolean(API_KEY);

async function getJson<T>(path: string): Promise<T | null> {
  if (!API_KEY) return null;
  try {
    const response = await fetch(`${API_URL}${path}`, {
      headers: { Authorization: `Bearer ${API_KEY}` },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export type CapabilityDTO = {
  id: string;
  name: string;
  category: string;
  description: string | null;
  target_proficiency: number;
  current_proficiency: number;
  last_assessed: string | null;
};

export type SkillDTO = {
  id: string;
  name: string;
  category: string | null;
  proficiency_level: number;
  description: string | null;
  acquired_at: string | null;
  last_practiced_at: string | null;
};

export type LanguageDTO = {
  language_code: string;
  vocabulary_level: number;
  conversational_ability: number;
  updated_at: string | null;
};

export async function getCapabilities(): Promise<CapabilityDTO[]> {
  return (await getJson<CapabilityDTO[]>("/api/v1/capabilities")) ?? [];
}

export async function getSkills(): Promise<SkillDTO[]> {
  return (await getJson<SkillDTO[]>("/api/v1/skills/")) ?? [];
}

export async function getLanguages(): Promise<LanguageDTO[]> {
  return (await getJson<LanguageDTO[]>("/api/v1/languages/")) ?? [];
}

export type IdentityDTO = {
  id: string;
  name: string;
  description: string | null;
  avatar_url: string | null;
  communication_preferences: Record<string, unknown>;
  interests: string[];
  personal_goals: string[];
  created_at: string | null;
  updated_at: string | null;
};

export type MemoryDTO = {
  id: string;
  content: string;
  memory_type: string;
  source: string | null;
  confidence_level: number;
  topic: string | null;
  created_at: string | null;
};

export type ConversationDTO = {
  id: string;
  title: string | null;
  started_at: string | null;
  ended_at: string | null;
  metadata: Record<string, unknown>;
};

export async function getIdentity(): Promise<IdentityDTO | null> {
  return getJson<IdentityDTO>("/api/v1/identity/");
}

export async function getMemories(): Promise<MemoryDTO[]> {
  return (await getJson<MemoryDTO[]>("/api/v1/memory/")) ?? [];
}

export async function getConversations(): Promise<ConversationDTO[]> {
  return (await getJson<ConversationDTO[]>("/api/v1/conversations/")) ?? [];
}

export type SuggestionMode = "focus" | "recall" | "create";

export async function getSuggestions(
  mode: SuggestionMode
): Promise<string[]> {
  const data = await getJson<{ suggestions?: string[] }>(
    `/api/v1/interface/suggestions?mode=${mode}`
  );
  return data?.suggestions ?? [];
}

export type PublicNodeDTO = { text: string; type: string };

export async function getPublicNodes(): Promise<PublicNodeDTO[]> {
  const data = await getJson<{ nodes?: PublicNodeDTO[] }>("/api/v1/interface/nodes");
  return data?.nodes ?? [];
}
