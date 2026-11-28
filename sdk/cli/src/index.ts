#!/usr/bin/env node
/** IAM CLI - thin wrapper over @iam/sdk. No separate protocol or auth path. */

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { IAM, type NodeRegistration } from "@iamagris/sdk";

const CREDENTIAL_PATH = join(homedir(), ".config", "iam", "token");

async function storedToken(): Promise<string | undefined> {
  if (process.env.IAM_TOKEN) return process.env.IAM_TOKEN;
  try {
    const token = await readFile(CREDENTIAL_PATH, "utf8");
    return token.trim() || undefined;
  } catch {
    return undefined;
  }
}

const args = process.argv.slice(2);
const [group, action, ...rest] = args;

async function client(): Promise<IAM> {
  return new IAM({
    endpoint: process.env.IAM_CORE_URL ?? "http://localhost:8000",
    token: await storedToken(),
  });
}

function fail(message: string): never {
  console.error(`iam: ${message}`);
  process.exit(1);
}

async function main(): Promise<void> {
  if (!group || group === "help") {
    console.log(`iam <command> [options]

  iam login                  Store a scoped token in the local credential store
  iam core status            Show core status
  iam node register          Register this deployment as a candidate node
  iam node status <id>       Show node status
  iam dev init               Scaffold a local IAM project
  iam dev test               Run local SDK contract tests
  iam storage status         Show core-authorised storage status
  iam sync status            Show synchronisation status
  iam asset list             List owner-owned digital assets
  iam asset register <json>  Register a digital asset
  iam domain list            List recorded domain registrations
  iam domain register <json> Record a domain registration (metadata only)
  iam sandbox status         Show free-sandbox policy and scheduler health
  iam sandbox providers      List free infrastructure providers
  iam sandbox discover       Discover eligible free providers
  iam sandbox monitor        Poll provider quotas once
  iam sandbox provision <json>  Provision a workload on a free provider`);
    return;
  }

  if (group === "login") {
    const token = action ?? process.env.IAM_TOKEN;
    if (!token) fail("login requires a scoped token argument or IAM_TOKEN");
    await mkdir(join(homedir(), ".config", "iam"), { recursive: true, mode: 0o700 });
    await writeFile(CREDENTIAL_PATH, `${token.trim()}\n`, { mode: 0o600 });
    console.log(`Stored scoped token in ${CREDENTIAL_PATH}`);
    return;
  }

  const iam = await client();

  switch (`${group} ${action ?? ""}`.trim()) {
    case "core status":
      console.log(await iam.core.status());
      break;
    case "node register": {
      const node: NodeRegistration = {
        name: rest[0] ?? process.env.IAM_NODE_NAME ?? "local-node",
        architecture: process.arch === "arm64" ? "arm64" : "x86-64",
        resources: {
          cpuCores: Number(process.env.IAM_CPU_CORES ?? 1),
          ramBytes: Number(process.env.IAM_RAM_BYTES ?? 0),
          storageBytes: Number(process.env.IAM_STORAGE_BYTES ?? 0),
          permittedContributionPercent: Number(
            process.env.IAM_CONTRIBUTION_PERCENT ?? 1,
          ),
        },
      };
      console.log(await iam.nodes.register(node));
      break;
    }
    case "node status":
      if (!rest[0]) fail("node status requires a node id");
      console.log(await iam.nodes.status(rest[0]));
      break;
    case "dev init": {
      await mkdir(".", { recursive: true });
      for (const [name, body] of [
        [".env.example", "IAM_CORE_URL=http://localhost:8000\n# IAM_TOKEN=scoped-token\n"],
        ["iam.config.json", '{"endpoint":"http://localhost:8000"}\n'],
      ] as const) {
        try {
          await writeFile(name, body, { flag: "wx" });
          console.log(`created ${name}`);
        } catch (error) {
          if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
          console.log(`${name} already exists (unchanged)`);
        }
      }
      break;
    }
    case "dev test":
      console.log(await iam.diagnostics.status());
      break;
    case "storage status":
      console.log(await iam.files.get("@status"));
      break;
    case "sync status":
      console.log(await iam.sync.status());
      break;
    case "asset list":
      console.log(await iam.digitalAssets.list());
      break;
    case "asset register":
      if (!rest[0]) fail("asset register requires a JSON payload");
      console.log(await iam.digitalAssets.create(JSON.parse(rest[0])));
      break;
    case "domain list":
      console.log(await iam.digitalAssets.domains());
      break;
    case "domain register":
      if (!rest[0]) fail("domain register requires a JSON payload");
      console.log(await iam.digitalAssets.registerDomain(JSON.parse(rest[0])));
      break;
    case "sandbox status":
      console.log(await iam.freeSandbox.status());
      break;
    case "sandbox providers":
      console.log(await iam.freeSandbox.providers());
      break;
    case "sandbox discover":
      console.log(await iam.freeSandbox.discover());
      break;
    case "sandbox monitor":
      console.log(await iam.freeSandbox.monitor());
      break;
    case "sandbox provision": {
      if (!rest[0]) fail("sandbox provision requires a JSON payload");
      console.log(await iam.freeSandbox.provision(JSON.parse(rest[0])));
      break;
    }
    default:
      fail(`unknown command: ${group}${action ? ` ${action}` : ""}`);
  }
}

main().catch((error) => fail(error instanceof Error ? error.message : String(error)));
