import axios from "axios";

// GET-only helper for internal IAM views. It routes through the server-side
// /iam-proxy allowlist so the browser never holds an IAM credential.
// Response shape matches axios so existing page components need only swap
// api.get(...) for secureGet(...); mutation calls stay on the normal api client.
const client = axios.create({ baseURL: "" });

export function secureGet<T = any>(path: string) {
  const proxied = path.startsWith("/api/") ? `/iam-proxy${path}` : path;
  return client.get<T>(proxied);
}
