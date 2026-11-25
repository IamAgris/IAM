export default function MemoryPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Memory</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Long-Term Memory</h2>
        <p className="text-muted-foreground text-sm">
          Memory persistence is handled via the backend API. View and manage
          memories at /api/v1/memory/ through the API docs.
        </p>
      </div>
    </main>
  );
}
