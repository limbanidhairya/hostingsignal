"""
HostingSignal Panel — Monitoring API
Real-time CPU, RAM, disk, network, and service health monitoring.
Includes WebSocket endpoint for live stats.
"""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from typing import List, Dict
import asyncio
import json

from app.core.security import get_current_user
from app.services.system_monitor import SystemMonitor

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])

monitor = SystemMonitor()


@router.get("/overview")
async def get_system_overview(current_user: dict = Depends(get_current_user)):
    """Get a complete system overview with all metrics."""
    try:
        stats = monitor.get_system_stats()
        return {
            "status": "success",
            "data": stats,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/cpu")
async def get_cpu_stats(current_user: dict = Depends(get_current_user)):
    """Get CPU usage statistics."""
    try:
        cpu = monitor.get_cpu_info()
        return {"status": "success", "cpu": cpu}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/memory")
async def get_memory_stats(current_user: dict = Depends(get_current_user)):
    """Get memory usage statistics."""
    try:
        memory = monitor.get_memory_info()
        return {"status": "success", "memory": memory}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/disk")
async def get_disk_stats(current_user: dict = Depends(get_current_user)):
    """Get disk usage statistics."""
    try:
        disk = monitor.get_disk_info()
        return {"status": "success", "disk": disk}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/network")
async def get_network_stats(current_user: dict = Depends(get_current_user)):
    """Get network I/O statistics."""
    try:
        network = monitor.get_network_info()
        return {"status": "success", "network": network}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/services")
async def get_services_status(current_user: dict = Depends(get_current_user)):
    """Get status of all managed services."""
    try:
        services_list = [
            "lsws", "mariadb", "redis-server", "postfix",
            "dovecot", "named", "hostingsignal-api",
            "hostingsignal-web", "hostingsignal-daemon",
        ]
        statuses = {}
        for svc in services_list:
            statuses[svc] = monitor.get_service_status(svc)
        return {"status": "success", "services": statuses}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/processes")
async def get_top_processes(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """Get top processes by CPU/memory usage."""
    try:
        processes = monitor.get_top_processes(limit)
        return {"status": "success", "processes": processes}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/history")
async def get_metrics_history(
    period: str = "1h",  # 1h, 6h, 24h, 7d
    current_user: dict = Depends(get_current_user),
):
    """Get historical metrics data for charts."""
    try:
        # In production, this would fetch from a time-series DB or Redis
        history = monitor.get_metrics_history(period)
        return {"status": "success", "period": period, "history": history}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── WebSocket for real-time monitoring ───────────────────────────────────────

class ConnectionManager:
    """Manages WebSocket connections for real-time monitoring."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass


ws_manager = ConnectionManager()


@router.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket):
    """WebSocket endpoint for real-time system stats."""
    await ws_manager.connect(websocket)
    try:
        while True:
            stats = monitor.get_system_stats()
            await websocket.send_json(stats)
            await asyncio.sleep(2)  # Send stats every 2 seconds
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
