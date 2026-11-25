"use client";

import React from "react";
import {
  Globe,
  Mail,
  Link,
  ShieldCheck,
  Clock,
  Plus,
  Edit2,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Wifi,
} from "lucide-react";
import { api } from "@/lib/api";

interface Integration {
  id: string;
  name: string;
  provider: string;
  integration_type: string;
  is_active: boolean;
  created_at?: string;
}

interface ApprovalRequest {
  id: string;
  action_type: string;
  description: string;
  status: string;
  requested_at?: string;
}

interface WebsiteIdentity {
  id?: string;
  domain: string;
  site_title: string;
  site_description?: string;
  is_published: boolean;
}

interface EmailIdentity {
  id?: string;
  email_address: string;
  provider: string;
  is_verified: boolean;
}

export default function ExternalPresencePage() {
  const [website, setWebsite] = React.useState<WebsiteIdentity | null>(null);
  const [email, setEmail] = React.useState<EmailIdentity | null>(null);
  const [integrations, setIntegrations] = React.useState<Integration[]>([]);
  const [approvals, setApprovals] = React.useState<ApprovalRequest[]>([]);
  const [activeTab, setActiveTab] = React.useState("website");
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [newIntegrationName, setNewIntegrationName] = React.useState("");
  const [newIntegrationProvider, setNewIntegrationProvider] = React.useState("");
  const [newIntegrationType, setNewIntegrationType] = React.useState("social");

  React.useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setIsLoading(true);
    try {
      const [wResp, eResp, iResp, aResp] = await Promise.all([
        api.get("/api/v1/external-presence/website").catch(() => null),
        api.get("/api/v1/external-presence/email").catch(() => null),
        api.get("/api/v1/external-presence/integrations").catch(() => null),
        api.get("/api/v1/external-presence/approvals").catch(() => null),
      ]);
      setWebsite(wResp?.data || null);
      setEmail(eResp?.data || null);
      setIntegrations(iResp?.data || []);
      setApprovals(aResp?.data || []);
    } catch (err) {
      setError("Failed to load external presence data");
    } finally {
      setIsLoading(false);
    }
  }

  async function createWebsite() {
    setIsLoading(true);
    try {
      const domain = window.prompt("Enter domain (e.g. aura.example.com):");
      if (!domain) return;
      const title = window.prompt("Enter site title:");
      if (!title) return;
      const desc = window.prompt("Enter site description (optional):");
      const response = await api.post("/api/v1/external-presence/website", {
        domain,
        site_title: title,
        site_description: desc || undefined,
        is_published: false,
      });
      setWebsite(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function createEmail() {
    setIsLoading(true);
    try {
      const emailAddr = window.prompt("Enter email address:");
      if (!emailAddr) return;
      const provider = window.prompt("Enter provider (e.g. custom-domain, gmail):", "custom-domain");
      if (!provider) return;
      const response = await api.post("/api/v1/external-presence/email", {
        email_address: emailAddr,
        provider,
        is_verified: false,
      });
      setEmail(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function connectIntegration() {
    if (!newIntegrationName || !newIntegrationProvider) return;
    setIsLoading(true);
    try {
      const response = await api.post("/api/v1/external-presence/integrations", {
        name: newIntegrationName,
        provider: newIntegrationProvider,
        integration_type: newIntegrationType,
        config: {},
        requires_human_approval: true,
      });
      setIntegrations([...integrations, response.data]);
      setNewIntegrationName("");
      setNewIntegrationProvider("");
      setNewIntegrationType("social");
      loadAll(); // refresh to get approval status
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function activateIntegration(id: string) {
    try {
      await api.patch(`/api/v1/external-presence/integrations/${id}/activate`);
      loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    }
  }

  async function disconnectIntegration(id: string) {
    if (!window.confirm("Disconnect this integration?")) return;
    try {
      await api.delete(`/api/v1/external-presence/integrations/${id}`);
      loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    }
  }

  async function createApproval() {
    const actionType = window.prompt("Enter action type (e.g. create_external_account, spend_funds):");
    if (!actionType) return;
    const description = window.prompt("Enter description:");
    if (!description) return;
    try {
      const response = await api.post("/api/v1/external-presence/approvals", {
        action_type: actionType,
        description,
        requested_by: "autonomy-service",
      });
      setApprovals([...approvals, response.data]);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    }
  }

  async function decideApproval(id: string, decision: "approved" | "rejected") {
    const decidedBy = window.prompt("Decided by (your name):", "human");
    if (!decidedBy) return;
    const reason = window.prompt("Reason (optional):");
    try {
      await api.patch(`/api/v1/external-presence/approvals/${id}/decide`, null, {
        params: { decision, decided_by: decidedBy, reason: reason || undefined },
      });
      loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    }
  }

  const tabProps = {
    website: { label: "Website", icon: <Globe className="w-4 h-4" /> },
    email: { label: "Email", icon: <Mail className="w-4 h-4" /> },
    integrations: { label: "Integrations", icon: <Link className="w-4 h-4" /> },
    approvals: { label: "Approvals", icon: <ShieldCheck className="w-4 h-4" /> },
  } as const;

  return (
    <main className="p-4 lg:p-8 space-y-6">
      <header className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Link className="w-6 h-6" />
            External Digital Presence
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Website, email, and authorized platform integrations. VibeCircle is
            an optional connector — not a dependency of AURA.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={createWebsite}
            disabled={isLoading || !!website}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Set Up Website
          </button>
          <button
            onClick={createEmail}
            disabled={isLoading || !!email}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition flex items-center gap-2"
          >
            <Mail className="w-4 h-4" /> Set Up Email
          </button>
        </div>
      </header>

      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm border border-destructive/20">
          {error}
        </div>
      )}

      <div className="flex gap-2 border-b border-input pb-2">
        {Object.entries(tabProps).map(([key, { label, icon }]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === key
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {icon} {label}
          </button>
        ))}
      </div>

      {/* Website Tab */}
      {activeTab === "website" && (
        <section className="space-y-4">
          {website ? (
            <div className="bg-card border rounded-lg p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold">{website.site_title}</h3>
                  <p className="text-sm text-muted-foreground">{website.domain}</p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  website.is_published ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                }`}>
                  {website.is_published ? "Published" : "Draft"}
                </span>
              </div>
              {website.site_description && (
                <p className="text-sm text-muted-foreground mb-4">{website.site_description}</p>
              )}
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    const newDomain = window.prompt("New domain:", website.domain);
                    if (!newDomain) return;
                    const newTitle = window.prompt("New title:", website.site_title);
                    if (!newTitle) return;
                    api
                      .patch("/api/v1/external-presence/website", {
                        domain: newDomain,
                        site_title: newTitle,
                        site_description: website.site_description,
                        is_published: website.is_published,
                      })
                      .then(() => loadAll())
                      .catch((err: any) => setError(err.response?.data?.detail || err.message));
                  }}
                  className="px-4 py-2 border border-input rounded-lg hover:bg-muted transition"
                >
                  <Edit2 className="w-4 h-4 mr-2" /> Edit
                </button>
                <button
                  onClick={() => {
                    api
                      .patch("/api/v1/external-presence/website", {
                        domain: website.domain,
                        site_title: website.site_title,
                        site_description: website.site_description,
                        is_published: !website.is_published,
                      })
                      .then(() => loadAll())
                      .catch((err: any) => setError(err.response?.data?.detail || err.message));
                  }}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition"
                >
                  {website.is_published ? "Unpublish" : "Publish"}
                </button>
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Your website gives AURA an independent web presence separate from
                any third-party platform.
              </p>
            </div>
          ) : (
            <div className="bg-muted rounded-lg p-6 text-center">
              <Globe className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <h3 className="font-semibold mb-2">No website configured</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Set up an independent website for AURA's external digital presence.
              </p>
              <button
                onClick={createWebsite}
                className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition"
              >
                <Plus className="w-4 h-4 mr-2" /> Create Website Identity
              </button>
            </div>
          )}
        </section>
      )}

      {/* Email Tab */}
      {activeTab === "email" && (
        <section className="space-y-4">
          {email ? (
            <div className="bg-card border rounded-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h3 className="font-semibold">{email.email_address}</h3>
                  <p className="text-sm text-muted-foreground">{email.provider}</p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  email.is_verified ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                }`}>
                  {email.is_verified ? "Verified" : "Unverified"}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Email identity for AURA's external communications. This is
                separate from any personal email accounts.
              </p>
            </div>
          ) : (
            <div className="bg-muted rounded-lg p-6 text-center">
              <Mail className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <h3 className="font-semibold mb-2">No email configured</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Set up an email identity for AURA's external communications.
              </p>
              <button
                onClick={createEmail}
                className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition"
              >
                <Plus className="w-4 h-4 mr-2" /> Create Email Identity
              </button>
            </div>
          )}
        </section>
      )}

      {/* Integrations Tab */}
      {activeTab === "integrations" && (
        <section className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Connected Integrations</h3>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newIntegrationName}
                onChange={(e) => setNewIntegrationName(e.target.value)}
                placeholder="Integration name"
                className="px-3 py-2 rounded-lg border border-input bg-background text-foreground text-sm"
              />
              <input
                type="text"
                value={newIntegrationProvider}
                onChange={(e) => setNewIntegrationProvider(e.target.value)}
                placeholder="Provider (e.g. vibecircle)"
                className="px-3 py-2 rounded-lg border border-input bg-background text-foreground text-sm"
              />
              <select
                value={newIntegrationType}
                onChange={(e) => setNewIntegrationType(e.target.value)}
                className="px-3 py-2 rounded-lg border border-input bg-background text-foreground text-sm"
              >
                <option value="social">Social</option>
                <option value="business">Business</option>
                <option value="communication">Communication</option>
              </select>
              <button
                onClick={connectIntegration}
                disabled={isLoading || !newIntegrationName || !newIntegrationProvider}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition"
              >
                <Plus className="w-4 h-4" /> Connect
              </button>
            </div>
          </div>

          {integrations.length === 0 ? (
            <div className="bg-muted rounded-lg p-6 text-center">
              <Wifi className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p className="text-sm text-muted-foreground">
                No external integrations connected. Add one to let AURA interact
                with external platforms.
              </p>
            </div>
          ) : (
            <div className="grid gap-3">
              {integrations.map((integ) => (
                <div
                  key={integ.id}
                  className="bg-card border rounded-lg p-4 flex justify-between items-start"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold">{integ.name}</span>
                      <span className="text-xs bg-muted text-muted-foreground rounded px-2 py-0.5">
                        {integ.provider}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {integ.integration_type} • {integ.is_active ? "Active" : "Pending approval"}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {!integ.is_active && (
                      <button
                        onClick={() => activateIntegration(integ.id)}
                        className="px-3 py-1.5 bg-green-100 text-green-800 text-xs rounded hover:bg-green-200 transition"
                      >
                        <CheckCircle2 className="w-3 h-3 mr-1" /> Approve
                      </button>
                    )}
                    <button
                      onClick={() => disconnectIntegration(integ.id)}
                      className="px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 rounded transition"
                    >
                      <Trash2 className="w-3 h-3 mr-1" /> Disconnect
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <p className="text-xs text-muted-foreground mt-2">
            Note: Integrations requiring external account creation need human
            approval before activation. VibeCircle is an optional connector —
            not a dependency of AURA's core services.
          </p>
        </section>
      )}

      {/* Approvals Tab */}
      {activeTab === "approvals" && (
        <section className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Pending Approvals</h3>
            <button
              onClick={createApproval}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Request Approval
            </button>
          </div>

          {approvals.length === 0 ? (
            <div className="bg-muted rounded-lg p-6 text-center">
              <Clock className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p className="text-sm text-muted-foreground">
                No pending approval requests.
              </p>
            </div>
          ) : (
            <div className="grid gap-3">
              {approvals.map((approval) => (
                <div
                  key={approval.id}
                  className="bg-card border rounded-lg p-4 flex justify-between items-start"
                >
                  <div>
                    <h4 className="font-semibold">{approval.action_type}</h4>
                    <p className="text-sm text-muted-foreground">{approval.description}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Requested: {approval.requested_at}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {approval.status === "pending" ? (
                      <>
                        <button
                          onClick={() => decideApproval(approval.id, "approved")}
                          className="px-3 py-1.5 bg-green-100 text-green-800 text-xs rounded hover:bg-green-200 transition"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => decideApproval(approval.id, "rejected")}
                          className="px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 rounded transition"
                        >
                          Reject
                        </button>
                      </>
                    ) : (
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        approval.status === "approved"
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}>
                        {approval.status}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
