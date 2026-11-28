// Server-only proxy for internal IAM views. The browser never receives an IAM
// credential. Only these read-only / analysis paths are allowed; no Creator
// authority, spending, provisioning or protected-core action can pass through.

export const dynamic = "force-dynamic";

const ALLOWED = [
  { pattern: /^api\/v1\/tone\/analyze$/, methods: ["POST"] },
  { pattern: /^api\/v1\/tone\/records$/, methods: ["GET"] },
  { pattern: /^api\/v1\/network\/agents$/, methods: ["GET"] },
  { pattern: /^api\/v1\/network\/interactions$/, methods: ["GET"] },
  { pattern: /^api\/v1\/network\/collaborations$/, methods: ["GET"] },
  { pattern: /^api\/v1\/network\/agents\/[^/]+\/profile$/, methods: ["GET"] },
  { pattern: /^api\/v1\/network\/agents\/[^/]+\/interviews$/, methods: ["GET"] },
  // Read-only views for free infrastructure and financial intelligence.
  // State-changing endpoints on these prefixes stay outside the allowlist.
  { pattern: /^api\/v1\/free-sandboxes\/(status|providers|environments|policy|expiry-calendar)$/, methods: ["GET"] },
  { pattern: /^api\/v1\/prediction-markets\/(policy|markets|adapter\/status|adapter\/policy|forecast\/policy)$/, methods: ["GET"] },
  { pattern: /^api\/v1\/gaming-intelligence\/(policy|records)$/, methods: ["GET"] },
  { pattern: /^api\/v1\/investment-intelligence\/(policy|records)$/, methods: ["GET"] },
  { pattern: /^api\/v1\/provider-registry\/(entries|policy)$/, methods: ["GET"] },
];

function allowed(path: string, method: string) {
  return ALLOWED.some((rule) => rule.pattern.test(path) && rule.methods.includes(method));
}

async function handler(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const targetPath = path.join("/");
  const method = request.method.toUpperCase();

  if (!allowed(targetPath, method)) {
    return Response.json({ detail: "path or method not allowed" }, { status: 403 });
  }

  const token = process.env.IAM_PROXY_TOKEN;
  if (!token) {
    return Response.json(
      { detail: "IAM proxy token not configured on the server" },
      { status: 503 },
    );
  }

  const base = (process.env.IAM_API_URL || "http://localhost:8000").replace(/\/$/, "");
  const query = new URL(request.url).search;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };

  let body: string | undefined;
  if (method === "POST") {
    try {
      body = JSON.stringify(await request.json());
    } catch {
      return Response.json({ detail: "invalid JSON body" }, { status: 400 });
    }
  }

  try {
    const response = await fetch(`${base}/${targetPath}${query}`, {
      method,
      headers,
      body,
      cache: "no-store",
    });
    const text = await response.text();
    return new Response(text, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return Response.json({ detail: "IAM backend unreachable" }, { status: 502 });
  }
}

export { handler as GET, handler as POST };
