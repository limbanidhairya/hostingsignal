"""
HostingSignal Panel — Website Management API
Create, delete, list websites, subdomains, SSL management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import os

from app.core.security import get_current_user
from app.services.webserver import WebServerManager
from app.services.ssl_manager import SSLManager

router = APIRouter(prefix="/api/websites", tags=["Websites"])

ws_manager = WebServerManager()
ssl_mgr = SSLManager()


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreateWebsiteRequest(BaseModel):
    domain: str
    admin_email: Optional[str] = None
    php_version: str = "8.2"
    enable_ssl: bool = True
    document_root: Optional[str] = None


class CreateSubdomainRequest(BaseModel):
    parent_domain: str
    subdomain: str
    document_root: Optional[str] = None


class SSLRequest(BaseModel):
    domain: str
    provider: str = "letsencrypt"  # letsencrypt | custom
    certificate: Optional[str] = None
    private_key: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/")
async def list_websites(current_user: dict = Depends(get_current_user)):
    """List all hosted websites."""
    try:
        sites = ws_manager.list_sites()
        return {"websites": sites, "total": len(sites)}
    except Exception as e:
        return {"websites": [], "total": 0, "warning": str(e)}


@router.post("/create")
async def create_website(
    body: CreateWebsiteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new website with vhost configuration."""
    try:
        doc_root = body.document_root or f"/home/{body.domain}/public_html"

        result = ws_manager.create_site(
            domain=body.domain,
            document_root=doc_root,
            php_version=body.php_version,
        )

        # Create directory structure
        os.makedirs(doc_root, exist_ok=True)
        os.makedirs(f"/home/{body.domain}/logs", exist_ok=True)
        os.makedirs(f"/home/{body.domain}/tmp", exist_ok=True)

        # Create default index page
        index_path = os.path.join(doc_root, "index.html")
        if not os.path.exists(index_path):
            with open(index_path, "w") as f:
                f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to {body.domain}</title>
    <style>
        body {{ font-family: 'Inter', system-ui, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #0f172a; color: #e2e8f0; }}
        .container {{ text-align: center; padding: 2rem; }}
        h1 {{ font-size: 2.5rem; background: linear-gradient(135deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        p {{ color: #94a3b8; font-size: 1.1rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to {body.domain}</h1>
        <p>This website is powered by HostingSignal Panel</p>
    </div>
</body>
</html>""")

        # Auto SSL if requested
        ssl_result = None
        if body.enable_ssl:
            try:
                ssl_result = ssl_mgr.issue_ssl(body.domain)
            except Exception:
                ssl_result = {"status": "pending", "message": "SSL will be configured after DNS propagation"}

        return {
            "status": "success",
            "domain": body.domain,
            "document_root": doc_root,
            "php_version": body.php_version,
            "ssl": ssl_result,
            "message": f"Website {body.domain} created successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{domain}")
async def delete_website(
    domain: str,
    remove_files: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Delete a website and optionally remove files."""
    try:
        result = ws_manager.delete_site(domain)

        if remove_files:
            import shutil
            site_dir = f"/home/{domain}"
            if os.path.exists(site_dir):
                shutil.rmtree(site_dir)

        return {
            "status": "success",
            "domain": domain,
            "files_removed": remove_files,
            "message": f"Website {domain} deleted.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{domain}")
async def get_website_details(
    domain: str,
    current_user: dict = Depends(get_current_user),
):
    """Get details of a specific website."""
    try:
        sites = ws_manager.list_sites()
        site = next((s for s in sites if s.get("domain") == domain), None)
        if not site:
            raise HTTPException(status_code=404, detail=f"Website {domain} not found")

        doc_root = f"/home/{domain}/public_html"
        disk_usage = 0
        if os.path.exists(doc_root):
            for dirpath, dirnames, filenames in os.walk(doc_root):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    disk_usage += os.path.getsize(fp)

        return {
            **site,
            "disk_usage_bytes": disk_usage,
            "disk_usage_mb": round(disk_usage / (1024 * 1024), 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subdomain")
async def create_subdomain(
    body: CreateSubdomainRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a subdomain under a parent domain."""
    full_domain = f"{body.subdomain}.{body.parent_domain}"
    doc_root = body.document_root or f"/home/{body.parent_domain}/subdomains/{body.subdomain}"

    try:
        os.makedirs(doc_root, exist_ok=True)
        result = ws_manager.create_site(
            domain=full_domain,
            document_root=doc_root,
        )
        return {
            "status": "success",
            "subdomain": full_domain,
            "document_root": doc_root,
            "message": f"Subdomain {full_domain} created.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ssl")
async def manage_ssl(
    body: SSLRequest,
    current_user: dict = Depends(get_current_user),
):
    """Issue or install SSL certificate for a domain."""
    try:
        if body.provider == "letsencrypt":
            result = ssl_mgr.issue_ssl(body.domain)
        elif body.provider == "custom" and body.certificate and body.private_key:
            result = ssl_mgr.install_custom_ssl(
                body.domain, body.certificate, body.private_key
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid SSL request")

        return {"status": "success", "domain": body.domain, "ssl": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
