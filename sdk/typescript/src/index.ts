import { randomUUID } from "node:crypto";
import {
  IAMError,
  PROTOCOL_VERSION,
  type Contribution,
  type IAMOptions,
  type NodeRegistration,
  type ResourceReport,
  type Task,
  type TaskSubmit,
} from "./types.js";

export * from "./types.js";

/** Minimal versioned HTTP transport shared by all IAM service groups. */
class Transport {
  private readonly base: string;
  private readonly version: string;
  private readonly timeoutMs: number;
  private readonly maxRetries: number;

  constructor(private readonly options: IAMOptions) {
    this.base = options.endpoint.replace(/\/$/, "");
    this.version = options.apiVersion ?? PROTOCOL_VERSION;
    this.timeoutMs = options.timeoutMs ?? 30_000;
    this.maxRetries = options.maxRetries ?? 3;
  }

  async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const absolute = path.startsWith("http") ? path : `${this.base}${path}`;
    const headers: Record<string, string> = {
      "X-IAM-Protocol-Version": this.version,
      Accept: "application/json",
    };
    if (this.options.token) headers.Authorization = `Bearer ${this.options.token}`;
    if (this.options.accessClientId && this.options.accessClientSecret) {
      headers["CF-Access-Client-Id"] = this.options.accessClientId;
      headers["CF-Access-Client-Secret"] = this.options.accessClientSecret;
    }
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (method === "POST") headers["Idempotency-Key"] = randomUUID();

    let lastError: unknown;
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const response = await fetch(absolute, {
          method,
          headers,
          body: body === undefined ? undefined : JSON.stringify(body),
          signal: AbortSignal.timeout(this.timeoutMs),
        });
        if (response.status === 204) return undefined as T;
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          const code = String(payload.code ?? "iam_error");
          throw new IAMError(
            String(payload.detail ?? response.statusText),
            response.status,
            code,
            payload.request_id as string | undefined,
          );
        }
        return payload as T;
      } catch (error) {
        lastError = error;
        const retryable =
          error instanceof IAMError &&
          (error.status === 429 || error.status >= 500);
        const networkError = error instanceof TypeError;
        if ((!retryable && !networkError) || attempt === this.maxRetries) break;
        await new Promise((resolve) => setTimeout(resolve, 2 ** attempt * 100));
      }
    }
    throw lastError;
  }
}

/** Official client for the IAM Core. */
export class IAM {
  private readonly transport: Transport;
  private readonly queue: Array<TaskSubmit> = [];
  private connected = false;

