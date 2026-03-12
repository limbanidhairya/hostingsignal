"""Database and database-user endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token
from ..service_manager import DatabaseManager

router = APIRouter(prefix="/api/mysql", tags=["mysql"], dependencies=[Depends(require_api_token)])

db = DatabaseManager()


class DatabaseCreateRequest(BaseModel):
    name: str


class DatabaseUserCreateRequest(BaseModel):
    username: str
    password: str | None = None


class GrantRequest(BaseModel):
    database: str
    username: str
    privileges: str = "ALL PRIVILEGES"


@router.post("/database/create")
def create_database(req: DatabaseCreateRequest) -> dict:
    res = db.create_database(req.name)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.delete("/database/{name}")
def delete_database(name: str) -> dict:
    res = db.delete_database(name)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.get("/database/list")
def list_databases() -> dict:
    return {"success": True, "data": db.list_databases()}


@router.post("/user/create")
def create_user(req: DatabaseUserCreateRequest) -> dict:
    res = db.create_db_user(req.username, req.password)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.delete("/user/{username}")
def delete_user(username: str) -> dict:
    res = db.delete_db_user(username)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/grant")
def grant(req: GrantRequest) -> dict:
    res = db.grant_privileges(req.database, req.username, req.privileges)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()
