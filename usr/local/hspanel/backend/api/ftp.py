"""FTP account endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from .deps import require_api_token
from ..service_manager import FTPManager

router = APIRouter(prefix="/api/ftp", tags=["ftp"], dependencies=[Depends(require_api_token)])

ftp_mgr = FTPManager()


class FTPCreateRequest(BaseModel):
    username: str
    password: str
    home: str
    system_user: str = "hspanel"


class FTPPasswordRequest(BaseModel):
    username: str
    new_password: str


@router.post("/create")
def create_ftp_user(req: FTPCreateRequest) -> dict:
    res = ftp_mgr.create_ftp_user(req.username, req.password, req.home, req.system_user)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.delete("/{username}")
def delete_ftp_user(username: str) -> dict:
    res = ftp_mgr.delete_ftp_user(username)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.post("/password")
def change_password(req: FTPPasswordRequest) -> dict:
    res = ftp_mgr.change_ftp_password(req.username, req.new_password)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res.to_dict()


@router.get("/list")
def list_ftp_users() -> dict:
    return {"success": True, "data": ftp_mgr.list_ftp_users()}
