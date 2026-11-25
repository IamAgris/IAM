"use client";

import React from "react";
import { MessageCircle } from "lucide-react";
import { ChatMessage, ChatInput } from "@/components/ui";
import { api, ChatMessage as ChatMessageAPI } from "@/lib/api";

export default function ConversationsPage() {
  const [messages, setMessages] = React.useState<{
    role: string;
    content: string;
    created_at?: string;
  }[]>([]);
  const [inputValue, setInputValue] = React.useState("");
  const [isSending, setIsSending] = React.useState(false);
  const [conversationId, setConversationId] = React.useState<string | null>(null);

  React.useEffect(() => {
    loadMessages();
  }, []);

  async function loadMessages() {
    try {
      // TODO: Fetch conversation messages from backend
      // const { data } = await api.get(`/api/v1/conversations/${conversationId}/messages`);
      // setMessages(data);
    } catch (error) {
      console.error("Failed to load messages:", error);
    }
  }

  async function handleSend(content: string) {
    if (!content.trim()) return;

    const optimisticMessage = {
      role: "user" as const,
      content,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticMessage]);
    setInputValue("");
    setIsSending(true);

    try {
      // Send to LiteLLM via backend proxy
      const response = await api.post("/api/v1/models/chat", {
        model: "qwen3.5-9b",
        messages: [
          ...messages.map((m) => ({ role: m.role, content: m.content })),
          { role: "user", content },
        ],
        temperature: 0.7,
      });

      const assistantContent =
        response.data?.choices?.[0]?.message?.content ||
        response.data?.response ||
        "I received your message but couldn't generate a response.";

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: assistantContent, created_at: new Date().toISOString() },
      ]);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to send message";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errorMessage}`, created_at: new Date().toISOString() },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="p-4 lg:p-8 h-screen flex flex-col">
      <header className="flex items-center justify-between mb-6 border-b border-input pb-4">
        <div>
          <h1 className="text-2xl font-bold">Conversations</h1>
          <p className="text-sm text-muted-foreground">Chat with Project AURA</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-xs text-muted-foreground">AURA online</span>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto space-y-4 p-4 bg-background/50 rounded-lg border border-border/50">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <svg className="w-16 h-16 mb-4 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <MessageCircle strokeWidth={1.5} />
            </svg>
            <p>No messages yet. Start a conversation with AURA.</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <ChatMessage
              key={i}
              role={msg.role as "user" | "assistant" | "system" | "tool"}
              content={msg.content}
              createdAt={msg.created_at}
            />
          ))
        )}
      </div>

      <ChatInput
        onSend={handleSend}
        disabled={isSending}
        placeholder="Ask AURA anything..."
      />
    </main>
  );
}
