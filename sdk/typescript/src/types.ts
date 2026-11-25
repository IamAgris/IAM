/** Shared IAM protocol types (v1). Must stay aligned with sdk/python/iam_sdk/types.py. */

export const PROTOCOL_VERSION = "1";

export interface IAMOptions {
  endpoint: string;
  token?: string;
  apiVersion?: string;
  timeoutMs?: number;
  maxRetries?: number;
}

export interface TaskSubmit {
  type: string;
  instruction: string;
  [key: string]: unknown;
}

export interface Task {
  id: string;
  type: string;
  status: string;
  result?: unknown;
}

export interface NodeRegistration {
  name: string;
  architecture: "arm64" | "x86-64" | string;
  resources: {
    cpuCores: number;
    ramBytes: number;
    storageBytes: number;
    permittedContributionPercent: number;
  };
  capabilities?: string[];
}

export interface ResourceReport {
  cpuCores: number;
  ramBytes: number;
  storageBytes: number;
  usedPercent?: number;
}

export interface Contribution {
  type: string;
  summary: string;
  evidence: string[];
}

export class IAMError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "IAMError";
  }
}
