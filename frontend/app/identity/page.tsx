export default function IdentityPage() {
  return (
    <main className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Identity</h1>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border rounded-lg p-6">
            <h2 className="font-semibold mb-4">Digital Identity</h2>
            <div className="text-muted-foreground text-sm">
              Identity initialization pending. Create the AI's digital name and
              profile from the backend identity endpoint.
            </div>
          </div>
        </div>
        <div className="bg-muted rounded-lg p-6">
          <h3 className="font-semibold mb-4">Profile</h3>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>Name: —</p>
            <p>Avatar: —</p>
            <p>Status: Not initialized</p>
          </div>
        </div>
      </div>
    </main>
  );
}
