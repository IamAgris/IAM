/** Offline contract tests for the TypeScript SDK (no IAM Core required). */

import assert from "node:assert/strict";
import { createServer, type IncomingMessage, type Server } from "node:http";
import { test } from "node:test";
import type { AddressInfo } from "node:net";

import { IAM } from "./index.js";

test("HBI interface uses versioned /api/v1/hbi paths", async () => {
  await withServer(
    () => ({ status: 200, body: { ok: true } }),
    async (endpoint, seen) => {
      const iam = new IAM({ endpoint });
      assert.deepEqual(await iam.hbi.status(), { ok: true });
      await iam.hbi.research.search("community", "research");
      await iam.hbi.behaviour.predict({
        question: "Will participation rise?",
        target: "participation",
        purpose: "research",
      });
      await iam.hbi.corpus.state();
      await iam.hbi.validation.report();
      const paths = seen.map((item) => item.url);
      assert.equal(paths[0], "/api/v1/hbi/status");
      assert.ok(paths.includes("/api/v1/hbi/behaviour/forecast"));
      assert.ok(paths.includes("/api/v1/hbi/knowledge/corpus/state"));
      assert.ok(paths.some((path) => path.startsWith("/api/v1/hbi/validation/report")));
    },
  );
});

type Seen = { method: string; url: string; headers: IncomingMessage["headers"]; body: string };

async function withServer(
  handler: (seen: Seen, attempt: number) => { status: number; body: unknown },
  run: (endpoint: string, seen: Seen[]) => Promise<void>,
): Promise<void> {
  const seen: Seen[] = [];
  let attempt = 0;
  const server: Server = createServer((req, res) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => chunks.push(chunk));
    req.on("end", () => {
      const record: Seen = {
        method: req.method ?? "",
        url: req.url ?? "",
        headers: req.headers,
        body: Buffer.concat(chunks).toString("utf8"),
      };
      seen.push(record);
      const reply = handler(record, ++attempt);
      res.writeHead(reply.status, { "Content-Type": "application/json" });
      res.end(JSON.stringify(reply.body));
    });
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = (server.address() as AddressInfo).port;
  try {
    await run(`http://127.0.0.1:${port}`, seen);
  } finally {
    await new Promise<void>((resolve, reject) =>
      server.close((error) => (error ? reject(error) : resolve())),
    );
  }
}

test("sends protocol, auth and Cloudflare Access headers", async () => {
  await withServer(
    () => ({ status: 200, body: { ok: true } }),
    async (endpoint, seen) => {
      const iam = new IAM({
        endpoint,
        token: "scoped-token",
        accessClientId: "access-id",
        accessClientSecret: "access-secret",
      });
      assert.deepEqual(await iam.core.status(), { ok: true });
      assert.equal(seen[0].headers["x-iam-protocol-version"], "1");
      assert.equal(seen[0].headers.authorization, "Bearer scoped-token");
      assert.equal(seen[0].headers["cf-access-client-id"], "access-id");
      assert.equal(seen[0].headers["cf-access-client-secret"], "access-secret");
    },
  );
});

test("creator challenge and signed decision use the documented paths", async () => {
  await withServer(
    (seen) => ({
      status: 200,
      body: seen.method === "POST" ? { decided: true } : { challenge_hash: "abc" },
    }),
    async (endpoint, seen) => {
      const iam = new IAM({ endpoint });
      assert.deepEqual(await iam.creator.challenge("cr_1"), { challenge_hash: "abc" });
      assert.deepEqual(
        await iam.creator.decide("cr_1", "approved", "c2ln", "hardware-key"),
        { decided: true },
      );
      assert.equal(seen[0].url, "/api/v1/creator/requests/cr_1/challenge");
      assert.equal(seen[1].url, "/api/v1/creator/requests/cr_1/decide");
      assert.equal(JSON.parse(seen[1].body).decision, "approved");
      assert.equal(JSON.parse(seen[1].body).signer_id, "hardware-key");
      assert.ok(seen[1].headers["idempotency-key"]);
    },
  );
});

test("retries a 429 and then succeeds", async () => {
  await withServer(
    (_seen, attempt) =>
      attempt === 1
        ? { status: 429, body: { detail: "slow down", code: "rate_limited" } }
        : { status: 200, body: { ok: true } },
    async (endpoint, seen) => {
      const iam = new IAM({ endpoint, maxRetries: 2 });
      assert.deepEqual(await iam.core.status(), { ok: true });
      assert.equal(seen.length, 2);
    },
  );
});
