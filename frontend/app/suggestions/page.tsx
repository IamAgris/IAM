import {
  getPublicNodes,
  getSuggestions,
  iamConfigured,
  type SuggestionMode,
} from "@/lib/iam-server-api";

export const dynamic = "force-dynamic";

const MODES: { mode: SuggestionMode; title: string; description: string }[] = [
  { mode: "focus", title: "Focus", description: "Explore a topic or plan something new." },
  { mode: "recall", title: "Recall", description: "Look back at what has been discussed or learned." },
  { mode: "create", title: "Create", description: "Draft, design or brainstorm something." },
];

export default async function SuggestionsPage() {
  const [focus, recall, create, nodes] = await Promise.all([
    getSuggestions("focus"),
    getSuggestions("recall"),
    getSuggestions("create"),
    getPublicNodes(),
  ]);
  const byMode: Record<SuggestionMode, string[]> = { focus, recall, create };

  return (
    <main className="h-[100dvh] overflow-y-auto p-4 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Suggestions</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Open prompts for working with IAM. {iamConfigured ? "" : "IAM is running in local mode."}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {MODES.map(({ mode, title, description }) => (
          <section key={mode} className="rounded-2xl border border-border bg-card p-4 space-y-3">
            <div>
              <h2 className="font-medium">{title}</h2>
              <p className="text-xs text-muted-foreground">{description}</p>
            </div>
            <ul className="space-y-2 text-sm">
              {(byMode[mode] || []).map((suggestion) => (
                <li key={suggestion} className="rounded-lg bg-muted px-3 py-2">{suggestion}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <section className="rounded-2xl border border-border bg-card p-4 space-y-3">
        <h2 className="font-medium">Public knowledge nodes</h2>
        <div className="flex flex-wrap gap-2">
          {nodes.map((node) => (
            <span key={`${node.type}-${node.text}`} className="rounded-full border border-border px-3 py-1 text-xs">
              {node.text}
            </span>
          ))}
        </div>
      </section>
    </main>
  );
}
