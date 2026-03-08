"""AI Monitoring — API Routes"""
from fastapi import APIRouter, Depends
from ..monitoring import metrics_collector, anomaly_predictor, alert_dispatcher

router = APIRouter(prefix="/api/monitoring/ai", tags=["AI Monitoring"])


@router.get("/metrics")
async def get_current_metrics():
    """Get current system metrics snapshot."""
    return metrics_collector.get_latest()


@router.get("/metrics/history")
async def get_metrics_history(minutes: int = 60):
    """Get metrics history for the specified number of minutes."""
    history = metrics_collector.get_history(minutes)
    return {"history": history, "count": len(history)}


@router.get("/alerts")
async def get_alerts(severity: str = None, limit: int = 50):
    """Get monitoring alerts, optionally filtered by severity."""
    return {"alerts": anomaly_predictor.get_alerts(severity, limit)}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge a monitoring alert."""
    success = anomaly_predictor.acknowledge_alert(alert_id)
    return {"acknowledged": success}


@router.get("/predictions")
async def get_predictions():
    """Get AI predictions for resource usage."""
    return anomaly_predictor.get_predictions()


@router.get("/health")
async def get_health_score():
    """Get overall system health score."""
    return anomaly_predictor.get_health_score()


@router.get("/alerts/config")
async def get_alert_config():
    """Get alert dispatcher configuration."""
    return alert_dispatcher.get_config()


@router.post("/alerts/config")
async def update_alert_config(config: dict):
    """Update alert dispatcher configuration."""
    alert_dispatcher.save_config(config)
    return {"status": "updated"}
