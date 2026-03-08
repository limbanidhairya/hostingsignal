"""Developer Panel — Cluster Control API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import secrets

router = APIRouter(prefix="/api/clusters", tags=["Cluster Control"])

_nodes: dict = {}


class RegisterNodeRequest(BaseModel):
    hostname: str
    ip_address: str
    role: str = "worker"  # master | worker
    region: Optional[str] = None
    specs: Optional[dict] = None  # cpu, ram, disk


class NodeCommandRequest(BaseModel):
    command: str  # restart_services | update | sync_config | drain | undrain


@router.post("/nodes/register")
async def register_node(body: RegisterNodeRequest):
    """Register a server node in the cluster."""
    node_id = f"node_{secrets.token_hex(6)}"
    node = {
        "id": node_id,
        "hostname": body.hostname,
        "ip_address": body.ip_address,
        "role": body.role,
        "region": body.region,
        "specs": body.specs or {},
        "status": "online",
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "websites_count": 0,
    }
    _nodes[node_id] = node
    return {"status": "success", "node": node}


@router.get("/nodes")
async def list_nodes(role: Optional[str] = None, status: Optional[str] = None):
    """List cluster nodes."""
    results = list(_nodes.values())
    if role:
        results = [n for n in results if n["role"] == role]
    if status:
        results = [n for n in results if n["status"] == status]
    return {"nodes": results, "total": len(results)}


@router.get("/nodes/{node_id}")
async def get_node(node_id: str):
    """Get node details."""
    if node_id not in _nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    return _nodes[node_id]


@router.post("/nodes/{node_id}/command")
async def send_command(node_id: str, body: NodeCommandRequest):
    """Send a command to a node."""
    if node_id not in _nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"status": "success", "node_id": node_id, "command": body.command, "message": f"Command '{body.command}' queued"}


@router.delete("/nodes/{node_id}")
async def remove_node(node_id: str):
    """Remove a node from the cluster."""
    if node_id not in _nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    del _nodes[node_id]
    return {"status": "success", "message": "Node removed"}


@router.get("/overview")
async def cluster_overview():
    """Cluster overview stats."""
    nodes = list(_nodes.values())
    total = len(nodes)
    online = sum(1 for n in nodes if n["status"] == "online")
    masters = sum(1 for n in nodes if n["role"] == "master")
    workers = sum(1 for n in nodes if n["role"] == "worker")
    total_websites = sum(n.get("websites_count", 0) for n in nodes)
    return {"total_nodes": total, "online": online, "masters": masters, "workers": workers, "total_websites": total_websites}
