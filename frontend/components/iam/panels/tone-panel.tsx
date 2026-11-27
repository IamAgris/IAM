"use client";

import React, { useState } from "react";

type Analysis = {
  tone: string;
  register: string;
  sentiment: number;
  confidence: number;
  signals: Array<{ pattern: string; interpretation: string }>;
  manipulation_indicators: string[];
  interpretations: string[];
  caveat: string;
  note: string;
};

export default function TonePanel() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function analyse() {
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/iam-proxy/api/v1/tone/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Analysis failed");
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="ml-64 p-8 max-w-4xl">
      <h1 className="text-2xl font-bold mb-2">Tone &amp; Influence Intelligence</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Defensive recognition of tone and influence patterns. Results are possibilities,
        not psychological diagnoses, and never claims about a private mental state.
      </p>

      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Paste public text to analyse…"
        className="w-full h-40 p-3 rounded-lg border border-input bg-background text-sm"
      />
      <button
        onClick={analyse}
        disabled={loading || !text.trim()}
        className="mt-3 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm disabled:opacity-50"
      >
        {loading ? "Analysing…" : "Analyse"}
      </button>

      {error && <p className="mt-4 text-sm text-red-500">{error}</p>}

      {result && (
        <section className="mt-6 space-y-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Metric label="Tone" value={result.tone} />
            <Metric label="Register" value={result.register} />
            <Metric label="Sentiment" value={String(result.sentiment)} />
            <Metric label="Confidence" value={String(result.confidence)} />
          </div>

          <div className="rounded-lg border border-input p-4">
            <h2 className="font-semibold mb-2">Observable patterns</h2>
            {result.signals.length === 0 ? (
              <p className="text-sm text-muted-foreground">No strong pattern detected.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {result.signals.map((signal, index) => (
                  <li key={index}>
                    <span className="font-medium">{signal.pattern}</span> → {signal.interpretation}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-lg border border-input p-4">
            <h2 className="font-semibold mb-2">Manipulation indicators</h2>
            {result.manipulation_indicators.length === 0 ? (
              <p className="text-sm text-muted-foreground">None flagged.</p>
            ) : (
              <p className="text-sm">{result.manipulation_indicators.join(", ")}</p>
            )}
          </div>

          <p className="text-xs text-muted-foreground">{result.caveat}</p>
          <p className="text-xs text-muted-foreground">{result.note}</p>
        </section>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-input p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-mono text-sm">{value}</p>
    </div>
  );
}
