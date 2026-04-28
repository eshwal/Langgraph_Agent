import subprocess
import sys
import os
import platform
import threading
import signal
import time
import requests

# Path to your virtual environment
VENV_PATH = "../chatenv"

FASTAPI_APP = "./main.py"
STREAMLIT_APP = "./ui/streamlit_frontend.py"

FASTAPI_URL = "http://127.0.0.1:8000/docs"

processes = []

def run_fastapi():
    python_bin = os.path.join(
        VENV_PATH, 
        "Scripts" if platform.system()=="Windows" else "bin", 
        "python"
    )

    cmd = [python_bin,FASTAPI_APP]
    proc = subprocess.Popen(cmd)
    processes.append(proc)

    proc.wait()

def wait_for_fastapi(timeout=30):
    """Return True only if FastAPI actually starts."""
    start = time.time()

    while time.time() - start < timeout:
        try:
            r = requests.get(FASTAPI_URL)
            if r.status_code == 200:
                print("FastAPI is ready!")
                return True
        except requests.exceptions.ConnectionError:
            pass
        
        time.sleep(1)

    return False  #  FastAPI did NOT start

def run_streamlit():
    python_bin = os.path.join(
        VENV_PATH, 
        "Scripts" if platform.system()=="Windows" else "bin", 
        "python"
    )

    cmd = [python_bin, "-m", "streamlit", "run", STREAMLIT_APP]
    proc = subprocess.Popen(cmd)
    processes.append(proc)
    proc.wait()

def signal_handler(sig, frame):
    print("\nStopping all processes...")
    for p in processes:
        p.terminate()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    # Start backend
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.start()

    # Wait for backend to come alive
    print("Waiting for FastAPI to start...")
    if not wait_for_fastapi():
        print("FastAPI failed to start. Not launching Streamlit.")
        # terminate backend if running
        for p in processes:
            p.terminate()
        sys.exit(1)

    # Start frontend
    print("Starting Streamlit...")
    streamlit_thread = threading.Thread(target=run_streamlit)
    streamlit_thread.start()

    fastapi_thread.join()
    streamlit_thread.join()
