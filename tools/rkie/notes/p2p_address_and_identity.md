# P2P address and stable node identity (27 November 2026)

P2P has **no separate port**: it is a WebSocket route on the backend HTTP service.

## Addresses

| Context | Address |
|---------|---------|
| Host machine | `ws://localhost:8000/api/v1/p2p/ws/<peer_id>` |
| Another container on `aura-network` | `ws://backend:8000/api/v1/p2p/ws/<peer_id>` |
| Through the optional Caddy edge | `ws://localhost:8080/api/v1/p2p/ws/<peer_id>` |
| Public TLS domain (once configured) | `wss://<domain>/api/v1/p2p/ws/<peer_id>` |

The shared signing secret can be supplied as `?secret=` or the `X-Peer-Secret` header
(header preferred so the secret is not in the URL).

## Identity fix

Previously `p2p_transport` used `node_id="local-iam"` and a random secret per process, so
peers could not reconnect after a restart. Added:

- `backend/app/core/config.py`: `iam_node_id`, `iam_p2p_secret`
- `backend/app/main.py`: `transport.configure(settings.iam_node_id, settings.iam_p2p_secret)` at startup
- `backend/app/api/routes/p2p.py`: accepts `X-Peer-Secret` header
- `docker-compose.yml` / `.env.example` / `.env`: `IAM_NODE_ID=iam-core`, `IAM_P2P_SECRET` set locally

## Verification

- Startup log: `P2P node identity configured: iam-core`
- `GET /api/v1/p2p/status` (admin credential) → `node_id: iam-core`

Peers remain untrusted until attested (OD-12/OD-13); a live two-node sync has not been run.
