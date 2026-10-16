import threading
import time
import uvicorn
import webview
import sys
import os
import socket
import traceback
from pathlib import Path

import urllib.request
from urllib.error import URLError, HTTPError

import base64
import tkinter as tk
from tkinter import filedialog
from app.main import app

class DesktopApi:
    def save_excel(self, base64_data, filename):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=filename,
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Save Report"
        )
        if filepath:
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(base64_data))
            return True
        return False


server_error_info = []


def get_log_file_path() -> Path:
    try:
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
            log_p = base_dir / "moiraluxe_startup.log"
            with open(log_p, "a") as f:
                pass
            return log_p
    except Exception:
        pass
    return Path(os.environ.get("TEMP", os.path.expanduser("~"))) / "moiraluxe_startup.log"


def write_startup_log(msg: str):
    try:
        log_p = get_log_file_path()
        with open(log_p, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def find_available_port(preferred_port=8000, max_attempts=15) -> int:
    """Find preferred_port or the next available local TCP port."""
    for port in range(preferred_port, preferred_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            # connect_ex returns 0 if port is open (already in use), non-zero if free
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return preferred_port


def run_server(port: int):
    """Run the FastAPI backend on 127.0.0.1:<port>"""
    try:
        write_startup_log(f"Starting uvicorn server on 127.0.0.1:{port}...")
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    except Exception as e:
        err = traceback.format_exc()
        server_error_info.append(err)
        write_startup_log(f"Uvicorn crash: {err}")


def wait_for_server(base_url: str, timeout=35.0):
    """Wait for the server to be responsive before opening the window."""
    start_time = time.time()
    health_url = f"{base_url}/api/health"
    write_startup_log(f"Waiting for server at {health_url} (timeout={timeout}s)...")

    while time.time() - start_time < timeout:
        if server_error_info:
            return False, server_error_info[0]

        try:
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    write_startup_log("Server responded with 200 OK!")
                    return True, None
        except HTTPError:
            # If server returned an HTTP error (404, 500), it is alive and listening
            write_startup_log("Server responded with HTTP status, server is alive.")
            return True, None
        except (URLError, socket.timeout):
            time.sleep(0.5)

    if server_error_info:
        return False, server_error_info[0]
    return False, "Server timed out after 35 seconds without responding to requests."


if __name__ == '__main__':
    # Find free port (8000, 8001, etc.)
    port = find_available_port(8000)
    server_url = f"http://127.0.0.1:{port}"

    # Start the backend server in a background thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait robustly for the server to start before opening the window
    is_alive, error_msg = wait_for_server(server_url)
    if not is_alive:
        log_file = get_log_file_path()
        write_startup_log(f"Server start failed: {error_msg}")
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()

        detail_text = f"The backend server failed to start on port {port}.\n\n"
        if error_msg:
            short_err = error_msg.strip()
            if len(short_err) > 350:
                short_err = short_err[-350:]
            detail_text += f"Error Details:\n{short_err}\n\n"
        detail_text += f"A detailed startup log was saved to:\n{log_file}\n\nPlease check your internet connection and database status."

        messagebox.showerror("Server Error", detail_text)
        sys.exit(1)

    api = DesktopApi()
    # Open the Desktop Window pointing to the local server
    webview.create_window(
        title="Billing Software",
        url=server_url,
        js_api=api,
        width=1280,
        height=800,
        min_size=(1024, 600),
        text_select=False,
    )

    # Start the webview GUI event loop
    webview.start()

    # Force exit to ensure the uvicorn daemon thread and any async threadpools are killed immediately
    import os
    os._exit(0)
