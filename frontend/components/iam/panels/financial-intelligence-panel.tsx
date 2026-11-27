"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { secureGet } from "@/lib/secure-api";

const PM = "/api/v1/prediction-markets";
const GI = "/api/v1/gaming-intelligence";
const II = "/api/v1/investment-intelligence";
const PR = "/api/v1/provider-registry";

type Tab = "prediction" | "gaming" | "investment" | "providers";

type Market = {
  id: string;
  platform: string;
  market_ref: string;
  event_name: string;
  outcomes: string[];
  implied_probabilities: Record<string, number>;
  legal_status: string;
  real_money_enabled: boolean;
};

type Comparison = {
  outcome: string;
  market_probability: number;
  iam_probability: number;
  difference_percentage_points: number;
  evidence: string[];
};

type ForecastResult = {
  method: string;
  formula: string;
  confidence: number;
  independent: boolean;
  market_implied_probabilities_used: boolean;
  comparison: { comparisons: Comparison[] };
  estimates: Array<{ outcome: string; iam_probability: number }>;
};

type GamingRecord = {
  id: string;
  game: string;
  rtp: number;
  house_edge: number;
  sample_size: number;
  methodology: string;
};

type InvestmentRecord = {
  id: string;
  asset_class: string;
  symbol: string;
  thesis: string;
  risk_notes: string | null;
  execution_enabled: boolean;
};

type ProviderEntry = {
  id: string;
  name: string;
  category: string;
  access_model: string;
  adapter_enabled: boolean;
  gates_reviewed: boolean;
  south_africa_supported: boolean;
  adapter_eligible: boolean;
  missing: string[];
  notes: string | null;
};

type EvidenceRow = {
  outcome: string;
  strength: number;
  source: string;
  description: string;
};

function errorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (
      error as { response?: { data?: { detail?: string } } }
    ).response;
    if (response?.data?.detail) return response.data.detail;
  }
  return "Action rejected. Check activation flags and credentials.";
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-input p-4 mt-4">
      <h2 className="text-lg font-semibold mb-2">{title}</h2>
      {children}
    </section>
  );
}

