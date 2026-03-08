"""
HostingSignal Panel — Database Management API
MySQL/MariaDB database and user CRUD, phpMyAdmin integration.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_current_user
from app.services.database_manager import DatabaseManager

router = APIRouter(prefix="/api/databases", tags=["Databases"])

db_mgr = DatabaseManager()


class CreateDatabaseRequest(BaseModel):
    name: str
    charset: str = "utf8mb4"
    collation: str = "utf8mb4_unicode_ci"


class CreateDBUserRequest(BaseModel):
    username: str
    password: str
    database: str
    host: str = "localhost"
    privileges: str = "ALL PRIVILEGES"


class UpdateDBUserRequest(BaseModel):
    username: str
    host: str = "localhost"
    new_password: Optional[str] = None
    privileges: Optional[str] = None
    database: Optional[str] = None


@router.get("/")
async def list_databases(current_user: dict = Depends(get_current_user)):
    """List all MySQL databases."""
    try:
        databases = db_mgr.list_databases()
        return {"databases": databases, "total": len(databases)}
    except Exception as e:
        return {"databases": [], "error": str(e)}


@router.post("/create")
async def create_database(
    body: CreateDatabaseRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new MySQL database."""
    try:
        result = db_mgr.create_database(body.name, body.charset, body.collation)
        return {
            "status": "success",
            "database": body.name,
            "message": f"Database '{body.name}' created.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}")
async def delete_database(
    name: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a MySQL database."""
    try:
        result = db_mgr.delete_database(name)
        return {"status": "success", "message": f"Database '{name}' deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def list_db_users(current_user: dict = Depends(get_current_user)):
    """List all MySQL users."""
    try:
        users = db_mgr.list_users()
        return {"users": users, "total": len(users)}
    except Exception as e:
        return {"users": [], "error": str(e)}


@router.post("/users/create")
async def create_db_user(
    body: CreateDBUserRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new MySQL user with database privileges."""
    try:
        result = db_mgr.create_user(
            body.username, body.password, body.database,
            body.host, body.privileges,
        )
        return {
            "status": "success",
            "username": body.username,
            "database": body.database,
            "message": f"User '{body.username}' created with {body.privileges} on '{body.database}'.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{username}")
async def delete_db_user(
    username: str,
    host: str = "localhost",
    current_user: dict = Depends(get_current_user),
):
    """Delete a MySQL user."""
    try:
        result = db_mgr.delete_user(username, host)
        return {"status": "success", "message": f"User '{username}'@'{host}' deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phpmyadmin")
async def phpmyadmin_info(current_user: dict = Depends(get_current_user)):
    """Get phpMyAdmin access URL and status."""
    import os
    pma_installed = os.path.exists("/usr/share/phpmyadmin") or os.path.exists("/var/www/phpmyadmin")
    return {
        "installed": pma_installed,
        "url": "/phpmyadmin" if pma_installed else None,
        "message": "phpMyAdmin is available" if pma_installed else "phpMyAdmin is not installed",
    }
