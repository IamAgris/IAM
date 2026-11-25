export default function CapabilitiesPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Capabilities</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Capability Development Registry</h2>
        <p className="text-muted-foreground text-sm">
          Catalogue of what IAM can do, cannot do, and wants to learn. Each capability
          requires measurable tests — not just reading about something.
        </p>
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-muted rounded-lg">
            <h3 className="font-medium mb-2">Programming</h3>
            <p className="text-xs text-muted-foreground">Proficiency: 0%</p>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <h3 className="font-medium mb-2">Languages</h3>
            <p className="text-xs text-muted-foreground">Proficiency: 0%</p>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <h3 className="font-medium mb-2">Business</h3>
            <p className="text-xs text-muted-foreground">Proficiency: 0%</p>
          </div>
        </div>
      </div>
    </main>
  );
}
