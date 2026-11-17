"""
WhatsApp Baileys Service Process Manager.
Ensures local Node.js engine is running on port 3001.
"""
import sys
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

_service_process = None
_launch_lock = threading.Lock()


def is_service_listening(host: str = "127.0.0.1", port: int = 3001) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def find_node_binary(whatsapp_dir: Path = None) -> str:
    # 0. Check bundled portable node.exe in whatsapp_service
    if whatsapp_dir and (whatsapp_dir / "node.exe").is_file():
        return str(whatsapp_dir / "node.exe")

    # Also check next to executable or in sys._MEIPASS
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        p_node = Path(meipass) / "whatsapp_service" / "node.exe"
        if p_node.is_file():
            return str(p_node)

    exe_dir = Path(sys.executable).parent
    if (exe_dir / "node.exe").is_file():
        return str(exe_dir / "node.exe")
    if (exe_dir / "whatsapp_service" / "node.exe").is_file():
        return str(exe_dir / "whatsapp_service" / "node.exe")

    # 1. PATH search
    bin_path = shutil.which("node") or shutil.which("node.exe")
    if bin_path:
        return bin_path

    # 2. Well-known Windows paths
    candidates = [
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\node\node.exe"),
        os.path.expandvars(r"%APPDATA%\npm\node.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def find_whatsapp_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "whatsapp_service",
        Path(getattr(sys, "_MEIPASS", "")) / "whatsapp_service",
        Path(sys.executable).parent / "whatsapp_service",
        Path(sys.executable).parent.parent / "whatsapp_service",
        Path(sys.executable).parent.parent / "backend" / "whatsapp_service",
        Path.cwd() / "backend" / "whatsapp_service",
        Path.cwd() / "whatsapp_service",
    ]
    for c in candidates:
        if (c / "server.js").is_file():
            return c
    return None


def start_whatsapp_service():
    global _service_process
    with _launch_lock:
        if is_service_listening(port=3001):
            return True

        js_dir = find_whatsapp_dir()
        if not js_dir:
            print("⚠️ whatsapp_service folder not found")
            return False

        node_bin = find_node_binary(js_dir)
        if not node_bin:
            err_msg = "Node.js runtime not found on this computer. Please install Node.js from https://nodejs.org"
            print(f"⚠️ {err_msg}")
            return False, err_msg
        creation_flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW

        # Log file for troubleshooting
        log_file_path = js_dir / "service.log"
        try:
            log_out = open(log_file_path, "a", encoding="utf-8")
        except Exception:
            log_out = subprocess.DEVNULL

        try:
            _service_process = subprocess.Popen(
                [node_bin, "server.js"],
                cwd=str(js_dir),
                stdout=log_out,
                stderr=log_out,
                creationflags=creation_flags
            )
            print(f"🚀 WhatsApp Baileys service launched (PID: {_service_process.pid})")
            return True
        except Exception as e:
            print(f"❌ Failed to start WhatsApp engine: {e}")
            return False


def ensure_whatsapp_running():
    if not is_service_listening(port=3001):
        threading.Thread(target=start_whatsapp_service, daemon=True).start()
