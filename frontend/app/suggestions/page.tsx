"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type SuggestionMode = "focus" | "recall" | "create";
type ModeGroup = { mode: SuggestionMode; title: string; description: string };
type PublicNode = { text: string; type: string };

const MODES: ModeGroup[] = [
  { mode: "focus", title: "Focus", description: "Explore a topic or plan something new." },
  { mode: "recall", title: "Recall", description: "Look back at what has been discussed or learned." },
  { mode: "create", title: "Create", description: "Draft, design or brainstorm something." },
];

const FALLBACK: Record<SuggestionMode, string[]> = {
  focus: ["Research something", "Explain a complex topic simply", "Plan a project"],
  recall: ["What have you learned lately?", "Summarize what we discussed"],
  create: ["Help me create something", "Design a small project plan"],
};

export default function SuggestionsPage() {
  const [suggestions, setSuggestions] = useState<Record<SuggestionMode, string[]>>({
    focus: [], recall: [], create: [],
  });
  const [nodes, setNodes] = useState<PublicNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const load = async () => {
      const byMode: Record<SuggestionMode, string[]> = {
        focus: FALLBACK.focus,
        recall: FALLBACK.recall,
        create: FALLBACK.create,
      };
      for (const mode of ["focus", "recall", "create"] as SuggestionMode[]) {
        try {
          const response = await api.get<{ suggestions?: string[] }>(
            "/api/v1/interface/suggestions",
            { params: { mode } }
          );
          if (response.data?.suggestions?.length) {
            byMode[mode] = response.data.suggestions;
          }
        } catch {
          // Fallback prompts are already in place.
        }
      }
      let publicNodes: PublicNode[] = [];
      try {
        const response = await api.get<PublicNode[]>("/api/v1/interface/nodes");
        if (Array.isArray(response.data)) publicNodes = response.data;
      } catch {
        // Keep the empty list.
      }
      if (active) {
        setSuggestions(byMode);
        setNodes(publicNodes);
        setLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, []);

  return (
    <main className="h-[100dvh] overflow-y-auto p-4 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Suggestions</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Open prompts for working with IAM. Public endpoints — no account required.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading suggestions...</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {MODES.map(({ mode, title, description }) => (
            <section key={mode} className="rounded-2xl border border-border bg-card p-4 space-y-3">
              <div>
                <h2 className="font-medium">{title}</h2>
                <p className="text-xs text-muted-foreground">{description}</p>
              </div>
              <ul className="space-y-2 text-sm">
                {suggestions[mode].map((suggestion) => (
                  <li key={suggestion} className="rounded-lg bg-muted px-3 py-2">{suggestion}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      <section className="rounded-2xl border border-border bg-card p-4 space-y-3">
        <h2 className="font-medium">Public knowledge nodes</h2>
        <div className="flex flex-wrap gap-2">
          {nodes.map((node, index) => (
            <span key={`${node.type}-${node.text}-${index}`} className="rounded-full border border-border px-3 py-1 text-xs">
              {node.text}
            </span>
          ))}
        </div>
      </section>
    </main>
  );
}
