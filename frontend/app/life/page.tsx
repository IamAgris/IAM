export default function LifePage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Life Management</h1>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-card border rounded-lg p-6">
          <h2 className="font-semibold mb-4">Current State</h2>
          <p className="text-muted-foreground text-sm">
            Daily self-management: decide when to work, research, learn, rest or conserve resources.
          </p>
          <div className="mt-4 p-4 bg-muted rounded-lg">
            <p className="text-xs text-muted-foreground mb-2">State: Idle</p>
            <p className="text-xs text-muted-foreground">Cycle: Active</p>
          </div>
        </div>
        <div className="bg-card border rounded-lg p-6">
          <h2 className="font-semibold mb-4">Long-Term Goals</h2>
          <p className="text-muted-foreground text-sm">
            Maintain goals over weeks, months and years with priority management.
          </p>
        </div>
        <div className="bg-card border rounded-lg p-6">
          <h2 className="font-semibold mb-4">Life History</h2>
          <p className="text-muted-foreground text-sm">
            Chronological record of important experiences, decisions and achievements.
          </p>
        </div>
      </div>
    </main>
  );
}
