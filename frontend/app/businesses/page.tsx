export default function BusinessesPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Businesses</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Business Projects</h2>
        <p className="text-muted-foreground text-sm">
          Business opportunities and projects are managed via the backend API
          (Phase 8 — Economic Independence).
        </p>
      </div>
    </main>
  );
}
