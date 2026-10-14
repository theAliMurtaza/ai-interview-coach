"""Authenticated downloads for owner-scoped uploads and reports."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.deps import get_current_active_user
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.storage.s3_client import generate_presigned_url, local_path, validate_key

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{key:path}")
async def download_file(key: str, user: User = Depends(get_current_active_user)):
    validate_key(key)
    parts = key.split("/")
    if len(parts) != 3 or parts[0] not in {"resumes", "reports"} or parts[1] != str(user.id):
        raise NotFoundError("File not found")
    if settings.STORAGE_BACKEND == "s3":
        return RedirectResponse(await run_in_threadpool(generate_presigned_url, key))
    path = local_path(key)
    if not path.is_file():
        raise NotFoundError("File not found")
    return FileResponse(path, filename=path.name, headers={"Cache-Control": "private, no-store"})
