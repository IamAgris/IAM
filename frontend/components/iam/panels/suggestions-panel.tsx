import {
  getPublicNodes,
  getSuggestions,
  iamConfigured,
  type SuggestionMode,
} from "@/lib/iam-server-api";

const MODES: { mode: SuggestionMode; title: string; description: string }[] = [
  {
    mode: "focus",
    title: "Focus",
    description: "Explore a topic or plan something new.",
  },
  {
    mode: "recall",
    title: "Recall",
    description: "Look back at what has been discussed or learned.",
  },
  {
    mode: "create",
    title: "Create",
    description: "Draft, design or brainstorm something.",
  },
];

export default async function SuggestionsPanel() {
  const [focus, recall, create, nodes] = await Promise.all([
    getSuggestions("focus"),
    getSuggestions("recall"),
    getSuggestions("create"),
    getPublicNodes(),
  ]);
  const groups = { focus, recall, create };

  return (
    <main className="h-[100dvh] overflow-y-auto p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Suggestions</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Open prompts for working with IAM.
          </p>
        </div>
        <span className="text-xs text-muted-foreground">
          {iamConfigured ? "Live data" : "Backend not configured"}
        </span>
      </div>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {MODES.map(({ mode, title, description }) => (
          <article key={mode} className="bg-card border rounded-lg p-6 space-y-4">
            <div>
              <h2 className="font-semibold">{title}</h2>
              <p className="text-xs text-muted-foreground mt-1">{description}</p>
            </div>
            <ul className="space-y-2">
              {(groups[mode] ?? []).map((suggestion) => (
                <li key={suggestion} className="text-sm bg-muted rounded px-3 py-2">
                  {suggestion}
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      <section className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold">Public knowledge nodes</h2>
        <p className="text-xs text-muted-foreground mt-1">
          Permission-filtered topics safe for public display.
        </p>
        <div className="flex flex-wrap gap-2 mt-4">
          {nodes.map((node, index) => (
            <span
              key={`${node.text}-${index}`}
              className="text-xs bg-muted rounded-full px-3 py-1"
            >
              {node.text}
            </span>
          ))}
        </div>
      </section>
    </main>
  );
}