export default function FinancialIntelligencePanel() {
  const [tab, setTab] = useState<Tab>("prediction");
  const [message, setMessage] = useState("");
  const [predictionPolicy, setPredictionPolicy] = useState<Record<string, unknown>>({});
  const [adapterStatus, setAdapterStatus] = useState<Record<string, unknown>>({});
  const [forecastPolicy, setForecastPolicy] = useState<Record<string, unknown>>({});
  const [markets, setMarkets] = useState<Market[]>([]);
  const [selectedMarketId, setSelectedMarketId] = useState("");
  const [evidence, setEvidence] = useState<EvidenceRow[]>([
    { outcome: "", strength: 0.5, source: "", description: "" },
  ]);
  const [method, setMethod] = useState("evidence_weighted");
  const [rationale, setRationale] = useState("");
  const [forecastResult, setForecastResult] = useState<ForecastResult | null>(null);
  const [manualOutcome, setManualOutcome] = useState("");
  const [manualProbability, setManualProbability] = useState(0.5);
  const [manualEvidence, setManualEvidence] = useState("");
  const [gamingPolicy, setGamingPolicy] = useState<Record<string, unknown>>({});
  const [gamingRecords, setGamingRecords] = useState<GamingRecord[]>([]);
  const [rtp, setRtp] = useState(0.96);
  const [wager, setWager] = useState(100);
  const [plays, setPlays] = useState(1);
  const [rtpResult, setRtpResult] = useState<Record<string, unknown> | null>(null);
  const [investmentPolicy, setInvestmentPolicy] = useState<Record<string, unknown>>({});
  const [investmentRecords, setInvestmentRecords] = useState<InvestmentRecord[]>([]);
  const [assetClass, setAssetClass] = useState("etfs");
  const [symbol, setSymbol] = useState("");
  const [thesis, setThesis] = useState("");
  const [riskNotes, setRiskNotes] = useState("");
  const [providers, setProviders] = useState<ProviderEntry[]>([]);
  const [providerPolicy, setProviderPolicy] = useState<Record<string, unknown>>({});

  const load = useCallback(async () => {
    try {
      const [pp, pa, fp, mk, gp, gr, ip, ir, pr, prp] = await Promise.all([
        secureGet(`${PM}/policy`),
        secureGet(`${PM}/adapter/status`),
        secureGet(`${PM}/forecast/policy`),
        secureGet(`${PM}/markets`),
        secureGet(`${GI}/policy`),
        secureGet(`${GI}/records`),
        secureGet(`${II}/policy`),
        secureGet(`${II}/records`),
        secureGet(`${PR}/entries`),
        secureGet(`${PR}/policy`),
      ]);
      setPredictionPolicy(pp.data as Record<string, unknown>);
      setAdapterStatus(pa.data as Record<string, unknown>);
      setForecastPolicy(fp.data as Record<string, unknown>);
      setMarkets(Array.isArray(mk.data) ? (mk.data as Market[]) : []);
      setGamingPolicy(gp.data as Record<string, unknown>);
      setGamingRecords(Array.isArray(gr.data) ? (gr.data as GamingRecord[]) : []);
      setInvestmentPolicy(ip.data as Record<string, unknown>);
      setInvestmentRecords(Array.isArray(ir.data) ? (ir.data as InvestmentRecord[]) : []);
      setProviders(Array.isArray(pr.data) ? (pr.data as ProviderEntry[]) : []);
      setProviderPolicy(prp.data as Record<string, unknown>);
      setMessage("");
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedMarketId && markets.length > 0) {
      const first = markets[0];
      setSelectedMarketId(first.id);
      setManualOutcome(first.outcomes[0] ?? "");
      setEvidence((rows) =>
        rows.map((row) => ({ ...row, outcome: row.outcome || (first.outcomes[0] ?? "") }))
      );
    }
  }, [markets, selectedMarketId]);

  const selectedMarket = markets.find((market) => market.id === selectedMarketId) ?? null;

  async function runAction(action: () => Promise<unknown>, success: string) {
    try {
      const result = await action();
      setMessage(success);
      await load();
      return result;
    } catch (error) {
      setMessage(errorMessage(error));
      return null;
    }
  }

  async function syncMarkets() {
    await runAction(
      () => api.post(`${PM}/adapter/sync`, { limit: 20 }),
      "Public market data synced. Implied probabilities are not IAM estimates."
    );
  }

  async function submitForecast() {
    if (!selectedMarket) {
      setMessage("Select a market first.");
      return;
    }
    const rows = evidence.map((row) => ({
      outcome: row.outcome || (selectedMarket.outcomes[0] ?? ""),
      strength: Number(row.strength),
      source: row.source,
      description: row.description,
    }));
    const result = await runAction(
      () =>
        api.post(`${PM}/forecast/run`, {
          market_id: selectedMarket.id,
          method,
          evidence: rows,
          rationale,
        }),
      "Independent forecast recorded."
    );
    if (result) setForecastResult(result as ForecastResult);
  }

  async function submitManualEstimate() {
    if (!selectedMarket) {
      setMessage("Select a market first.");
      return;
    }
    await runAction(
      () =>
        api.post(`${PM}/markets/${selectedMarket.id}/estimates`, {
          outcome: manualOutcome,
          iam_probability: Number(manualProbability),
          evidence: manualEvidence
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      "Manual probability estimate recorded."
    );
  }

  async function submitRtpScenario() {
    const result = await runAction(
      () => api.post(`${GI}/rtp-scenario`, { rtp: Number(rtp), wager: Number(wager), plays: Number(plays) }),
      "Long-run illustration calculated."
    );
    if (result) setRtpResult(result as Record<string, unknown>);
  }

  async function submitThesis() {
    await runAction(
      () => api.post(`${II}/records`, { asset_class: assetClass, symbol, thesis, risk_notes: riskNotes }),
      "Investment research note recorded. No order was placed."
    );
    setSymbol("");
    setThesis("");
  }

  async function seedProviders() {
    await runAction(() => api.post(`${PR}/seed`), "Provider catalogue seed attempted (idempotent).");
  }

  const tabs: Array<{ key: Tab; label: string }> = [
    { key: "prediction", label: "Prediction markets" },
    { key: "gaming", label: "Gaming intelligence" },
    { key: "investment", label: "Investment intelligence" },
    { key: "providers", label: "Provider gates" },
  ];

  return (
    <main className="p-6">
      <h1 className="text-2xl font-bold">Financial Intelligence (Doc 25 Amendment A)</h1>
      <p className="text-sm text-muted-foreground mt-1">
        Research-only modules. No wagering, wallet funding or real order execution is exposed.
      </p>

      <nav className="flex flex-wrap gap-2 mt-4">
        {tabs.map((item) => (
          <button
            key={item.key}
            onClick={() => setTab(item.key)}
            className={`rounded px-3 py-1 text-sm border ${
              tab === item.key ? "bg-primary text-primary-foreground" : "border-input"
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {message && <pre className="mt-4 whitespace-pre-wrap text-sm">{message}</pre>}

      {tab === "prediction" && (
        <>
          <Panel title="Policy and public-data adapter">
            <pre className="text-xs whitespace-pre-wrap">
              {JSON.stringify({ policy: predictionPolicy, adapter: adapterStatus }, null, 2)}
            </pre>
            <button onClick={() => void syncMarkets()} className="mt-2 rounded border border-input px-3 py-1 text-sm">
              Sync public markets
            </button>
            <p className="text-xs text-muted-foreground mt-2">
              South African participation requires separate legal review. Legal clearance does not
              enable execution.
            </p>
          </Panel>

          <Panel title="Markets and independent forecasts">
            {markets.length === 0 ? (
              <p className="text-sm">No markets recorded yet. Sync public data or register one manually.</p>
            ) : (
              <>
                <label className="block text-sm mb-2">
                  Market
                  <select
                    value={selectedMarketId}
                    onChange={(event) => setSelectedMarketId(event.target.value)}
                    className="block w-full mt-1 bg-background border border-input rounded p-2"
                  >
                    {markets.map((market) => (
                      <option key={market.id} value={market.id}>
                        {market.platform}: {market.event_name}
                      </option>
                    ))}
                  </select>
                </label>
                {selectedMarket && (
                  <pre className="text-xs whitespace-pre-wrap mb-3">
                    {JSON.stringify(selectedMarket, null, 2)}
                  </pre>
                )}
                <pre className="text-xs whitespace-pre-wrap mb-3">
                  {JSON.stringify(forecastPolicy, null, 2)}
                </pre>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="border border-input rounded p-3">
                    <h3 className="font-semibold mb-2">Evidence-weighted forecast</h3>
                    <label className="block text-sm mb-2">
                      Method
                      <select
                        value={method}
                        onChange={(event) => setMethod(event.target.value)}
                        className="block w-full mt-1 bg-background border border-input rounded p-2"
                      >
                        <option value="evidence_weighted">evidence_weighted</option>
                        <option value="base_rate">base_rate</option>
                      </select>
                    </label>
                    {evidence.map((row, index) => (
                      <div key={index} className="grid gap-2 mb-2 md:grid-cols-4">
                        <input
                          aria-label="Outcome"
                          placeholder={selectedMarket?.outcomes[0] ?? "outcome"}
                          value={row.outcome}
                          onChange={(event) =>
                            setEvidence((rows) =>
                              rows.map((item, i) =>
                                i === index ? { ...item, outcome: event.target.value } : item
                              )
                            )
                          }
                          className="bg-background border border-input rounded p-1 text-sm"
                        />
                        <input
                          aria-label="Strength"
                          type="number"
                          min={0}
                          max={1}
                          step={0.05}
                          value={row.strength}
                          onChange={(event) =>
                            setEvidence((rows) =>
                              rows.map((item, i) =>
                                i === index ? { ...item, strength: Number(event.target.value) } : item
                              )
                            )
                          }
                          className="bg-background border border-input rounded p-1 text-sm"
                        />
                        <input
                          aria-label="Source"
                          placeholder="source"
                          value={row.source}
                          onChange={(event) =>
                            setEvidence((rows) =>
                              rows.map((item, i) =>
                                i === index ? { ...item, source: event.target.value } : item
                              )
                            )
                          }
                          className="bg-background border border-input rounded p-1 text-sm"
                        />
                        <input
                          aria-label="Description"
                          placeholder="description"
                          value={row.description}
                          onChange={(event) =>
                            setEvidence((rows) =>
                              rows.map((item, i) =>
                                i === index ? { ...item, description: event.target.value } : item
                              )
                            )
                          }
                          className="bg-background border border-input rounded p-1 text-sm"
                        />
                      </div>
                    ))}
                    <button
                      onClick={() =>
                        setEvidence((rows) => [
                          ...rows,
                          {
                            outcome: selectedMarket?.outcomes[0] ?? "",
                            strength: 0.5,
                            source: "",
                            description: "",
                          },
                        ])
                      }
                      className="text-sm border border-input rounded px-2 py-1"
                    >
                      Add evidence
                    </button>
                    <label className="block text-sm mt-3">
                      Rationale
                      <textarea
                        value={rationale}
                        onChange={(event) => setRationale(event.target.value)}
                        className="block w-full mt-1 bg-background border border-input rounded p-2"
                        rows={3}
                      />
                    </label>
                    <button
                      onClick={() => void submitForecast()}
                      className="mt-2 rounded border border-input px-3 py-1 text-sm"
                    >
                      Record independent forecast
                    </button>
                  </div>

                  <div className="border border-input rounded p-3">
                    <h3 className="font-semibold mb-2">Manual probability estimate</h3>
                    <label className="block text-sm mb-2">
                      Outcome
                      <select
                        value={manualOutcome}
                        onChange={(event) => setManualOutcome(event.target.value)}
                        className="block w-full mt-1 bg-background border border-input rounded p-2"
                      >
                        {(selectedMarket?.outcomes ?? []).map((outcome) => (
                          <option key={outcome} value={outcome}>
                            {outcome}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="block text-sm mb-2">
                      IAM probability (0–1)
                      <input
                        type="number"
                        min={0}
                        max={1}
                        step={0.01}
                        value={manualProbability}
                        onChange={(event) => setManualProbability(Number(event.target.value))}
                        className="block w-full mt-1 bg-background border border-input rounded p-2"
                      />
                    </label>
                    <label className="block text-sm mb-2">
                      Evidence (comma separated)
                      <input
                        value={manualEvidence}
                        onChange={(event) => setManualEvidence(event.target.value)}
                        className="block w-full mt-1 bg-background border border-input rounded p-2"
                      />
                    </label>
                    <button
                      onClick={() => void submitManualEstimate()}
                      className="rounded border border-input px-3 py-1 text-sm"
                    >
                      Record estimate
                    </button>
                    <p className="text-xs text-muted-foreground mt-2">
                      A probability gap is not automatically profitable: fees, liquidity, spreads,
                      settlement and estimate uncertainty still apply.
                    </p>
                  </div>
                </div>

                {forecastResult && (
                  <div className="mt-4">
                    <h3 className="font-semibold">Latest forecast result</h3>
                    <pre className="text-xs whitespace-pre-wrap">
                      {JSON.stringify(forecastResult, null, 2)}
                    </pre>
                  </div>
                )}
              </>
            )}
          </Panel>
        </>
      )}

      {tab === "gaming" && (
        <>
          <Panel title="Gaming research policy">
            <pre className="text-xs whitespace-pre-wrap">
              {JSON.stringify(gamingPolicy, null, 2)}
            </pre>
            <p className="text-sm mt-2">
              Casino mathematics and RNG research only. Wagering and overseas account funding are
              disabled in every build.
            </p>
          </Panel>
          <Panel title="RTP scenario (long-run illustration)">
            <div className="grid gap-2 md:grid-cols-3">
              <label className="text-sm">
                RTP
                <input
                  type="number"
                  step={0.0001}
                  min={0}
                  max={1}
                  value={rtp}
                  onChange={(event) => setRtp(Number(event.target.value))}
                  className="block w-full mt-1 bg-background border border-input rounded p-2"
                />
              </label>
              <label className="text-sm">
                Wager
                <input
                  type="number"
                  min={0}
                  value={wager}
                  onChange={(event) => setWager(Number(event.target.value))}
                  className="block w-full mt-1 bg-background border border-input rounded p-2"
                />
              </label>
              <label className="text-sm">
                Plays
                <input
                  type="number"
                  min={0}
                  value={plays}
                  onChange={(event) => setPlays(Number(event.target.value))}
                  className="block w-full mt-1 bg-background border border-input rounded p-2"
                />
              </label>
            </div>
            <button onClick={() => void submitRtpScenario()} className="mt-2 rounded border border-input px-3 py-1 text-sm">
              Calculate illustration
            </button>
            {rtpResult && (
              <pre className="text-xs whitespace-pre-wrap mt-3">
                {JSON.stringify(rtpResult, null, 2)}
              </pre>
            )}
          </Panel>
          <Panel title="Recorded game analyses">
            <ul className="text-sm space-y-1">
              {gamingRecords.map((record) => (
                <li key={record.id}>
                  {record.game} — RTP {record.rtp}, house edge {record.house_edge}, samples{" "}
                  {record.sample_size}
                </li>
              ))}
            </ul>
          </Panel>
        </>
      )}

      {tab === "investment" && (
        <>
          <Panel title="Investment research policy">
            <pre className="text-xs whitespace-pre-wrap">
              {JSON.stringify(investmentPolicy, null, 2)}
            </pre>
            <p className="text-sm mt-2">Research notes and proposals only. No broker orders are placed.</p>
          </Panel>
          <Panel title="Record a research note">
            <div className="grid gap-2 md:grid-cols-2">
              <label className="text-sm">
                Asset class
                <select
                  value={assetClass}
                  onChange={(event) => setAssetClass(event.target.value)}
                  className="block w-full mt-1 bg-background border border-input rounded p-2"
                >
                  {["stocks", "etfs", "commodities", "futures", "bonds", "precious_metals", "indices"].map(
                    (name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    )
                  )}
                </select>
              </label>
              <label className="text-sm">
                Symbol
                <input
                  value={symbol}
                  onChange={(event) => setSymbol(event.target.value)}
                  className="block w-full mt-1 bg-background border border-input rounded p-2"
                />
              </label>
            </div>
            <label className="block text-sm mt-2">
              Thesis
              <textarea
                value={thesis}
                onChange={(event) => setThesis(event.target.value)}
                rows={3}
                className="block w-full mt-1 bg-background border border-input rounded p-2"
              />
            </label>
            <label className="block text-sm mt-2">
              Risk notes
              <input
                value={riskNotes}
                onChange={(event) => setRiskNotes(event.target.value)}
                className="block w-full mt-1 bg-background border border-input rounded p-2"
              />
            </label>
            <button onClick={() => void submitThesis()} className="mt-2 rounded border border-input px-3 py-1 text-sm">
              Record research note
            </button>
          </Panel>
          <Panel title="Recorded research">
            <ul className="text-sm space-y-1">
              {investmentRecords.map((record) => (
                <li key={record.id}>
                  {record.asset_class}: {record.symbol} — {record.thesis}
                </li>
              ))}
            </ul>
          </Panel>
        </>
      )}

      {tab === "providers" && (
        <>
          <Panel title="Provider registry policy">
            <pre className="text-xs whitespace-pre-wrap">
              {JSON.stringify(providerPolicy, null, 2)}
            </pre>
            <button onClick={() => void seedProviders()} className="mt-2 rounded border border-input px-3 py-1 text-sm">
              Seed §18 candidate catalogue
            </button>
            <p className="text-xs text-muted-foreground mt-2">
              Seeding records candidate names only. Adapters remain disabled until every gate is
              reviewed. South African availability is unverified for seeded candidates.
            </p>
          </Panel>
          <Panel title="Provider gates">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left">
                  <th className="p-1">Provider</th>
                  <th className="p-1">Category</th>
                  <th className="p-1">Reviewed</th>
                  <th className="p-1">ZA</th>
                  <th className="p-1">Adapter</th>
                  <th className="p-1">Missing gates</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((entry) => (
                  <tr key={entry.id} className="border-t border-input">
                    <td className="p-1">{entry.name}</td>
                    <td className="p-1">{entry.category}</td>
                    <td className="p-1">{entry.gates_reviewed ? "yes" : "no"}</td>
                    <td className="p-1">{entry.south_africa_supported ? "yes" : "no"}</td>
                    <td className="p-1">{entry.adapter_enabled ? "enabled" : "disabled"}</td>
                    <td className="p-1">{entry.missing.join(", ") || "none"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </>
      )}
    </main>
  );
}
