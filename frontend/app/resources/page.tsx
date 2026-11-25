export default function ResourcesPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Resources</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Computing & Model Usage</h2>
        <p className="text-muted-foreground text-sm">
          Resource metrics and model usage are tracked via the backend API
          (Phase 7 — Self-Evolution).
        </p>
      </div>
    </main>
  );
}
