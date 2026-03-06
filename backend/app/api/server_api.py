"""
HostingSignal — Server Management API Router
Exposes all service managers as REST API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..core.security import get_current_user

router = APIRouter(prefix="/api/server", tags=["Server Management"])


# ─── Schemas ──────────────────────────────────────────────────────────
class WebsiteCreate(BaseModel):
    domain: str
    php_version: str = "8.2"

class RecordCreate(BaseModel):
    name: str
    type: str
    content: str
    ttl: int = 3600

class EmailCreate(BaseModel):
    email: str
    password: str
    quota_mb: int = 1024

class AliasCreate(BaseModel):
    source: str
    destination: str

class DatabaseCreate(BaseModel):
    name: str
    username: Optional[str] = None
    password: Optional[str] = None

class SSLIssue(BaseModel):
    domain: str
    email: str = "admin@hostingsignal.com"
    wildcard: bool = False

class PortAction(BaseModel):
    port: int
    protocol: str = "tcp"

class IPAction(BaseModel):
    ip: str
    reason: str = ""

class FTPCreate(BaseModel):
    username: str
    password: str
    directory: str
    quota_mb: int = 0

class BackupCreate(BaseModel):
    domain: str
    include_db: bool = True
    include_email: bool = True

class DockerExec(BaseModel):
    command: str


# ─── WEBSITE ENDPOINTS ───────────────────────────────────────────────
@router.get("/websites")
async def get_websites(user=Depends(get_current_user)):
    from ..services.webserver import list_websites
    return list_websites()


@router.post("/websites")
async def create_website(data: WebsiteCreate, user=Depends(get_current_user)):
    from ..services.webserver import create_website
    return create_website(data.domain, data.php_version)


@router.delete("/websites/{domain}")
async def delete_website(domain: str, user=Depends(get_current_user)):
    from ..services.webserver import delete_website
    return {"success": delete_website(domain)}


@router.put("/websites/{domain}/php")
async def change_php(domain: str, data: dict, user=Depends(get_current_user)):
    from ..services.webserver import change_php_version
    return {"success": change_php_version(domain, data.get("version", "8.2"))}


@router.get("/webserver/status")
async def get_webserver_status(user=Depends(get_current_user)):
    from ..services.webserver import webserver_status
    return webserver_status()


# ─── DNS ENDPOINTS ───────────────────────────────────────────────────
@router.get("/dns/zones")
async def get_zones(user=Depends(get_current_user)):
    from ..services.dns_manager import list_zones
    return list_zones()


@router.get("/dns/zones/{domain}")
async def get_zone(domain: str, user=Depends(get_current_user)):
    from ..services.dns_manager import get_zone
    zone = get_zone(domain)
    if not zone:
        raise HTTPException(404, "Zone not found")
    return zone


@router.post("/dns/zones")
async def create_zone(data: dict, user=Depends(get_current_user)):
    from ..services.dns_manager import create_zone
    return create_zone(data["domain"])


@router.post("/dns/zones/{domain}/records")
async def add_dns_record(domain: str, data: RecordCreate, user=Depends(get_current_user)):
    from ..services.dns_manager import add_record
    return add_record(domain, data.name, data.type, data.content, data.ttl)


@router.delete("/dns/zones/{domain}/records")
async def del_dns_record(domain: str, name: str, type: str, user=Depends(get_current_user)):
    from ..services.dns_manager import delete_record
    return delete_record(domain, name, type)


@router.delete("/dns/zones/{domain}")
async def del_zone(domain: str, user=Depends(get_current_user)):
    from ..services.dns_manager import delete_zone
    return delete_zone(domain)


# ─── EMAIL ENDPOINTS ─────────────────────────────────────────────────
@router.get("/email/accounts")
async def get_email_accounts(domain: Optional[str] = None, user=Depends(get_current_user)):
    from ..services.email_manager import list_accounts
    return list_accounts(domain)


@router.post("/email/accounts")
async def create_email(data: EmailCreate, user=Depends(get_current_user)):
    from ..services.email_manager import create_account
    return create_account(data.email, data.password, data.quota_mb)


@router.delete("/email/accounts/{email}")
async def delete_email(email: str, user=Depends(get_current_user)):
    from ..services.email_manager import delete_account
    return {"success": delete_account(email)}


@router.get("/email/aliases")
async def get_aliases(domain: Optional[str] = None, user=Depends(get_current_user)):
    from ..services.email_manager import list_aliases
    return list_aliases(domain)


@router.post("/email/aliases")
async def create_alias(data: AliasCreate, user=Depends(get_current_user)):
    from ..services.email_manager import add_alias
    return add_alias(data.source, data.destination)


@router.post("/email/dkim/{domain}")
async def setup_dkim(domain: str, user=Depends(get_current_user)):
    from ..services.email_manager import setup_dkim
    return setup_dkim(domain)


# ─── DATABASE ENDPOINTS ──────────────────────────────────────────────
@router.get("/databases")
async def get_databases(user=Depends(get_current_user)):
    from ..services.database_manager import list_databases
    return list_databases()


@router.post("/databases")
async def create_db(data: DatabaseCreate, user=Depends(get_current_user)):
    from ..services.database_manager import create_database
    return create_database(data.name, data.username, data.password)


@router.delete("/databases/{name}")
async def delete_db(name: str, drop_user: Optional[str] = None, user=Depends(get_current_user)):
    from ..services.database_manager import delete_database
    return {"success": delete_database(name, drop_user)}


# ─── SSL ENDPOINTS ───────────────────────────────────────────────────
@router.get("/ssl/certificates")
async def get_certs(user=Depends(get_current_user)):
    from ..services.ssl_manager import list_certificates
    return list_certificates()


@router.post("/ssl/certificates")
async def issue_cert(data: SSLIssue, user=Depends(get_current_user)):
    from ..services.ssl_manager import issue_certificate
    return issue_certificate(data.domain, data.email, data.wildcard)


@router.post("/ssl/certificates/{domain}/renew")
async def renew_cert(domain: str, user=Depends(get_current_user)):
    from ..services.ssl_manager import renew_certificate
    return renew_certificate(domain)


@router.delete("/ssl/certificates/{domain}")
async def revoke_cert(domain: str, user=Depends(get_current_user)):
    from ..services.ssl_manager import revoke_certificate
    return revoke_certificate(domain)


# ─── FIREWALL ENDPOINTS ──────────────────────────────────────────────
@router.get("/firewall/rules")
async def get_fw_rules(user=Depends(get_current_user)):
    from ..services.firewall_manager import list_rules
    return list_rules()


@router.post("/firewall/ports")
async def open_fw_port(data: PortAction, user=Depends(get_current_user)):
    from ..services.firewall_manager import open_port
    return open_port(data.port, data.protocol)


@router.delete("/firewall/ports/{port}")
async def close_fw_port(port: int, protocol: str = "tcp", user=Depends(get_current_user)):
    from ..services.firewall_manager import close_port
    return close_port(port, protocol)


@router.get("/firewall/blocked")
async def get_blocked(user=Depends(get_current_user)):
    from ..services.firewall_manager import list_blocked_ips
    return list_blocked_ips()


@router.post("/firewall/block")
async def block(data: IPAction, user=Depends(get_current_user)):
    from ..services.firewall_manager import block_ip
    return block_ip(data.ip, data.reason)


@router.delete("/firewall/block/{ip}")
async def unblock(ip: str, user=Depends(get_current_user)):
    from ..services.firewall_manager import unblock_ip
    return unblock_ip(ip)


@router.get("/firewall/status")
async def fw_status(user=Depends(get_current_user)):
    from ..services.firewall_manager import firewall_status
    return firewall_status()


# ─── FTP ENDPOINTS ───────────────────────────────────────────────────
@router.get("/ftp/accounts")
async def get_ftp(user=Depends(get_current_user)):
    from ..services.ftp_manager import list_accounts
    return list_accounts()


@router.post("/ftp/accounts")
async def create_ftp(data: FTPCreate, user=Depends(get_current_user)):
    from ..services.ftp_manager import create_account
    return create_account(data.username, data.password, data.directory, data.quota_mb)


@router.delete("/ftp/accounts/{username}")
async def delete_ftp(username: str, user=Depends(get_current_user)):
    from ..services.ftp_manager import delete_account
    return {"success": delete_account(username)}


# ─── FILE MANAGER ENDPOINTS ──────────────────────────────────────────
@router.get("/files")
async def get_files(path: str = "/", user=Depends(get_current_user)):
    from ..services.file_manager import list_files
    return list_files(path)


@router.get("/files/read")
async def read_file(path: str, user=Depends(get_current_user)):
    from ..services.file_manager import read_text_file
    content = read_text_file(path)
    if content is None:
        raise HTTPException(404, "File not found")
    return {"path": path, "content": content}


@router.post("/files/write")
async def write_file(data: dict, user=Depends(get_current_user)):
    from ..services.file_manager import write_text_file
    return {"success": write_text_file(data["path"], data["content"])}


@router.post("/files/mkdir")
async def mkdir(data: dict, user=Depends(get_current_user)):
    from ..services.file_manager import create_directory
    return {"success": create_directory(data["path"])}


@router.delete("/files")
async def delete_file(path: str, user=Depends(get_current_user)):
    from ..services.file_manager import delete_item
    return {"success": delete_item(path)}


@router.post("/files/rename")
async def rename(data: dict, user=Depends(get_current_user)):
    from ..services.file_manager import rename_item
    return {"success": rename_item(data["path"], data["new_name"])}


@router.post("/files/compress")
async def compress_files(data: dict, user=Depends(get_current_user)):
    from ..services.file_manager import compress
    return {"success": compress(data["paths"], data["output"])}


@router.post("/files/extract")
async def extract_archive(data: dict, user=Depends(get_current_user)):
    from ..services.file_manager import extract
    return {"success": extract(data["archive"], data["destination"])}


# ─── BACKUP ENDPOINTS ────────────────────────────────────────────────
@router.get("/backups")
async def get_backups(domain: Optional[str] = None, user=Depends(get_current_user)):
    from ..services.backup_manager import list_backups
    return list_backups(domain)


@router.post("/backups")
async def create_backup(data: BackupCreate, user=Depends(get_current_user)):
    from ..services.backup_manager import create_backup
    return create_backup(data.domain, data.include_db, data.include_email)


@router.post("/backups/{backup_id}/restore")
async def restore_backup(backup_id: str, domain: Optional[str] = None, user=Depends(get_current_user)):
    from ..services.backup_manager import restore_backup
    return restore_backup(backup_id, domain)


@router.delete("/backups/{backup_id}")
async def delete_backup(backup_id: str, user=Depends(get_current_user)):
    from ..services.backup_manager import delete_backup
    return {"success": delete_backup(backup_id)}


# ─── SYSTEM MONITOR ENDPOINTS ────────────────────────────────────────
@router.get("/monitor")
async def get_stats(user=Depends(get_current_user)):
    from ..services.system_monitor import get_system_stats
    return get_system_stats()


@router.get("/monitor/services")
async def get_services(user=Depends(get_current_user)):
    from ..services.system_monitor import get_service_statuses
    return get_service_statuses()


@router.get("/monitor/processes")
async def get_processes(limit: int = 20, user=Depends(get_current_user)):
    from ..services.system_monitor import get_process_list
    return get_process_list(limit)


# ─── DOCKER ENDPOINTS ────────────────────────────────────────────────
@router.get("/docker/containers")
async def get_containers(user=Depends(get_current_user)):
    from ..services.docker_manager import list_containers
    return list_containers()


@router.get("/docker/images")
async def get_images(user=Depends(get_current_user)):
    from ..services.docker_manager import list_images
    return list_images()


@router.post("/docker/containers/{cid}/start")
async def start_c(cid: str, user=Depends(get_current_user)):
    from ..services.docker_manager import start_container
    return start_container(cid)


@router.post("/docker/containers/{cid}/stop")
async def stop_c(cid: str, user=Depends(get_current_user)):
    from ..services.docker_manager import stop_container
    return stop_container(cid)


@router.post("/docker/containers/{cid}/restart")
async def restart_c(cid: str, user=Depends(get_current_user)):
    from ..services.docker_manager import restart_container
    return restart_container(cid)


@router.delete("/docker/containers/{cid}")
async def remove_c(cid: str, user=Depends(get_current_user)):
    from ..services.docker_manager import remove_container
    return remove_container(cid)


@router.get("/docker/containers/{cid}/logs")
async def container_log(cid: str, tail: int = 100, user=Depends(get_current_user)):
    from ..services.docker_manager import container_logs
    return {"logs": container_logs(cid, tail)}


@router.post("/docker/containers/{cid}/exec")
async def exec_in_container(cid: str, data: DockerExec, user=Depends(get_current_user)):
    from ..services.docker_manager import exec_command
    return exec_command(cid, data.command)


# ─── SERVER INFO ─────────────────────────────────────────────────────
@router.get("/info")
async def server_info(user=Depends(get_current_user)):
    from ..services.server_utils import get_os_info, get_server_ip, get_hostname
    return {
        "os": get_os_info(),
        "ip": get_server_ip(),
        "hostname": get_hostname(),
        "panel_version": "1.0.0",
    }
