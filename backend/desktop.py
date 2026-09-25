import threading
import time
import uvicorn
import webview
import sys
import os

import urllib.request
from urllib.error import URLError

from app.main import app

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
    wait_for_server(server_url)

    # Open the Desktop Window pointing to the local server
    webview.create_window(
        title="Billing Software",
        url=server_url,
        width=1280,
        height=800,
        min_size=(1024, 600),
        text_select=False,
    )
    
    # Start the webview GUI event loop
    webview.start()
