/**
 * Client-side conversation API used by the conversation history page.
 *
 * Uses the same relative axios client as the rest of the app so /api/* is
 * rewritten to the backend without CORS or exposed provider keys.
 */
import { api, type Conversation } from "./api";

export const conversations = {
  async list(): Promise<Conversation[]> {
    const { data } = await api.get<Conversation[]>("/api/v1/conversations/");
    return Array.isArray(data) ? data : [];
  },

  async get(conversationId: string): Promise<Conversation> {
    const { data } = await api.get<Conversation>(
      `/api/v1/conversations/${conversationId}`
    );
    return data;
  },

  async del(conversationId: string): Promise<void> {
    await api.delete(`/api/v1/conversations/${conversationId}`);
  },
};
