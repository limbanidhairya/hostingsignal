"""Developer Panel — Cluster Control API (service-backed)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db, ManagedServer
from ..services.cluster_manager import cluster_manager

router = APIRouter(prefix="/api/clusters", tags=["Cluster Control"])


class RegisterNodeRequest(BaseModel):
    hostname: str
    ip_address: str
    role: str = "worker"  # master | worker
    region: Optional[str] = None
    specs: Optional[dict] = None  # cpu, ram, disk
    port: int = 8000
    cluster_id: Optional[str] = None
    os_info: Optional[str] = None
    license_key: Optional[str] = None


class NodeCommandRequest(BaseModel):
    command: str  # restart_services | update | sync_config | drain | undrain
    payload: Optional[dict] = None


@router.post("/nodes/register")
async def register_node(body: RegisterNodeRequest, db: AsyncSession = Depends(get_db)):
    """Register a server node in the cluster database."""
    try:
        node = await cluster_manager.register_server(
            db=db,
            hostname=body.hostname,
            ip_address=body.ip_address,
            port=body.port,
            cluster_id=body.cluster_id,
            os_info=body.os_info,
            license_key=body.license_key,
        )
        return {
            "success": True,
            "node": {
                "id": str(node.id),
                "hostname": node.hostname,
                "ip_address": node.ip_address,
                "status": node.status,
                "cluster_id": str(node.cluster_id) if node.cluster_id else None,
            },
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/nodes")
async def list_nodes(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List cluster nodes."""
    stmt = select(ManagedServer)
    if status:
        stmt = stmt.where(ManagedServer.status == status)
    result = await db.execute(stmt.order_by(ManagedServer.created_at.desc()))
    nodes = result.scalars().all()

    return {
        "nodes": [
            {
                "id": str(n.id),
                "hostname": n.hostname,
                "ip_address": n.ip_address,
                "status": n.status,
                "cluster_id": str(n.cluster_id) if n.cluster_id else None,
                "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
            }
            for n in nodes
        ],
        "total": len(nodes),
    }


@router.get("/nodes/{node_id}")
async def get_node(node_id: str, db: AsyncSession = Depends(get_db)):
    """Get node details."""
    result = await db.execute(select(ManagedServer).where(ManagedServer.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {
        "id": str(node.id),
        "hostname": node.hostname,
        "ip_address": node.ip_address,
        "port": node.port,
        "status": node.status,
        "panel_version": node.panel_version,
        "os_info": node.os_info,
        "cluster_id": str(node.cluster_id) if node.cluster_id else None,
        "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
    }


@router.post("/nodes/{node_id}/command")
async def send_command(node_id: str, body: NodeCommandRequest, db: AsyncSession = Depends(get_db)):
    """Send a command to a node."""
    result = await db.execute(select(ManagedServer).where(ManagedServer.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    payload = await cluster_manager.push_command(node, body.command, body.payload)
    return {"success": True, "node_id": node_id, "command": body.command, "result": payload}


@router.delete("/nodes/{node_id}")
async def remove_node(node_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a node from the cluster."""
    try:
        await cluster_manager.remove_server(db, node_id)
        return {"success": True, "message": "Node removed"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/overview")
async def cluster_overview(db: AsyncSession = Depends(get_db)):
    """Cluster overview stats."""
    result = await db.execute(select(ManagedServer))
    nodes = result.scalars().all()
    total = len(nodes)
    online = sum(1 for n in nodes if n.status == "online")
    offline = sum(1 for n in nodes if n.status == "offline")
    return {
        "total_nodes": total,
        "online": online,
        "offline": offline,
        "degraded": max(total - online - offline, 0),
    }
