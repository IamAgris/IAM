export default function AutonomyPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Autonomy</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Autonomous Operations</h2>
        <p className="text-muted-foreground text-sm">
          Goals, tasks, decisions, and tools are managed via the backend API at
          /api/v1/autonomy/ endpoints. Check worker status at
          /api/v1/autonomy/status.
        </p>
      </div>
    </main>
  );
}
