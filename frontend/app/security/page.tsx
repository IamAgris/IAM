export default function SecurityPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Security</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Permissions & Approvals</h2>
        <p className="text-muted-foreground text-sm">
          Tool permissions, integration permissions, and approval requests are
          managed via the backend API at /api/v1/autonomy/tools/ and
          /api/v1/external-presence/approvals.
        </p>
      </div>
    </main>
  );
}
