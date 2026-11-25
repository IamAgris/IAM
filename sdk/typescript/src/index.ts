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
  };
  resources: { report: (nodeId: string, report: ResourceReport) => Promise<void> };
  files: {
    upload: (name: string, content: string) => Promise<Record<string, unknown>>;
    get: (id: string) => Promise<Record<string, unknown>>;
  };
  knowledge: { submit: (c: Contribution) => Promise<Record<string, unknown>> };
  sync: { status: () => Promise<Record<string, unknown>> };
  diagnostics: { status: () => Promise<Record<string, unknown>> };
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
    this.sync = { status: () => this.transport.request("GET", "/api/v1/sync/status") };
    this.diagnostics = {
      status: () => this.transport.request("GET", "/api/v1/diagnostics"),
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
