export default function ReflectionPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Reflection</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Reflection Engine</h2>
        <p className="text-muted-foreground text-sm">
          Review decisions and experiences, evaluate outcomes, identify lessons learned,
          and update operating principles.
        </p>
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-muted rounded-lg">
            <h3 className="font-medium mb-2">Recent Reflections</h3>
            <p className="text-xs text-muted-foreground">No reflections recorded yet</p>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <h3 className="font-medium mb-2">Operating Principles</h3>
            <p className="text-xs text-muted-foreground">Safety, legal, security, operational, personal</p>
          </div>
        </div>
      </div>
    </main>
  );
}
