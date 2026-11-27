"""P2P transport routes — WebSocket peer connections and store-and-forward sync."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json

from app.core.database import get_db_session
from app.services.p2p_transport import transport
from app.services.skill_exchange_service import SkillExchangeError, SkillExchangeService
from app.services.whitehat_policy import WhiteHatPolicyError

router = APIRouter(prefix="/api/v1/p2p", tags=["p2p"])


class SendRequest(BaseModel):
    peer_id: str
    topic: str
    payload: Dict[str, Any] = {}


class BroadcastRequest(BaseModel):
    topic: str
    payload: Dict[str, Any] = {}


class SkillReleaseRequest(BaseModel):
    envelope: Dict[str, Any]
    peer_secret: Optional[str] = None


class SkillPublishRequest(BaseModel):
    skill_id: str
    peer_id: Optional[str] = None


@router.post("/send")
async def send(request: SendRequest):
    """Send a signed message to a peer (queued if offline)."""
    try:
        return await transport.send_to(request.peer_id, request.topic, request.payload)
    except WhiteHatPolicyError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/broadcast")
async def broadcast(request: BroadcastRequest):
    """Gossip a message to all connected peers."""
    try:
        return await transport.broadcast(request.topic, request.payload)
    except WhiteHatPolicyError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.get("/outbox/{peer_id}")
async def drain(peer_id: str):
    """Retrieve messages queued while a peer was offline."""
    return {"peer_id": peer_id, "messages": transport.drain(peer_id)}


@router.get("/status")
async def status():
    return {
        "node_id": transport.node_id,
        "connected_peers": list(transport.connections.keys()),
        "queued_peers": {k: len(v) for k, v in transport.outbox.items()},
        "last_seen_seqs": dict(transport.seq),
    }


@router.websocket("/ws/{peer_id}")
async def peer_socket(websocket: WebSocket, peer_id: str, secret: Optional[str] = None):
    """Persistent peer connection: exchange signed envelopes, drain offline queue.

    ?secret= sets the shared signing secret for this peer's messages.
    """
    await websocket.accept()
    peer_secret = secret or transport.local_secret
    transport.register_ws(peer_id, websocket)

    # Deliver anything queued while this peer was offline
    for env in transport.drain(peer_id):
        try:
            await websocket.send_json(env)
        except Exception:
            break

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                env = json.loads(raw)
            except Exception:
                await websocket.send_json({"error": "invalid_json"})
                continue

            result = transport.accept(env, peer_secret=peer_secret)
            await websocket.send_json({"ack": result.get("accepted"), "reason": result.get("reason")})

            if result.get("accepted"):
                # Echo to other peers (gossip) — exclude sender
                for other, ws in list(transport.connections.items()):
                    if other != peer_id:
                        try:
                            await ws.send_json(env)
                        except Exception:
                            transport.queue_for(other, env)
    except WebSocketDisconnect:
        pass
    finally:
        transport.unregister_ws(peer_id)
