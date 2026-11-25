export default function DevelopmentPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Development</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Self-Development</h2>
        <p className="text-muted-foreground text-sm">
          Software projects, code changes, and experiments are managed via the
          backend API at /api/v1/autonomy/ endpoints.
        </p>
      </div>
    </main>
  );
}
