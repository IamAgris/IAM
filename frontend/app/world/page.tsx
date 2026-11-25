export default function WorldModelPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">World Model</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Internal World Representation</h2>
        <p className="text-muted-foreground text-sm">
          Tracks people, organisations, countries, technologies, cause-and-effect,
          and IAM's own capabilities and limitations.
        </p>
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-muted rounded-lg">
            <h3 className="font-medium mb-2">Entities</h3>
            <p className="text-xs text-muted-foreground">World entities tracked</p>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <h3 className="font-medium mb-2">Relationships</h3>
            <p className="text-xs text-muted-foreground">Entity connections</p>
          </div>
        </div>
      </div>
    </main>
  );
}
