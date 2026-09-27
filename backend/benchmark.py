import time
import urllib.parse
from sqlalchemy import create_engine, text
from app.config import settings

def run_benchmark():
    print("Running Database Performance Benchmark...")
    print(f"Target DB: {settings.DATABASE_URL.split('@')[-1]}")
    
    # Connect
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # 1. Ping Latency Test
            start = time.perf_counter()
            conn.execute(text("SELECT 1"))
            ping_ms = (time.perf_counter() - start) * 1000
            print(f"Network Ping (SELECT 1): {ping_ms:.2f} ms")
            
            # 2. Standard Fetch Test
            start = time.perf_counter()
            conn.execute(text("SELECT * FROM sales LIMIT 50"))
            fetch_ms = (time.perf_counter() - start) * 1000
            print(f"Standard Fetch (SELECT * FROM sales LIMIT 50): {fetch_ms:.2f} ms")
            
            # Analysis
            print("\nAnalysis:")
            print(f"Query Execution: Fetching 50 full sales rows takes roughly ~{fetch_ms:.2f} ms.")
            if ping_ms > 50:
                print(f"Connection Latency: The ping took ~{ping_ms:.2f} ms. This indicates the database is hosted remotely.")
            
    except Exception as e:
        print(f"Benchmark failed: {e}")

if __name__ == "__main__":
    run_benchmark()
