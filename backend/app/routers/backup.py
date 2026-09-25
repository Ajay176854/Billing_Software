"""
Backup router — database backup and restore (Admin only).
"""
import shutil
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth import require_role
from app.config import settings

router = APIRouter(prefix="/backup", tags=["Backup"])

# Derive DB file path from the SQLite URL
DB_PATH = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
BACKUP_DIR = DB_PATH.parent / "backups"


@router.post("/create")
def create_backup(current_user=Depends(require_role("admin"))):
    """Create a backup of the SQLite database."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"billing_backup_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_filename

    shutil.copy2(str(DB_PATH), str(backup_path))

    return {
        "message": "Backup created successfully",
        "filename": backup_filename,
        "path": str(backup_path),
        "size_mb": round(backup_path.stat().st_size / (1024 * 1024), 2),
    }


@router.get("/list")
def list_backups(current_user=Depends(require_role("admin"))):
    """List available backups."""
    if not BACKUP_DIR.exists():
        return {"backups": []}

    backups = []
    for f in sorted(BACKUP_DIR.glob("*.db"), reverse=True):
        backups.append({
            "filename": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            "created": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
        })

    return {"backups": backups}


@router.get("/download/{filename}")
def download_backup(filename: str, current_user=Depends(require_role("admin"))):
    """Download a backup file."""
    backup_path = BACKUP_DIR / filename
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(str(backup_path), filename=filename)
