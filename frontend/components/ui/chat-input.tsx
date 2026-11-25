"use client";

import React from "react";
import { Send, Mic, Paperclip } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled = false, placeholder = "Type a message..." }: ChatInputProps) {
  const [text, setText] = React.useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full gap-2 p-3 bg-card border-t border-input">
      <Mic className="w-5 h-5 text-muted-foreground hover:text-foreground cursor-pointer" />
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 px-4 py-2 rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
      />
      <Paperclip className="w-5 h-5 text-muted-foreground hover:text-foreground cursor-pointer" />
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition"
      >
        <Send className="w-4 h-4" />
      </button>
    </form>
  );
}
