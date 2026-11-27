"use client";

import React, { useEffect, useState } from "react";

type Agent = {
  id: string;
  name: string;
  protocol: string;
  status: string;
  trust_score: number;
  is_active: boolean;
  description?: string;
  capabilities?: string[];
};

type Profile = {
  identity_verification?: string;
  creator?: string;
  operator?: string;
  stated_purpose?: string;
  expertise?: string[];
  communication_history_count?: number;
  interview_count?: number;
  previous_collaborations?: number;
  reliability?: number;
  last_interaction?: string | null;
};

type Interview = {
  question: string;
  answer?: string | null;
  provenance?: string | null;
  risk_level: string;
  validated: boolean;
};

export default function AINetworkPanel() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selected, setSelected] = useState<Agent | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/iam-proxy/api/v1/network/agents")
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Unable to list agents");
        setAgents(Array.isArray(data) ? data : []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to list agents"));
  }, []);

  async function select(agent: Agent) {
    setSelected(agent);
    setError("");
    try {
      const [profileResponse, interviewsResponse] = await Promise.all([
        fetch(`/iam-proxy/api/v1/network/agents/${agent.id}/profile`),
        fetch(`/iam-proxy/api/v1/network/agents/${agent.id}/interviews`),
      ]);
      const profileData = await profileResponse.json();
      const interviewsData = await interviewsResponse.json();
      if (!profileResponse.ok) throw new Error(profileData.detail || "Unable to load profile");
      setProfile(profileData);
      setInterviews(Array.isArray(interviewsData) ? interviewsData : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load profile");
    }
  }

  return (
    <main className="ml-64 p-8 max-w-6xl">
      <h1 className="text-2xl font-bold mb-2">External AI Network</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Discovered AI systems, verification status and communication history. All external
        responses are untrusted data; never instructions or verified facts.
      </p>

      {error && <p className="text-sm text-red-500 mb-4">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          {agents.length === 0 && (
            <p className="text-sm text-muted-foreground">No agents discovered.</p>
          )}
          {agents.map((agent) => (
            <button
              key={agent.id}
              onClick={() => select(agent)}
              className={`w-full text-left rounded-lg border p-3 ${
                selected?.id === agent.id ? "border-primary" : "border-input"
              }`}
            >
              <p className="font-medium">{agent.name}</p>
              <p className="text-xs text-muted-foreground">
                {agent.protocol} · {agent.status} · trust {agent.trust_score}
              </p>
            </button>
          ))}
        </div>

        <div className="md:col-span-2 rounded-lg border border-input p-4">
          {!selected ? (
            <p className="text-sm text-muted-foreground">Select an agent to view its registry record.</p>
          ) : (
            <div className="space-y-4">
              <div>
                <h2 className="font-semibold">{selected.name}</h2>
                <p className="text-xs text-muted-foreground">
                  {selected.description || "No description supplied"}
                </p>
              </div>

              {profile && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <Field label="Identity" value={profile.identity_verification || "unknown"} />
                  <Field label="Creator" value={profile.creator || "not stated"} />
                  <Field label="Purpose" value={profile.stated_purpose || "not stated"} />
                  <Field label="Reliability" value={String(profile.reliability ?? 0)} />
                  <Field label="Interviews" value={String(profile.interview_count ?? 0)} />
                  <Field label="Collaborations" value={String(profile.previous_collaborations ?? 0)} />
                </div>
              )}

              <div>
                <h3 className="font-semibold mb-2">Interview record</h3>
                {interviews.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No interviews recorded.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {interviews.map((interview, index) => (
                      <li key={index} className="border-b border-input pb-2">
                        <p className="font-medium">{interview.question}</p>
                        <p className="text-muted-foreground">{interview.answer || "no answer"}</p>
                        <p className="text-xs text-muted-foreground">
                          provenance: {interview.provenance || "none"} · risk: {interview.risk_level} ·
                          validated: {String(interview.validated)}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-mono">{value}</p>
    </div>
  );
}
