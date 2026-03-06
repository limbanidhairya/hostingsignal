"""
HostingSignal — Docker Manager
Container and image management.
"""
from .server_utils import run_cmd, DEV_MODE, logger
import json

DEMO_CONTAINERS = [
    {"id": "abc123", "name": "wordpress_site1", "image": "wordpress:latest", "status": "running", "ports": "0.0.0.0:8080->80/tcp", "created": "2 days ago"},
    {"id": "def456", "name": "redis_cache", "image": "redis:7-alpine", "status": "running", "ports": "127.0.0.1:6379->6379/tcp", "created": "5 days ago"},
    {"id": "ghi789", "name": "phpmyadmin", "image": "phpmyadmin:latest", "status": "exited", "ports": "", "created": "1 week ago"},
]

DEMO_IMAGES = [
    {"id": "img001", "repository": "wordpress", "tag": "latest", "size": "615MB", "created": "3 days ago"},
    {"id": "img002", "repository": "redis", "tag": "7-alpine", "size": "30MB", "created": "1 week ago"},
    {"id": "img003", "repository": "phpmyadmin", "tag": "latest", "size": "510MB", "created": "2 weeks ago"},
]


def _parse_docker_json(output: str) -> list[dict]:
    try:
        return json.loads(f"[{output.strip().replace(chr(10), ',')}]")
    except json.JSONDecodeError:
        return []


def list_containers(all_containers: bool = True) -> list[dict]:
    if DEV_MODE:
        return DEMO_CONTAINERS
    flag = "-a" if all_containers else ""
    result = run_cmd(f'docker ps {flag} --format "{{{{json .}}}}"')
    if not result.success:
        return []
    containers = _parse_docker_json(result.stdout)
    return [{"id": c.get("ID", ""), "name": c.get("Names", ""), "image": c.get("Image", ""),
             "status": c.get("Status", ""), "ports": c.get("Ports", ""), "created": c.get("CreatedAt", "")}
            for c in containers]


def list_images() -> list[dict]:
    if DEV_MODE:
        return DEMO_IMAGES
    result = run_cmd('docker images --format "{{json .}}"')
    if not result.success:
        return []
    images = _parse_docker_json(result.stdout)
    return [{"id": i.get("ID", ""), "repository": i.get("Repository", ""), "tag": i.get("Tag", ""),
             "size": i.get("Size", ""), "created": i.get("CreatedAt", "")}
            for i in images]


def start_container(container_id: str) -> dict:
    result = run_cmd(f"docker start {container_id}")
    return {"id": container_id, "status": "started" if result.success or DEV_MODE else "failed"}


def stop_container(container_id: str) -> dict:
    result = run_cmd(f"docker stop {container_id}")
    return {"id": container_id, "status": "stopped" if result.success or DEV_MODE else "failed"}


def restart_container(container_id: str) -> dict:
    result = run_cmd(f"docker restart {container_id}")
    return {"id": container_id, "status": "restarted" if result.success or DEV_MODE else "failed"}


def remove_container(container_id: str, force: bool = False) -> dict:
    flag = "-f" if force else ""
    result = run_cmd(f"docker rm {flag} {container_id}")
    return {"id": container_id, "status": "removed" if result.success or DEV_MODE else "failed"}


def container_logs(container_id: str, tail: int = 100) -> str:
    if DEV_MODE:
        return f"[dev-mode] Last {tail} log lines for container {container_id}\n[2026-02-28 10:00:00] Server started\n[2026-02-28 10:00:01] Listening on port 80"
    result = run_cmd(f"docker logs --tail {tail} {container_id}")
    return result.stdout if result.success else result.stderr


def exec_command(container_id: str, command: str) -> dict:
    """Execute a command inside a running container."""
    result = run_cmd(f"docker exec {container_id} {command}", timeout=30)
    return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}


def pull_image(image: str) -> dict:
    result = run_cmd(f"docker pull {image}", timeout=300)
    return {"image": image, "status": "pulled" if result.success or DEV_MODE else "failed"}


def remove_image(image_id: str) -> dict:
    result = run_cmd(f"docker rmi {image_id}")
    return {"id": image_id, "status": "removed" if result.success or DEV_MODE else "failed"}
