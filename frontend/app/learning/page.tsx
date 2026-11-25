export default function LearningPage() {
  return (
    <main className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Learning</h1>
      </div>
      <div className="bg-card border rounded-lg p-6">
        <h2 className="font-semibold mb-4">Language & Skills</h2>
        <p className="text-muted-foreground text-sm">
          Language proficiency and skills are managed via the backend API at
          /api/v1/languages/ and /api/v1/skills/ endpoints.
        </p>
      </div>
    </main>
  );
}
