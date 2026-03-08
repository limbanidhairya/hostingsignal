"""
AI Monitoring Microservice — Alert System
Dispatches alerts via webhooks, email, and panel notifications.
"""
import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

ALERT_CONFIG_PATH = "/usr/local/hostingsignal/monitoring/alert_config.json"
DEFAULT_CONFIG = {
    "email": {
        "enabled": False,
        "smtp_host": "localhost",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_pass": "",
        "from_addr": "alerts@hostingsignal.com",
        "to_addrs": [],
        "use_tls": True,
    },
    "webhook": {
        "enabled": False,
        "urls": [],
        "secret": "",
    },
    "panel": {
        "enabled": True,
        "api_url": "http://localhost:8000/api/notifications",
    },
    "severity_filter": ["critical", "warning"],
    "cooldown_minutes": 5,
}


class AlertDispatcher:
    """Dispatches monitoring alerts to configured channels."""

    def __init__(self):
        self.config = self._load_config()
        self.sent_alerts: dict = {}

    def _load_config(self) -> dict:
        if os.path.exists(ALERT_CONFIG_PATH):
            with open(ALERT_CONFIG_PATH) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        return DEFAULT_CONFIG

    def save_config(self, config: dict):
        self.config = {**DEFAULT_CONFIG, **config}
        os.makedirs(os.path.dirname(ALERT_CONFIG_PATH), exist_ok=True)
        with open(ALERT_CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=2)

    async def dispatch(self, alert: dict):
        """Send alert to all configured channels."""
        severity = alert.get("severity", "info")
        if severity not in self.config.get("severity_filter", ["critical"]):
            return

        # Cooldown check
        alert_type = alert.get("type", "")
        now = datetime.utcnow()
        if alert_type in self.sent_alerts:
            last_sent = self.sent_alerts[alert_type]
            cooldown = self.config.get("cooldown_minutes", 5) * 60
            if (now - last_sent).total_seconds() < cooldown:
                return

        self.sent_alerts[alert_type] = now

        if self.config["email"]["enabled"]:
            await self._send_email(alert)

        if self.config["webhook"]["enabled"]:
            await self._send_webhook(alert)

        if self.config["panel"]["enabled"]:
            await self._send_panel_notification(alert)

    async def _send_email(self, alert: dict):
        """Send alert via email."""
        cfg = self.config["email"]
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert['severity'].upper()}] HostingSignal Alert: {alert['type']}"
            msg["From"] = cfg["from_addr"]
            msg["To"] = ", ".join(cfg["to_addrs"])

            text = f"""
HostingSignal Panel Alert
{'=' * 40}
Severity: {alert['severity'].upper()}
Type: {alert['type']}
Message: {alert['message']}
Time: {alert.get('timestamp', datetime.utcnow().isoformat())}

Data: {json.dumps(alert.get('data', {}), indent=2)}
"""
            html = f"""
<div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: {'#ef4444' if alert['severity'] == 'critical' else '#f59e0b'}; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
        <h2 style="margin: 0;">⚠️ {alert['severity'].upper()} Alert</h2>
    </div>
    <div style="background: #1a1a2e; color: #e0e0e0; padding: 24px; border-radius: 0 0 8px 8px;">
        <p style="font-size: 16px; font-weight: 600;">{alert['message']}</p>
        <p>Type: <code>{alert['type']}</code></p>
        <p>Time: {alert.get('timestamp', '')}</p>
        <pre style="background: #0d0d1a; padding: 12px; border-radius: 6px; overflow-x: auto;">{json.dumps(alert.get('data', {}), indent=2)}</pre>
        <hr style="border-color: #333;">
        <p style="color: #888; font-size: 12px;">HostingSignal Panel Monitoring</p>
    </div>
</div>
"""
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"])
            if cfg.get("use_tls"):
                server.starttls()
            if cfg["smtp_user"]:
                server.login(cfg["smtp_user"], cfg["smtp_pass"])
            server.sendmail(cfg["from_addr"], cfg["to_addrs"], msg.as_string())
            server.quit()
            logger.info(f"Alert email sent: {alert['type']}")
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")

    async def _send_webhook(self, alert: dict):
        """Send alert to configured webhook URLs."""
        cfg = self.config["webhook"]
        payload = {
            "source": "hostingsignal-monitoring",
            "alert": alert,
            "timestamp": datetime.utcnow().isoformat(),
        }

        async with httpx.AsyncClient(timeout=10) as client:
            for url in cfg["urls"]:
                try:
                    headers = {"Content-Type": "application/json"}
                    if cfg.get("secret"):
                        import hmac
                        import hashlib
                        body = json.dumps(payload)
                        sig = hmac.new(cfg["secret"].encode(), body.encode(), hashlib.sha256).hexdigest()
                        headers["X-Signature"] = sig

                    await client.post(url, json=payload, headers=headers)
                    logger.info(f"Alert webhook sent to {url}")
                except Exception as e:
                    logger.error(f"Webhook failed ({url}): {e}")

    async def _send_panel_notification(self, alert: dict):
        """Send alert as a panel notification via internal API."""
        cfg = self.config["panel"]
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(cfg["api_url"], json={
                    "type": "monitoring_alert",
                    "severity": alert["severity"],
                    "title": f"[{alert['severity'].upper()}] {alert['type']}",
                    "message": alert["message"],
                    "data": alert.get("data", {}),
                })
        except Exception as e:
            logger.debug(f"Panel notification failed: {e}")

    def get_config(self) -> dict:
        """Return config with sensitive fields masked."""
        safe = json.loads(json.dumps(self.config))
        if safe.get("email", {}).get("smtp_pass"):
            safe["email"]["smtp_pass"] = "********"
        if safe.get("webhook", {}).get("secret"):
            safe["webhook"]["secret"] = "********"
        return safe


# Singleton
alert_dispatcher = AlertDispatcher()
