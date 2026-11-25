"use client";

import React from "react";
import { Link as LinkIcon, ShieldCheck, Info, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

export default function VibeCirclePage() {
  const [connected, setConnected] = React.useState(false);
  const [isConnecting, setIsConnecting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api
      .get("/api/v1/external-presence/integrations")
      .then((resp) => {
        const hasVibecircle = (resp.data || []).some(
          (i: any) => i.provider === "vibecircle"
        );
        setConnected(hasVibecircle);
      })
      .catch(() => {
        // Ignore errors on load
      });
  }, []);

  async function connectVibeCircle() {
    setIsConnecting(true);
    setError(null);
    try {
      const response = await api.post("/api/v1/external-presence/integrations", {
        name: "vibecircle",
        provider: "vibecircle",
        integration_type: "social",
        config: {},
        requires_human_approval: true,
      });
      setConnected(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Failed to connect");
    } finally {
      setIsConnecting(false);
    }
  }

  async function disconnectVibeCircle() {
    try {
      const integrationsResp = await api.get("/api/v1/external-presence/integrations");
      const vc = (integrationsResp.data || []).find(
        (i: any) => i.provider === "vibecircle"
      );
      if (vc) {
        await api.delete(`/api/v1/external-presence/integrations/${vc.id}`);
        setConnected(false);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Failed to disconnect");
    }
  }

  return (
    <main className="p-4 lg:p-8 space-y-6">
      <header>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <LinkIcon className="w-6 h-6 text-primary" />
          VibeCircle Connector
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Optional external platform integration. VibeCircle is not a dependency
          of AURA's core architecture.
        </p>
      </header>

      <div className="bg-card border rounded-lg p-6">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="font-semibold">Connection Status</h2>
            <p className="text-sm text-muted-foreground">
              Connect AURA to VibeCircle as an external platform.
            </p>
          </div>
          <div className={`px-3 py-1 rounded-full text-xs font-medium ${
            connected ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
          }`}>
            {connected ? "Connected" : "Not Connected"}
          </div>
        </div>

        <div className="bg-muted/50 rounded-lg p-4 mb-6">
          <h3 className="font-medium mb-2">Important</h3>
          <ul className="space-y-1 text-sm text-muted-foreground list-disc list-inside">
            <li>
              VibeCircle is an <strong>optional external platform</strong>. AURA
              may connect to it in the future with your authorization.
            </li>
            <li>
              VibeCircle is <strong>not part of AURA's architecture</strong> —
              no database, authentication, backend, or deployment dependency.
            </li>
            <li>
              Connecting requires <strong>human approval</strong> before the
              integration becomes active.
            </li>
            <li>
              AURA can function completely independently without VibeCircle.
            </li>
          </ul>
        </div>

        {connected ? (
          <div className="flex gap-3">
            <button
              onClick={disconnectVibeCircle}
              disabled={isConnecting}
              className="px-6 py-3 text-destructive hover:bg-destructive/10 rounded-lg transition"
            >
              <AlertTriangle className="w-4 h-4 mr-2" />
              Disconnect VibeCircle
            </button>
          </div>
        ) : (
          <button
            onClick={connectVibeCircle}
            disabled={isConnecting}
            className="w-full py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition flex items-center justify-center gap-2"
          >
            <LinkIcon className="w-4 h-4" /> Connect to VibeCircle
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm border border-destructive/20">
          {error}
        </div>
      )}

      <div className="bg-muted rounded-lg p-6">
        <h3 className="font-semibold mb-4">About External Integrations</h3>
        <p className="text-sm text-muted-foreground mb-4">
          AURA maintains complete independence. External platforms like VibeCircle
          are optional connectors that require explicit authorization. AURA's
          identity, memory, and core services never depend on any external
          platform.
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ShieldCheck className="w-4 h-4" />
          <span>Independent by design</span>
        </div>
      </div>
    </main>
  );
}
