export default function GovernancePage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Governance</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Authority Control Model</h2>
        <p className="text-muted-foreground text-sm">
          Four-level authority model: independent thinking, internal execution,
          external operations (policy-controlled), high-impact decisions (human authorization).
        </p>
        <div className="mt-6 space-y-3">
          <div className="p-4 bg-muted rounded-lg">
            <h3 className="font-medium mb-1">Level 1 — Independent Thinking</h3>
            <p className="text-xs text-muted-foreground">Autonomous: Research, learn, reason, plan</p>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <h3 className="font-medium mb-1">Level 2 — Internal Execution</h3>
            <p className="text-xs text-muted-foreground">Autonomous: Code, tests, internal files</p>
          </div>
          <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-100">
            <h3 className="font-medium text-yellow-900 mb-1">Level 3 — External Operations</h3>
            <p className="text-xs text-yellow-700">Policy-controlled: Publish, communicate, operate accounts</p>
          </div>
          <div className="p-4 bg-red-50 rounded-lg border border-red-100">
            <h3 className="font-medium text-red-900 mb-1">Level 4 — High-Impact Decisions</h3>
            <p className="text-xs text-red-700">Human authorization: Finance, contracts, security changes</p>
          </div>
        </div>
        <div className="mt-6 p-4 bg-muted rounded-lg">
          <h3 className="font-semibold mb-2">Immutable Security Boundaries</h3>
          <ul className="space-y-1 text-xs text-muted-foreground list-disc list-inside">
            <li>IAM cannot authorize its own financial limit increases</li>
            <li>IAM cannot disable its own security boundaries</li>
            <li>IAM cannot grant itself unrestricted access</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
