"""
Updates Router — automatic GitHub release update detection and seamless self-updating.
"""
import sys
import os
import re
import json
import urllib.request
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.config import settings

router = APIRouter(prefix="/updates", tags=["Updates"])

GITHUB_REPO = "Ajay176854/Billing_Software"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_version(v_str: str) -> tuple:
    """Extract numeric version tuple from string (e.g. 'v1.1.0' -> (1, 1, 0))."""
    if not v_str:
        return (0, 0, 0)
    numbers = [int(n) for n in re.findall(r"\d+", v_str)]
    return tuple(numbers) if numbers else (0, 0, 0)


@router.get("/check")
def check_for_updates():
    """
    Check GitHub Releases for a newer version of the software.
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "User-Agent": "MoiraLuxe-POS",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        latest_ver_tuple = parse_version(latest_tag)
        current_ver_tuple = parse_version(settings.APP_VERSION)

        # Find .exe asset
        exe_asset = None
        for asset in data.get("assets", []):
            if asset.get("name", "").lower().endswith(".exe"):
                exe_asset = asset
                break

        update_available = latest_ver_tuple > current_ver_tuple and exe_asset is not None

        return {
            "update_available": update_available,
            "current_version": settings.APP_VERSION,
            "latest_version": latest_tag.lstrip("v"),
            "release_name": data.get("name") or latest_tag,
            "release_notes": data.get("body") or "",
            "download_url": exe_asset.get("browser_download_url") if exe_asset else None,
            "file_size_mb": round((exe_asset.get("size", 0) / (1024 * 1024)), 1) if exe_asset else 0,
            "published_at": data.get("published_at"),
        }
    except Exception as e:
        # Fallback silently if offline or rate limited
        return {
            "update_available": False,
            "current_version": settings.APP_VERSION,
            "error": str(e),
        }


# Global in-memory progress tracker for live UI feedback
update_progress = {
    "state": "idle",       # "idle" | "downloading" | "applying" | "error"
    "percent": 0,
    "downloaded_mb": 0.0,
    "total_mb": 0.0,
    "message": ""
}


@router.get("/progress")
def get_update_progress():
    """Return the current progress of the in-flight update."""
    return update_progress


def _perform_update(download_url: str):
    """Download the new executable using high-speed 1MB buffers and restart."""
    global update_progress
    try:
        update_progress["state"] = "downloading"
        update_progress["percent"] = 0
        update_progress["message"] = "Connecting to download server..."

        if getattr(sys, "frozen", False):
            target_exe = Path(sys.executable).resolve()
            app_dir = target_exe.parent
        else:
            app_dir = Path(__file__).resolve().parent.parent.parent / "dist"
            app_dir.mkdir(parents=True, exist_ok=True)
            target_exe = app_dir / "MoiraLuxe.exe"

        temp_exe = app_dir / "MoiraLuxe_update_temp.exe"

        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "MoiraLuxe-POS"}
        )

        with urllib.request.urlopen(req, timeout=120) as response, open(temp_exe, "wb") as out_file:
            total_size = int(response.headers.get("content-length", 0))
            total_mb = round(total_size / (1024 * 1024), 1) if total_size else 78.4
            update_progress["total_mb"] = total_mb
            
            # High-performance 1 MB buffer chunk for 3x faster transfer
            CHUNK_SIZE = 1024 * 1024
            downloaded = 0

            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                dl_mb = round(downloaded / (1024 * 1024), 1)
                pct = int((downloaded / total_size) * 100) if total_size else min(95, int(dl_mb))
                
                update_progress["percent"] = pct
                update_progress["downloaded_mb"] = dl_mb
                update_progress["message"] = f"Downloading: {pct}% ({dl_mb} MB / {total_mb} MB)"

        update_progress["state"] = "applying"
        update_progress["percent"] = 100
        update_progress["message"] = "Download complete. Restarting Moira Luxe..."

        current_pid = os.getpid()

        # Generate the self-replacing updater batch script
        batch_script = app_dir / "apply_update.bat"
        with open(batch_script, "w", encoding="utf-8") as f:
            f.write(f"""@echo off
timeout /t 1 /nobreak > nul
:waitloop
taskkill /F /PID {current_pid} > nul 2>&1
move /Y "{temp_exe}" "{target_exe}" > nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak > nul
    goto waitloop
)
start "" "{target_exe}"
del "%~f0"
""")

        # Execute updater batch detached and shut down
        subprocess.Popen(
            ["cmd.exe", "/c", str(batch_script)],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            close_fds=True,
        )

        # Gracefully exit python process
        os._exit(0)

    except Exception as e:
        print(f"Update error: {e}")
        update_progress["state"] = "error"
        update_progress["message"] = str(e)


@router.post("/apply")
def apply_update(background_tasks: BackgroundTasks):
    """
    Download the latest update from GitHub and restart the application.
    """
    info = check_for_updates()
    download_url = info.get("download_url")

    if not download_url:
        raise HTTPException(status_code=400, detail="No executable download URL found for this release.")

    # Schedule the download and swap in the background so the HTTP response finishes cleanly
    background_tasks.add_task(_perform_update, download_url)
    return {"success": True, "message": "Update process initiated. The app will restart shortly."}

