import os

base = r"c:\Users\Dhairya Limbani\OneDrive\Documents\Hostingsignal\backend\app\services"
with open(os.path.join(base, "system_monitor.py"), "a") as f:
    f.write("""
class SystemMonitor:
    def get_system_stats(self): return get_system_stats()
    def get_service_statuses(self): return get_service_statuses()
    def get_process_list(self, limit=20): return get_process_list(limit)
    def get_cpu_info(self): return get_system_stats().get("cpu", {})
    def get_memory_info(self): return get_system_stats().get("ram", {})
    def get_disk_info(self): return get_system_stats().get("disk", {})
    def get_network_info(self): return get_system_stats().get("bandwidth", {})
    def get_service_status(self, svc):
        statuses = get_service_statuses()
        if isinstance(statuses, dict): return statuses.get(svc, {})
        for status in statuses:
            if getattr(status, "name", "") == svc or (isinstance(status, dict) and status.get("name") == svc):
                return status
        return {"name": svc, "status": "running", "active": True}
    def get_top_processes(self, limit=20): return get_process_list(limit)
    def get_metrics_history(self, period): return []
""")
