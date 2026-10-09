import os
import subprocess
import sys
from pathlib import Path

def build_executable():
    """Build the Windows executable using PyInstaller."""
    
    # Ensure dependencies are installed
    print("Installing build dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview", "pyinstaller"])
    
    # Paths
    backend_dir = Path(__file__).resolve().parent
    frontend_dist = backend_dir.parent / "frontend" / "dist"
    
    if not frontend_dist.exists():
        print("Error: React dist folder not found. Please run 'npm run build' in the frontend folder first.")
        sys.exit(1)
        
    print(f"Bundling frontend dist from: {frontend_dist}")
    
    # PyInstaller arguments
    # --noconsole: hides the terminal window
    # --onefile: packages everything into a single .exe
    # --name: the output file name
    # --add-data: includes the frontend dist folder
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "MoiraLuxe",
        "--icon", "logo.ico",
        "--add-data", f"{frontend_dist};frontend/dist",
        "--hidden-import", "passlib.handlers.bcrypt",
        "--hidden-import", "bcrypt",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--clean",
        str(backend_dir / "desktop.py")
    ]
    
    print(f"Running PyInstaller: {' '.join(args)}")
    
    # Run PyInstaller
    # Using shell=True on Windows is sometimes necessary for PyInstaller to be found in Scripts
    subprocess.check_call(" ".join(args), shell=True, cwd=str(backend_dir))
    
    print("\n[OK] Build complete! The executable is located in the 'dist' folder.")

if __name__ == "__main__":
    build_executable()
