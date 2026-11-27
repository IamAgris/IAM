"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { secureGet } from "@/lib/secure-api";

const BASE = "/api/v1/iics";

type Item = Record<string, unknown>;

export default function IICSControlPanel() {
  const [scheduled, setScheduled] = useState<Item[]>([]);
  const [qa, setQa] = useState<Item[]>([]);
  const [advisories, setAdvisories] = useState<Item[]>([]);
  const [message, setMessage] = useState("");
  const [url, setUrl] = useState("https://example.com");
  const [action, setAction] = useState("browse_public");
  const [update, setUpdate] = useState("");

  const load = useCallback(async () => {
    try {
      const [s, q, a] = await Promise.all([
        secureGet(`${BASE}/scheduled`),
        secureGet(`${BASE}/qa/results`),
        secureGet(`${BASE}/security/advisories`),
      ]);
      setScheduled(Array.isArray(s.data) ? s.data : []);
      setQa(Array.isArray(q.data) ? q.data : []);
      setAdvisories(Array.isArray(a.data) ? a.data : []);
      setMessage("");
    } catch {
      setMessage("Unable to load IICS state (admin credential required).");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function post(path: string, body: unknown = {}) {
    try {
      const response = await api.post(`${BASE}${path}`, body);
      setMessage(JSON.stringify(response.data, null, 2));
      await load();
    } catch (error) {
      setMessage("Action rejected. Check credentials and permissions.");
    }
  }

  return (
    <main style={{ padding: 24, color: "var(--foreground, #eee)" }}>
      <h1>IAM Internet Control (IICS)</h1>
      <p>
        Local-first internet capability. Free lawful research is autonomous; consequential actions
        require a signed Creator decision. Email notifications are informational only.
      </p>

      <section style={{ marginTop: 20 }}>
        <h2>Egress / permission check</h2>
        <input value={url} onChange={(e) => setUrl(e.target.value)} aria-label="URL" />
        <input value={action} onChange={(e) => setAction(e.target.value)} aria-label="Action" />
        <button onClick={() => void post("/egress/check", { url })}>Check egress</button>
        <button onClick={() => void post("/authorize", { action_type: action, url })}>
          Authorize
        </button>
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Quality assurance</h2>
        <button onClick={() => void post("/qa/run")}>Run benchmarks</button>
        <ul>
          {qa.map((item, index) => (
            <li key={index}>
              {String(item.benchmark)} — {String(item.score)} / {String(item.threshold)} (
              {String(item.passed)})
            </li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Scheduled research</h2>
        <ul>
          {scheduled.map((item, index) => (
            <li key={index}>
              {String(item.task_id)} — {String(item.status)} — {String(item.query)}
            </li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Threat advisories</h2>
        <button onClick={() => void post("/security/advisories/ingest", { payload: {}, source: "osv" })}>
          Ingest empty feed
        </button>
        <ul>
          {advisories.map((item, index) => (
            <li key={index}>
              {String(item.cve_id)} — {String(item.severity)}
            </li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Creator email</h2>
        <input value={update} onChange={(e) => setUpdate(e.target.value)} aria-label="Update" />
        <button onClick={() => void post("/creator/notify", { update })}>Send status</button>
        <button
          onClick={() =>
            void post("/creator/approval-request", {
              action_type: "spend_money",
              summary: update || "Paid action",
            })
          }
        >
          Request signed approval
        </button>
        <p>Replying to these emails never grants authority.</p>
      </section>

      {message && <pre style={{ marginTop: 20, whiteSpace: "pre-wrap" }}>{message}</pre>}
    </main>
  );
}
