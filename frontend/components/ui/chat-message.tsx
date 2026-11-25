"use client";

import { User, Bot, MessageCircle, Clock } from "lucide-react";

interface ChatMessageProps {
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  createdAt?: string;
}

export function ChatMessage({ role, content, createdAt }: ChatMessageProps) {
  const isUser = role === "user";
  const isAssistant = role === "assistant";

  const icon = isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />;
  const bgClass = isUser
    ? "bg-aura-600 text-white"
    : isAssistant
      ? "bg-muted text-foreground"
      : "bg-muted/50 text-muted-foreground";
  const alignClass = isUser ? "ml-auto" : "mr-auto";

  return (
    <div className={`flex items-start gap-3 mb-4 ${alignClass}`}>
      {isUser ? (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-bold">
          <User className="w-4 h-4" />
        </div>
      ) : (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted text-foreground flex items-center justify-center text-xs">
          <Bot className="w-4 h-4" />
        </div>
      )}
      <div className="max-w-[80%]">
        <div className={`rounded-lg p-3 whitespace-pre-wrap text-sm ${bgClass}`}>
          {content}
        </div>
        {createdAt && (
          <div className="text-[10px] text-muted-foreground mt-1 text-right">
            {new Date(createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </div>
        )}
      </div>
    </div>
  );
}