  core: { status: () => Promise<Record<string, unknown>> };
  tasks: {
    submit: (task: TaskSubmit) => Promise<Task>;
    get: (id: string) => Promise<Task>;
    flushQueue: () => Promise<number>;
  };
  nodes: {
    register: (node: NodeRegistration) => Promise<Record<string, unknown>>;
    status: (id: string) => Promise<Record<string, unknown>>;
    attest: (
      id: string,
      payload: Record<string, unknown>,
      signature: string,
    ) => Promise<Record<string, unknown>>;
    restrict: (id: string, reason: string) => Promise<Record<string, unknown>>;
    revoke: (id: string) => Promise<Record<string, unknown>>;
  };
  integrity: {
    status: () => Promise<Record<string, unknown>>;
    approve: () => Promise<Record<string, unknown>>;
  };
  resources: { report: (nodeId: string, report: ResourceReport) => Promise<void> };
  files: {
    upload: (name: string, content: string) => Promise<Record<string, unknown>>;
    get: (id: string) => Promise<Record<string, unknown>>;
  };
  knowledge: { submit: (c: Contribution) => Promise<Record<string, unknown>> };
  sync: {
    status: () => Promise<Record<string, unknown>>;
    publish: (object: Record<string, unknown>) => Promise<Record<string, unknown>>;
    list: (since?: string) => Promise<Record<string, unknown>>;
  };
  diagnostics: { status: () => Promise<Record<string, unknown>> };
  uwaie: {
    inspect: (url: string) => Promise<Record<string, unknown>>;
    execute: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    workflows: () => Promise<Record<string, unknown>>;
  };
  assistantLab: {
    boundaries: () => Promise<Record<string, unknown>>;
    registerSystem: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    systems: () => Promise<Record<string, unknown>>;
    addNote: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    notes: (assistantId: string, topic?: string) => Promise<Record<string, unknown>>;
    registerAdapter: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    adapters: (assistantId: string) => Promise<Record<string, unknown>>;
    startExperiment: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    experiments: () => Promise<Record<string, unknown>>;
    recordResult: (id: string, payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    adoptExperiment: (id: string, approvalReference: string) => Promise<Record<string, unknown>>;
    compare: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    comparisons: (capability?: string) => Promise<Record<string, unknown>>;
    status: () => Promise<Record<string, unknown>>;
  };
  freeSandbox: {
    policy: () => Promise<Record<string, unknown>>;
    providers: () => Promise<Record<string, unknown>>;
    discover: () => Promise<Record<string, unknown>>;
    requestRegistration: (name: string) => Promise<Record<string, unknown>>;
    verifyCredentials: (name: string) => Promise<Record<string, unknown>>;
    verifyQuota: (name: string) => Promise<Record<string, unknown>>;
    status: () => Promise<Record<string, unknown>>;
    monitor: () => Promise<Record<string, unknown>>;
    expiryCalendar: () => Promise<Record<string, unknown>>;
    provision: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    recover: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    environments: () => Promise<Record<string, unknown>>;
    environment: (id: string) => Promise<Record<string, unknown>>;
    start: (id: string) => Promise<Record<string, unknown>>;
    stop: (id: string) => Promise<Record<string, unknown>>;
    remove: (id: string) => Promise<Record<string, unknown>>;
    results: (id: string) => Promise<Record<string, unknown>>;
  };
  humanPresence: {
    boundaries: () => Promise<Record<string, unknown>>;
    createPerson: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    people: (name?: string) => Promise<Record<string, unknown>>;
    addProfile: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    verifyProfile: (id: string) => Promise<Record<string, unknown>>;
    addClaim: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    matchPeople: (id: string, payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    addRelationship: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    profiles: (id: string) => Promise<Record<string, unknown>>;
    claims: (id: string) => Promise<Record<string, unknown>>;
    timeline: (id: string) => Promise<Record<string, unknown>>;
  };
  geo: {
    registerProvider: (provider: Record<string, unknown>) => Promise<Record<string, unknown>>;
    providers: (kind?: string) => Promise<Record<string, unknown>>;
    mapConfig: (kind?: string) => Promise<Record<string, unknown>>;
    addPlace: (place: Record<string, unknown>) => Promise<Record<string, unknown>>;
    places: (query: string, countryCode?: string) => Promise<Record<string, unknown>>;
    nearby: (lat: number, lon: number, radiusKm?: number) => Promise<Record<string, unknown>>;
    reverse: (lat: number, lon: number, radiusKm?: number) => Promise<Record<string, unknown>>;
    geocode: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    importGeoJSON: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    exportGeoJSON: (placeIds?: string[]) => Promise<Record<string, unknown>>;
    registerFeed: (feed: Record<string, unknown>) => Promise<Record<string, unknown>>;
    feeds: () => Promise<Record<string, unknown>>;
    snapshotFeed: (id: string, data: unknown) => Promise<Record<string, unknown>>;
    cacheTile: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    tileStatus: () => Promise<Record<string, unknown>>;
    grantPermission: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    resolveLocation: (subject: string, lat?: number, lon?: number) => Promise<Record<string, unknown>>;
    status: () => Promise<Record<string, unknown>>;
  };
  legal: {
    sources: () => Promise<Record<string, unknown>>;
    registerSource: (source: Record<string, unknown>) => Promise<Record<string, unknown>>;
    checkSource: (id: string, content?: string) => Promise<Record<string, unknown>>;
    recordInstrument: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    recordChange: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    authenticate: (id: string) => Promise<Record<string, unknown>>;
    understand: (id: string, summary: string) => Promise<Record<string, unknown>>;
    assess: (id: string, impacts: Record<string, unknown>[]) => Promise<Record<string, unknown>>;
    recommend: (id: string, recommendations: string[]) => Promise<Record<string, unknown>>;
    authorise: (id: string, payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    implement: (id: string, evidence: Record<string, unknown>) => Promise<Record<string, unknown>>;
    verify: (id: string, evidence: Record<string, unknown>) => Promise<Record<string, unknown>>;
    alerts: (severity?: string) => Promise<Record<string, unknown>>;
    status: () => Promise<Record<string, unknown>>;
  };
  publicRecords: {
    registerSource: (source: Record<string, unknown>) => Promise<Record<string, unknown>>;
    sources: () => Promise<Record<string, unknown>>;
    ingest: (record: Record<string, unknown>) => Promise<Record<string, unknown>>;
    search: (filters?: Record<string, string | number>) => Promise<Record<string, unknown>>;
    crossReference: (id: string, body: Record<string, unknown>) => Promise<Record<string, unknown>>;
    correct: (id: string, body: Record<string, unknown>) => Promise<Record<string, unknown>>;
    relationships: (id: string) => Promise<Record<string, unknown>>;
    status: () => Promise<Record<string, unknown>>;
  };
  /** Creator channel: locally reviewed, signed decisions (OD-03/OD-19). */
  creator: {
    policy: () => Promise<Record<string, unknown>>;
    pending: (status?: string) => Promise<Record<string, unknown>>;
    get: (id: string) => Promise<Record<string, unknown>>;
    challenge: (id: string) => Promise<Record<string, unknown>>;
    decide: (
      id: string,
      decision: "approved" | "rejected",
      signature: string,
      signerId: string,
    ) => Promise<Record<string, unknown>>;
  };
  events: { stream: () => EventSource | null };

  constructor(options: IAMOptions) {
    this.transport = new Transport(options);

    this.core = {
      status: () => this.transport.request("GET", "/health"),
    };
    this.tasks = {
      submit: async (task) => {
        if (!this.connected) {
          this.queue.push(task);
          throw new IAMError("offline: task queued locally", 0, "offline");
        }
        return this.transport.request<Task>("POST", "/api/v1/autonomy/tasks/", task);
      },
      get: (id) =>
        this.transport.request<Task>("GET", `/api/v1/autonomy/tasks/${id}`),
      flushQueue: async () => {
        let sent = 0;
        while (this.queue.length) {
          const task = this.queue.shift()!;
          await this.transport.request("POST", "/api/v1/autonomy/tasks/", task);
          sent++;
        }
        return sent;
      },
    };
    this.nodes = {
      register: (node) =>
        this.transport.request("POST", "/api/v1/nodes/register", node),
      status: (id) => this.transport.request("GET", `/api/v1/nodes/${id}`),
      attest: (id, payload, signature) =>
        this.transport.request("POST", `/api/v1/nodes/${id}/attestation`, {
          payload,
          signature,
        }),
      restrict: (id, reason) =>
        this.transport.request("POST", `/api/v1/nodes/${id}/restricted-report`, {
          reason,
        }),
      revoke: (id) =>
        this.transport.request("POST", `/api/v1/nodes/${id}/revoke`),
    };
    this.integrity = {
      status: () => this.transport.request("GET", "/api/v1/integrity/status"),
      approve: () =>
        this.transport.request("POST", "/api/v1/integrity/manifest", {
          confirm: true,
        }),
    };
    this.resources = {
      report: async (nodeId, report) => {
        await this.transport.request(
          "POST",
          `/api/v1/nodes/${nodeId}/resources`,
          report,
        );
      },
    };
    this.files = {
      upload: (name, content) =>
        this.transport.request("POST", "/api/v1/storage/objects", { name, content }),
      get: (id) => this.transport.request("GET", `/api/v1/storage/objects/${id}`),
    };
    this.knowledge = {
      submit: (c) =>
        this.transport.request("POST", "/api/v1/knowledge/contributions", c),
    };
    this.sync = {
      status: () => this.transport.request("GET", "/api/v1/sync/status"),
      publish: (object) =>
        this.transport.request("POST", "/api/v1/sync/objects", object),
      list: (since) =>
        this.transport.request(
          "GET",
          `/api/v1/sync/objects${since ? `?since=${encodeURIComponent(since)}` : ""}`,
        ),
    };
    this.diagnostics = {
      status: () =>
        this.transport.request("GET", "/api/v1/nodes/protocol/diagnostics"),
    };
    this.uwaie = {
      inspect: (url) =>
        this.transport.request("POST", "/api/v1/uwaie/inspect", { url }),
      execute: (payload) =>
        this.transport.request("POST", "/api/v1/uwaie/execute", payload),
      workflows: () => this.transport.request("GET", "/api/v1/uwaie/workflows"),
    };
    const fs = "/api/v1/free-sandboxes";
    this.freeSandbox = {
      policy: () => this.transport.request("GET", `${fs}/policy`),
      providers: () => this.transport.request("GET", `${fs}/providers`),
      discover: () => this.transport.request("POST", `${fs}/discover`),
      requestRegistration: (name) =>
        this.transport.request("POST", `${fs}/providers/${encodeURIComponent(name)}/request-registration`),
      verifyCredentials: (name) =>
        this.transport.request("POST", `${fs}/providers/${encodeURIComponent(name)}/verify-credentials`),
      verifyQuota: (name) =>
        this.transport.request("POST", `${fs}/providers/${encodeURIComponent(name)}/verify-quota`),
      status: () => this.transport.request("GET", `${fs}/status`),
      monitor: () => this.transport.request("POST", `${fs}/monitor`),
      expiryCalendar: () => this.transport.request("GET", `${fs}/expiry-calendar`),
      provision: (payload) => this.transport.request("POST", `${fs}/provision`, payload),
      recover: (payload) => this.transport.request("POST", `${fs}/recover`, payload),
      environments: () => this.transport.request("GET", `${fs}/environments`),
      environment: (id) =>
        this.transport.request("GET", `${fs}/environments/${encodeURIComponent(id)}`),
      start: (id) =>
        this.transport.request("POST", `${fs}/environments/${encodeURIComponent(id)}/start`),
      stop: (id) =>
        this.transport.request("POST", `${fs}/environments/${encodeURIComponent(id)}/stop`),
      remove: (id) =>
        this.transport.request("DELETE", `${fs}/environments/${encodeURIComponent(id)}`),
      results: (id) =>
        this.transport.request("POST", `${fs}/environments/${encodeURIComponent(id)}/results`),
    };

    const lab = "/api/v1/assistant-lab";
    this.assistantLab = {
      boundaries: () => this.transport.request("GET", `${lab}/boundaries`),
      registerSystem: (payload) => this.transport.request("POST", `${lab}/systems`, payload),
      systems: () => this.transport.request("GET", `${lab}/systems`),
      addNote: (payload) => this.transport.request("POST", `${lab}/notes`, payload),
      notes: (assistantId, topic) =>
        this.transport.request(
          "GET",
          `${lab}/notes?assistant_id=${assistantId}${topic ? `&topic=${topic}` : ""}`,
        ),
      registerAdapter: (payload) => this.transport.request("POST", `${lab}/adapters`, payload),
      adapters: (assistantId) => this.transport.request("GET", `${lab}/adapters?assistant_id=${assistantId}`),
      startExperiment: (payload) => this.transport.request("POST", `${lab}/experiments`, payload),
      experiments: () => this.transport.request("GET", `${lab}/experiments`),
      recordResult: (id, payload) =>
        this.transport.request("POST", `${lab}/experiments/${id}/result`, payload),
      adoptExperiment: (id, approvalReference) =>
        this.transport.request("POST", `${lab}/experiments/${id}/adopt`, {
          creator_approval_reference: approvalReference,
        }),
      compare: (payload) => this.transport.request("POST", `${lab}/comparisons`, payload),
      comparisons: (capability) =>
        this.transport.request("GET", `${lab}/comparisons${capability ? `?capability=${capability}` : ""}`),
      status: () => this.transport.request("GET", `${lab}/status`),
    };

    const hp = "/api/v1/human-presence";
    this.humanPresence = {
      boundaries: () => this.transport.request("GET", `${hp}/boundaries`),
      createPerson: (payload) => this.transport.request("POST", `${hp}/people`, payload),
      people: (name) =>
        this.transport.request("GET", `${hp}/people${name ? `?name=${encodeURIComponent(name)}` : ""}`),
      addProfile: (payload) => this.transport.request("POST", `${hp}/profiles`, payload),
      verifyProfile: (id) => this.transport.request("POST", `${hp}/profiles/${id}/verify`),
      addClaim: (payload) => this.transport.request("POST", `${hp}/claims`, payload),
      matchPeople: (id, payload) =>
        this.transport.request("POST", `${hp}/people/${id}/match`, payload),
      addRelationship: (payload) => this.transport.request("POST", `${hp}/relationships`, payload),
      profiles: (id) => this.transport.request("GET", `${hp}/people/${id}/profiles`),
      claims: (id) => this.transport.request("GET", `${hp}/people/${id}/claims`),
      timeline: (id) => this.transport.request("GET", `${hp}/people/${id}/timeline`),
    };

    const geo = "/api/v1/geo";
    this.geo = {
      registerProvider: (provider) => this.transport.request("POST", `${geo}/providers`, provider),
      providers: (kind) =>
        this.transport.request("GET", `${geo}/providers${kind ? `?kind=${kind}` : ""}`),
      mapConfig: (kind = "tile") =>
        this.transport.request("GET", `${geo}/map/config?kind=${kind}`),
      addPlace: (place) => this.transport.request("POST", `${geo}/places`, place),
      places: (query, countryCode) =>
        this.transport.request(
          "GET",
          `${geo}/places?query=${encodeURIComponent(query)}${countryCode ? `&country_code=${countryCode}` : ""}`,
        ),
      nearby: (lat, lon, radiusKm = 25) =>
        this.transport.request(
          "GET",
          `${geo}/places/nearby?latitude=${lat}&longitude=${lon}&radius_km=${radiusKm}`,
        ),
      reverse: (lat, lon, radiusKm = 25) =>
        this.transport.request(
          "GET",
          `${geo}/places/reverse?latitude=${lat}&longitude=${lon}&radius_km=${radiusKm}`,
        ),
      geocode: (payload) => this.transport.request("POST", `${geo}/geocode`, payload),
      importGeoJSON: (payload) => this.transport.request("POST", `${geo}/data`, payload),
      exportGeoJSON: (placeIds) =>
        this.transport.request(
          "GET",
          `${geo}/data/export${placeIds?.length ? `?place_ids=${placeIds.join(",")}` : ""}`,
        ),
      registerFeed: (feed) => this.transport.request("POST", `${geo}/feeds`, feed),
      feeds: () => this.transport.request("GET", `${geo}/feeds`),
      snapshotFeed: (id, data) =>
        this.transport.request("POST", `${geo}/feeds/${id}/snapshot`, { data }),
      cacheTile: (payload) => this.transport.request("POST", `${geo}/tiles`, payload),
      tileStatus: () => this.transport.request("GET", `${geo}/tiles/status`),
      grantPermission: (payload) => this.transport.request("POST", `${geo}/permissions`, payload),
      resolveLocation: (subject, lat, lon) =>
        this.transport.request(
          "GET",
          `${geo}/location?subject=${encodeURIComponent(subject)}${lat !== undefined ? `&latitude=${lat}&longitude=${lon}` : ""}`,
        ),
      status: () => this.transport.request("GET", `${geo}/status`),
    };

    const law = "/api/v1/legal";
    this.legal = {
      sources: () => this.transport.request("GET", `${law}/sources`),
      registerSource: (source) => this.transport.request("POST", `${law}/sources`, source),
      checkSource: (id, content) =>
        this.transport.request("POST", `${law}/sources/${id}/check`, { content }),
      recordInstrument: (payload) => this.transport.request("POST", `${law}/instruments`, payload),
      recordChange: (payload) => this.transport.request("POST", `${law}/changes`, payload),
      authenticate: (id) => this.transport.request("POST", `${law}/changes/${id}/authenticate`),
      understand: (id, summary) =>
        this.transport.request("POST", `${law}/changes/${id}/understand`, { summary }),
      assess: (id, impacts) =>
        this.transport.request("POST", `${law}/changes/${id}/assess`, { impacts }),
      recommend: (id, recommendations) =>
        this.transport.request("POST", `${law}/changes/${id}/recommend`, { recommendations }),
      authorise: (id, payload) =>
        this.transport.request("POST", `${law}/changes/${id}/authorise`, payload),
      implement: (id, evidence) =>
        this.transport.request("POST", `${law}/changes/${id}/implement`, { evidence }),
      verify: (id, evidence) =>
        this.transport.request("POST", `${law}/changes/${id}/verify`, { evidence }),
      alerts: (severity) =>
        this.transport.request("GET", `${law}/alerts${severity ? `?severity=${severity}` : ""}`),
      status: () => this.transport.request("GET", `${law}/status`),
    };

    const pr = "/api/v1/public-records";
    this.publicRecords = {
      registerSource: (source) => this.transport.request("POST", `${pr}/sources`, source),
      sources: () => this.transport.request("GET", `${pr}/sources`),
      ingest: (record) => this.transport.request("POST", `${pr}/records`, record),
      search: (filters = {}) => {
        const query = new URLSearchParams(
          Object.entries(filters).map(([key, value]) => [key, String(value)]),
        );
        return this.transport.request("GET", `${pr}/records?${query}`);
      },
      crossReference: (id, body) =>
        this.transport.request("POST", `${pr}/records/${id}/cross-reference`, body),
      correct: (id, body) =>
        this.transport.request("POST", `${pr}/records/${id}/corrections`, body),
      relationships: (id) => this.transport.request("GET", `${pr}/records/${id}/relationships`),
      status: () => this.transport.request("GET", `${pr}/status`),
    };
    const creator = "/api/v1/creator";
    this.creator = {
      policy: () => this.transport.request("GET", `${creator}/policy`),
      pending: (status = "pending") =>
        this.transport.request(
          "GET",
          `${creator}/requests${status ? `?status=${encodeURIComponent(status)}` : ""}`,
        ),
      get: (id) =>
        this.transport.request("GET", `${creator}/requests/${encodeURIComponent(id)}`),
      challenge: (id) =>
        this.transport.request(
          "GET",
          `${creator}/requests/${encodeURIComponent(id)}/challenge`,
        ),
      decide: (id, decision, signature, signerId) =>
        this.transport.request(
          "POST",
          `${creator}/requests/${encodeURIComponent(id)}/decide`,
          { decision, signature, signer_id: signerId },
        ),
    };
    this.events = {
      stream: () => {
        if (typeof EventSource === "undefined") return null;
        const url = `${options.endpoint.replace(/\/$/, "")}/api/v1/events`;
        const source = new EventSource(url);
        return source;
      },
    };
  }

  async connect(): Promise<void> {
    await this.core.status();
    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.connected = false;
  }

  get queuedTasks(): number {
    return this.queue.length;
  }
}
