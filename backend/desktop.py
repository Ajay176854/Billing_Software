import threading
import time
import uvicorn
import webview
import sys
import os

import urllib.request
from urllib.error import URLError

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


def run_server():
    """Run the FastAPI backend on localhost:8000"""
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

def wait_for_server(url, timeout=20.0):
    """Wait for the server to be responsive before opening the window"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url)
            return True
        except URLError:
            time.sleep(0.5)
    return False

if __name__ == '__main__':
    # Start the backend server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    server_url = "http://127.0.0.1:8000"
    
    # Wait robustly for the server to start before opening the window
    if not wait_for_server(server_url):
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Server Error", "The backend server failed to start. Port 8000 might be in use or there was a missing dependency.")
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
