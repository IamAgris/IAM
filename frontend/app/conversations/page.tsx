"use client";

import { conversations } from "@/lib/api-conversations";
import Link from "next/link";
import { useState, useEffect } from "react";
import { ArrowRight, Trash2, Clock, MessageCircle } from "lucide-react";

export default function ConversationsPage() {
  const [conversationsList, setConversationsList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConversations = async () => {
    try {
      setLoading(true);
      const data = await conversations.list();
      setConversationsList(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  };

  const deleteConversation = async (id: string) => {
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await conversations.del(id);
      setConversationsList((prev) => prev.filter((c) => c.id !== id));
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete conversation");
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin"></div>
          <span className="text-sm text-gray-600">Loading conversations...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md p-6 bg-white rounded-lg shadow-sm border border-gray-200 text-center">
          <Trash2 className="w-8 h-8 mx-auto mb-3 text-red-500" />
          <h3 className="text-lg font-medium text-gray-900">Error loading conversations</h3>
          <p className="text-sm text-gray-500 mb-4">{error}</p>
          <button
            onClick={() => loadConversations()}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (conversationsList.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md p-8 bg-white rounded-lg shadow-sm border border-gray-200 text-center">
          <MessageCircle className="w-8 h-8 mx-auto mb-3 text-gray-400" />
          <h3 className="text-lg font-medium text-gray-900">No conversations yet</h3>
          <p className="text-sm text-gray-500 mb-6">
            Start a new conversation with IAM to begin.
          </p>
          <Link href="/" className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium">
            Start new conversation
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Conversations</h1>
            <p className="mt-1 text-sm text-gray-600">
              Your past conversations with IAM
            </p>
          </div>
          <Link
            href="/"
            className="mt-4 sm:mt-0 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            <ArrowRight className="w-4 h-4 mr-2" /> New conversation
          </Link>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 sm:gap-0">
            <h2 className="text-sm font-medium text-gray-900">Conversations</h2>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-500">{conversationsList.length} conversation{conversationsList.length !== 1 ? "s" : ""}</span>
            </div>
          </div>
          <ul className="divide-y divide-gray-100">
            {conversationsList.map((conv) => (
              <li key={conv.id}>
                <Link
                  href={`/conversations/${conv.id}`}
                  className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <MessageCircle className="w-5 h-5 text-gray-400" />
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">
                        {conv.title || "Untitled conversation"}
                      </h3>
                      <p className="text-xs text-gray-500">
                        {conv.created_at ? new Date(conv.created_at).toLocaleDateString() : ""}
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}