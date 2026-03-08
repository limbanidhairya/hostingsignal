"""Cluster Management API Routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import json

router = APIRouter(prefix="/api/cluster", tags=["Cluster"])

CLUSTER_CONFIG_PATH = "/usr/local/hostingsignal/config/cluster.json"
DEFAULT_CLUSTER_CONFIG = {
    "enabled": False,
    "node_id": "",
    "role": "standalone",  # standalone, master, worker
    "master_url": "",
    "api_key": "",
    "heartbeat_interval": 30,
    "nodes": [],
}


class ClusterJoinRequest(BaseModel):
    master_url: str
    api_key: str
    node_name: Optional[str] = ""


class ClusterNodeInfo(BaseModel):
    hostname: str
    ip_address: str
    port: int = 8000
    role: str = "worker"


def _load_cluster_config() -> dict:
    if os.path.exists(CLUSTER_CONFIG_PATH):
        with open(CLUSTER_CONFIG_PATH) as f:
            return {**DEFAULT_CLUSTER_CONFIG, **json.load(f)}
    return DEFAULT_CLUSTER_CONFIG


def _save_cluster_config(config: dict):
    os.makedirs(os.path.dirname(CLUSTER_CONFIG_PATH), exist_ok=True)
    with open(CLUSTER_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


@router.get("/status")
async def cluster_status():
    """Get current cluster status."""
    config = _load_cluster_config()
    return {
        "enabled": config["enabled"],
        "role": config["role"],
        "node_id": config["node_id"],
        "master_url": config["master_url"],
        "nodes": config.get("nodes", []),
        "node_count": len(config.get("nodes", [])),
    }


@router.post("/join")
async def join_cluster(req: ClusterJoinRequest):
    """Join an existing cluster as a worker node."""
    config = _load_cluster_config()

    # Register with master
    try:
        import socket
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{req.master_url}/api/cluster/register",
                json={
                    "hostname": req.node_name or hostname,
                    "ip_address": ip_address,
                    "port": 8000,
                    "role": "worker",
                },
                headers={"X-Cluster-Key": req.api_key},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to register with master")
            result = resp.json()

        config["enabled"] = True
        config["role"] = "worker"
        config["master_url"] = req.master_url
        config["api_key"] = req.api_key
        config["node_id"] = result.get("node_id", "")
        _save_cluster_config(config)

        return {"status": "joined", "node_id": config["node_id"], "master": req.master_url}
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach master: {str(e)}")


@router.post("/leave")
async def leave_cluster():
    """Leave the current cluster."""
    config = _load_cluster_config()
    if not config["enabled"]:
        raise HTTPException(status_code=400, detail="Not part of a cluster")

    # Notify master
    if config["master_url"] and config["node_id"]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{config['master_url']}/api/cluster/deregister",
                    json={"node_id": config["node_id"]},
                    headers={"X-Cluster-Key": config["api_key"]},
                )
        except Exception:
            pass  # Best effort

    config["enabled"] = False
    config["role"] = "standalone"
    config["master_url"] = ""
    config["api_key"] = ""
    config["node_id"] = ""
    config["nodes"] = []
    _save_cluster_config(config)

    return {"status": "left", "role": "standalone"}


@router.post("/register")
async def register_node(node: ClusterNodeInfo):
    """Register a new worker node (master endpoint)."""
    config = _load_cluster_config()
    if config["role"] != "master":
        raise HTTPException(status_code=403, detail="Only master can accept registrations")

    import uuid
    node_id = str(uuid.uuid4())[:8]
    node_entry = {
        "node_id": node_id,
        "hostname": node.hostname,
        "ip_address": node.ip_address,
        "port": node.port,
        "role": node.role,
        "status": "online",
        "joined_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
    config.setdefault("nodes", []).append(node_entry)
    _save_cluster_config(config)

    return {"node_id": node_id, "status": "registered"}


@router.post("/deregister")
async def deregister_node(data: dict):
    """Remove a worker node (master endpoint)."""
    config = _load_cluster_config()
    node_id = data.get("node_id")
    config["nodes"] = [n for n in config.get("nodes", []) if n.get("node_id") != node_id]
    _save_cluster_config(config)
    return {"status": "removed"}


@router.get("/nodes")
async def list_nodes():
    """List all nodes in the cluster."""
    config = _load_cluster_config()
    return {"nodes": config.get("nodes", []), "count": len(config.get("nodes", []))}


@router.post("/init")
async def init_master():
    """Initialize this node as cluster master."""
    config = _load_cluster_config()
    import uuid
    config["enabled"] = True
    config["role"] = "master"
    config["node_id"] = str(uuid.uuid4())[:8]
    config["api_key"] = str(uuid.uuid4())
    _save_cluster_config(config)

    return {
        "status": "initialized",
        "role": "master",
        "node_id": config["node_id"],
        "api_key": config["api_key"],
    }
