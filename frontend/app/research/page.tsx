"use client";

import React from "react";
import { Search, Globe, ShieldCheck, Save, Clock } from "lucide-react";
import { api } from "@/lib/api";

interface Source {
  index: number;
  url: string;
  title: string;
  snippet: string;
  credibility_score: number;
  fetched_at?: string;
}

interface Finding {
  source: string;
  title: string;
  content_preview: string;
  credibility_score: number;
}

export default function ResearchPage() {
  const [query, setQuery] = React.useState("");
  const [results, setResults] = React.useState<{
    query: string;
    sources: Source[];
    findings: Finding[];
    credibility_score: number;
    source_count: number;
    started_at?: string;
    completed_at?: string;
  } | null>(null);
  const [isResearching, setIsResearching] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleResearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsResearching(true);
    setError(null);

    try {
      const response = await api.post("/api/v1/research/", {
        query,
        store_as_memory: true,
        store_as_knowledge: false,
        max_results: 10,
      });
      setResults(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Research failed");
    } finally {
      setIsResearching(false);
    }
  };

  return (
    <main className="p-4 lg:p-8 space-y-6">
      <header>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Globe className="w-6 h-6" /> Web Research
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Search, browse, extract, and store findings with source provenance.
          All results treated as untrusted until verified.
        </p>
      </header>

      <form onSubmit={handleResearch} className="bg-card border rounded-lg p-6">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-2">Research Query</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. quantum computing breakthroughs 2026"
              className="w-full px-4 py-2 rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <button
            type="submit"
            disabled={isResearching || !query.trim()}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition flex items-center gap-2"
          >
            {isResearching ? (
              <>
                <Clock className="w-4 h-4 animate-spin" /> Researching...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" /> Start Research
              </>
            )}
          </button>
        </div>
        {error && (
          <div className="mt-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
            {error}
          </div>
        )}
      </form>

      {results && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Results for "{results.query}"</h2>
            <div className="flex items-center gap-2 text-sm">
              <ShieldCheck className="w-4 h-4" />
              <span>
                Credibility: {(results.credibility_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <div className="grid gap-4">
            <div className="col-span-1 lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-muted rounded-lg p-4">
                <div className="text-xs text-muted-foreground uppercase font-semibold mb-1">Sources</div>
                <div className="text-xl font-bold">{results.source_count}</div>
              </div>
              <div className="bg-muted rounded-lg p-4">
                <div className="text-xs text-muted-foreground uppercase font-semibold mb-1">Findings</div>
                <div className="text-xl font-bold">{results.findings.length}</div>
              </div>
              <div className="bg-muted rounded-lg p-4">
                <div className="text-xs text-muted-foreground uppercase font-semibold mb-1">Stored in Memory</div>
                <div className="text-xl font-bold">Yes</div>
              </div>
            </div>
          </div>

          <div className="grid gap-4">
            {results.sources.map((source) => (
              <div
                key={source.index}
                className="bg-card border rounded-lg p-4 hover:border-primary/50 transition"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold">{source.title}</h3>
                  <span className={`text-xs px-2 py-1 rounded ${
                    source.credibility_score >= 0.7
                      ? "bg-green-100 text-green-800"
                      : source.credibility_score >= 0.4
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-red-100 text-red-800"
                  }`}>
                    {(source.credibility_score * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mb-2">{source.snippet}</p>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline break-all"
                >
                  {source.url}
                </a>
              </div>
            ))}
          </div>

          <div className="bg-muted rounded-lg p-4">
            <h3 className="font-semibold mb-2">Findings Stored in Memory</h3>
            <div className="space-y-2">
              {results.findings.map((f, i) => (
                <div key={i} className="text-sm p-2 bg-background/50 rounded">
                  <p className="font-medium">{f.title}</p>
                  <p className="text-muted-foreground truncate">{f.content_preview}</p>
                  <div className="flex justify-between items-center mt-1">
                    <span className="text-xs text-muted-foreground">{f.source}</span>
                    <span className="text-xs">
                      Confidence: {(f.credibility_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
