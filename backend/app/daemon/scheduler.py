"""
HostingSignal Panel — Scheduler Daemon
Cron-like scheduled tasks: backup jobs, SSL renewal, cleanup.
"""
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Callable


class ScheduledTask:
    """A single scheduled task."""

    def __init__(self, name: str, cron: str, handler: Callable, enabled: bool = True):
        self.name = name
        self.cron = cron
        self.handler = handler
        self.enabled = enabled
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.last_error = None


class Scheduler:
    """Simple async task scheduler."""

    def __init__(self):
        self.tasks: List[ScheduledTask] = []
        self._running = False

    def register(self, name: str, cron: str, handler: Callable, enabled: bool = True):
        """Register a scheduled task."""
        task = ScheduledTask(name, cron, handler, enabled)
        self.tasks.append(task)
        print(f"📅 Scheduled: {name} [{cron}]")

    async def start(self):
        """Start the scheduler loop."""
        self._running = True
        print("📅 Scheduler started")

        # Register default tasks
        self._register_defaults()

        while self._running:
            now = datetime.now(timezone.utc)
            for task in self.tasks:
                if not task.enabled:
                    continue
                if self._should_run(task, now):
                    asyncio.create_task(self._run_task(task))
            await asyncio.sleep(60)  # Check every minute

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        print("📅 Scheduler stopped")

    def _register_defaults(self):
        """Register default system tasks."""
        self.register("ssl_auto_renew", "0 3 * * *", self._ssl_auto_renew)
        self.register("cleanup_temp", "0 4 * * *", self._cleanup_temp)
        self.register("log_rotation", "0 0 * * 0", self._log_rotation)

    def _should_run(self, task: ScheduledTask, now: datetime) -> bool:
        """Simple cron matching — checks if task should run this minute."""
        if task.last_run and (now - task.last_run).total_seconds() < 60:
            return False

        parts = task.cron.split()
        if len(parts) != 5:
            return False

        minute, hour, day, month, weekday = parts

        if minute != "*" and int(minute) != now.minute:
            return False
        if hour != "*" and int(hour) != now.hour:
            return False
        if day != "*" and int(day) != now.day:
            return False
        if month != "*" and int(month) != now.month:
            return False
        if weekday != "*" and int(weekday) != now.weekday():
            return False

        return True

    async def _run_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        try:
            task.last_run = datetime.now(timezone.utc)
            task.run_count += 1
            print(f"📅 Running: {task.name}")

            if asyncio.iscoroutinefunction(task.handler):
                await task.handler()
            else:
                task.handler()

            task.last_error = None
        except Exception as e:
            task.last_error = str(e)
            print(f"❌ Task {task.name} failed: {e}")

    # ── Default Task Handlers ────────────────────────────────────────────────

    async def _ssl_auto_renew(self):
        """Auto-renew SSL certificates nearing expiry."""
        import subprocess
        try:
            subprocess.run(
                ["certbot", "renew", "--quiet", "--no-self-upgrade"],
                capture_output=True, timeout=300,
            )
            print("✅ SSL auto-renewal completed")
        except Exception as e:
            print(f"⚠️  SSL renewal failed: {e}")

    async def _cleanup_temp(self):
        """Clean up temporary files."""
        import shutil
        import os
        temp_dirs = ["/tmp/hostingsignal", "/var/log/hostingsignal/tmp"]
        for d in temp_dirs:
            if os.path.exists(d):
                for item in os.listdir(d):
                    path = os.path.join(d, item)
                    try:
                        if os.path.isfile(path):
                            os.unlink(path)
                        elif os.path.isdir(path):
                            shutil.rmtree(path)
                    except Exception:
                        pass

    async def _log_rotation(self):
        """Rotate log files."""
        import subprocess
        try:
            subprocess.run(["logrotate", "-f", "/etc/logrotate.d/hostingsignal"], capture_output=True, timeout=60)
        except Exception:
            pass


# Singleton
scheduler = Scheduler()
