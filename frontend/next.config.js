/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Local CPU inference can take >30s before the first SSE token. The Next.js
  // dev rewrite proxy otherwise aborts the stream with ERR_INCOMPLETE_CHUNKED_ENCODING.
  experimental: { proxyTimeout: 180000 },
  async rewrites() {
    // Inside Docker, localhost is the frontend container itself — use the
    // compose-provided service URL. Local `next dev` falls back to localhost.
    const api = (process.env.IAM_API_URL || "http://localhost:8000").replace(/\/$/, "");
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/health", destination: `${api}/health` },
    ];
  },
};

module.exports = nextConfig;
