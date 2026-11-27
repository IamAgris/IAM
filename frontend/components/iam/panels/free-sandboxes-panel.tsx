"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { secureGet } from "@/lib/secure-api";

const BASE = "/api/v1/free-sandboxes";

export default function FreeSandboxesPanel() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [providers, setProviders] = useState<unknown[]>([]);
  const [environments, setEnvironments] = useState<unknown[]>([]);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const [s, p, e] = await Promise.all([
        secureGet(`${BASE}/status`),
        secureGet(`${BASE}/providers`),
        secureGet(`${BASE}/environments`),
      ]);
      setStatus(s.data);
      setProviders(Array.isArray(p.data) ? p.data : []);
      setEnvironments(Array.isArray(e.data) ? e.data : []);
      setMessage("");
    } catch (error) {
      setMessage("Unable to load free sandbox state (admin credential required).");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function post(path: string) {
    try {
      const response = await api.post(`${BASE}${path}`);
      setMessage(JSON.stringify(response.data, null, 2));
      await load();
    } catch (error) {
      setMessage("Action rejected. Check the activation flag and credentials.");
    }
  }

  const policy = (status?.policy ?? {}) as Record<string, unknown>;

  return (
    <main style={{ padding: 24, color: "var(--foreground, #eee)" }}>
      <h1>Free Infrastructure (OEDIE)</h1>
      <p>
        IAM&apos;s free sandbox capability. External platforms are candidate capacity only —
        IAM remains operational when all of them are unavailable.
      </p>

      <section style={{ marginTop: 20 }}>
        <h2>Policy</h2>
        <pre>{JSON.stringify(policy, null, 2)}</pre>
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Providers</h2>
        <button onClick={() => void post("/discover")}>Discover</button>
        <ul>
          {providers.map((provider, index) => (
            <li key={index}>{JSON.stringify(provider)}</li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Environments</h2>
        <button onClick={() => void post("/monitor")}>Poll quotas</button>
        <ul>
          {environments.map((environment, index) => (
            <li key={index}>{JSON.stringify(environment)}</li>
          ))}
        </ul>
      </section>

      {message && (
        <pre style={{ marginTop: 20, whiteSpace: "pre-wrap" }}>{message}</pre>
      )}
    </main>
  );
}
