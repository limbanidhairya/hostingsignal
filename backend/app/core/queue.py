"""
HostingSignal Panel — RabbitMQ Task Queue Client
Connection and task publishing for async job processing.
"""
import json
from typing import Optional, Callable
from datetime import datetime, timezone

from config import settings

# Optional import — RabbitMQ may not be available in dev mode
try:
    import pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False


class TaskQueue:
    """RabbitMQ task queue for async job processing."""

    QUEUE_BACKUP = "hostingsignal.backups"
    QUEUE_SSL = "hostingsignal.ssl"
    QUEUE_EMAIL = "hostingsignal.email"
    QUEUE_GENERAL = "hostingsignal.general"

    def __init__(self):
        self._connection = None
        self._channel = None

    def connect(self):
        """Create RabbitMQ connection."""
        if not RABBITMQ_AVAILABLE:
            print("⚠️  RabbitMQ not available — task queue disabled")
            return
        try:
            rabbitmq_url = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
            params = pika.URLParameters(rabbitmq_url)
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()

            # Declare queues
            for queue in [self.QUEUE_BACKUP, self.QUEUE_SSL, self.QUEUE_EMAIL, self.QUEUE_GENERAL]:
                self._channel.queue_declare(queue=queue, durable=True)

            print("✅ RabbitMQ connected")
        except Exception as e:
            print(f"⚠️  RabbitMQ connection failed: {e}")
            self._connection = None
            self._channel = None

    def publish_task(self, queue: str, task_name: str, payload: dict) -> bool:
        """Publish a task to a queue."""
        if not self._channel:
            print(f"⚠️  Cannot publish task '{task_name}' — MQ not connected")
            return False

        try:
            message = {
                "task": task_name,
                "payload": payload,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
            self._channel.basic_publish(
                exchange="",
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type="application/json",
                ),
            )
            return True
        except Exception as e:
            print(f"❌ Failed to publish task: {e}")
            return False

    def close(self):
        """Close RabbitMQ connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass


# Singleton instance
task_queue = TaskQueue()
