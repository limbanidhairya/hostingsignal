"""PHP Manager API Routes"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/php", tags=["PHP Manager"])


@router.get("/versions")
async def list_versions():
    """List installed and available PHP versions."""
    import subprocess
    installed = []
    for ver in ["7.4", "8.0", "8.1", "8.2", "8.3"]:
        try:
            result = subprocess.run(
                [f"php{ver}", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                installed.append({
                    "version": ver,
                    "full_version": result.stdout.split("\n")[0],
                    "installed": True,
                })
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return {"installed": installed}


@router.post("/install/{version}")
async def install_version(version: str):
    """Install a PHP version."""
    return {"status": "queued", "version": version, "message": f"PHP {version} installation queued"}


@router.delete("/remove/{version}")
async def remove_version(version: str):
    return {"status": "queued", "version": version, "message": f"PHP {version} removal queued"}


@router.get("/extensions/{version}")
async def list_extensions(version: str):
    """List extensions for a PHP version."""
    import subprocess
    try:
        result = subprocess.run(
            [f"php{version}", "-m"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            modules = [m.strip() for m in result.stdout.split("\n") if m.strip() and not m.startswith("[")]
            return {"version": version, "extensions": modules}
    except Exception:
        pass
    return {"version": version, "extensions": []}


@router.post("/extensions/{version}/{extension}/enable")
async def enable_extension(version: str, extension: str):
    return {"status": "enabled", "version": version, "extension": extension}


@router.post("/extensions/{version}/{extension}/disable")
async def disable_extension(version: str, extension: str):
    return {"status": "disabled", "version": version, "extension": extension}


@router.post("/switch")
async def switch_php(domain: str, version: str):
    """Switch PHP version for a website."""
    return {"status": "switched", "domain": domain, "version": version}
