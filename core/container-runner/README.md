# Container Runner

Docker/Podman lifecycle engine for HS-Panel.

## Capabilities
- Runtime detection (`docker` preferred, fallback `podman`).
- Status checks (`info` probe).
- List containers (`running-only` or all).
- Run/start/stop/remove container operations.
- Tail logs for existing containers.

## CLI Examples
```bash
python3 core/container-runner/container_runner.py status
python3 core/container-runner/container_runner.py list
python3 core/container-runner/container_runner.py run nginx:alpine --name hs-nginx --port 8081:80
python3 core/container-runner/container_runner.py logs hs-nginx --tail 50
```

## API Wiring
Mounted under developer API:
- `GET /api/containers/status`
- `GET /api/containers/list`
- `POST /api/containers/run`
- `POST /api/containers/start`
- `POST /api/containers/stop`
- `POST /api/containers/remove`
- `POST /api/containers/logs`

All endpoints require admin JWT auth.
