import subprocess
import time
import signal
import sys
import os
import threading
import datetime

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

class TeeStream:
    def __init__(self, streams, lock):
        self.streams = streams
        self.lock = lock

    def write(self, data):
        if not data:
            return
        with self.lock:
            for s in self.streams:
                try:
                    s.write(data)
                except Exception:
                    pass

    def flush(self):
        with self.lock:
            for s in self.streams:
                try:
                    s.flush()
                except Exception:
                    pass

    def isatty(self):
        return any(getattr(s, "isatty", lambda: False)() for s in self.streams)

    def fileno(self):
        for s in self.streams:
            if hasattr(s, "fileno"):
                try:
                    return s.fileno()
                except Exception:
                    continue
        raise OSError("No valid fileno")

def start_stream_forwarder(stream, target):
    def _forward():
        try:
            for line in iter(stream.readline, ""):
                target.write(line)
                target.flush()
        except Exception:
            pass
        finally:
            try:
                stream.close()
            except Exception:
                pass
    t = threading.Thread(target=_forward, daemon=True)
    t.start()
    return t

def cleanup_stale_processes():
    print("Cleaning up stale Chrome/Driver processes...")
    try:
        subprocess.run(["pkill", "-f", "chrome"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "chromedriver"], stderr=subprocess.DEVNULL)
    except Exception:
        pass

def run_server():
    base_dir = os.getcwd()
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_filename = datetime.datetime.now().strftime("run-%Y%m%d-%H%M%S.log")
    log_path = os.path.join(logs_dir, log_filename)

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    tee_lock = threading.Lock()
    sys.stdout = TeeStream([original_stdout, log_file], tee_lock)
    sys.stderr = TeeStream([original_stderr, log_file], tee_lock)

    print(f"Logging all output to: {log_path}")
    print("Starting Waseda Grade Scraper System...")
    
    # Define paths
    backend_dir = os.path.join(base_dir, "waseda-grade-api")
    frontend_dir = os.path.join(base_dir, "frontend")
    
    # Check swap status
    try:
        with open('/proc/swaps', 'r') as f:
            content = f.read()
            if content.count('\n') < 2: # Header is one line
                print("WARNING: No swap file detected! The server may crash due to low memory.")
    except Exception:
        pass

    # Cleanup before start
    cleanup_stale_processes()
    
    # Check if frontend build exists
    if not os.path.exists(os.path.join(frontend_dir, ".next")):
        print("Warning: Frontend build (.next) not found. Attempting to build...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
        except subprocess.CalledProcessError:
            print("Error: Frontend build failed.")
            sys.exit(1)

    # Environment variables for Node.js memory limit
    env = os.environ.copy()
    env["NODE_OPTIONS"] = "--max-old-space-size=256"
    env["BACKEND_URL"] = "http://127.0.0.1:8001"
    
    processes = []
    stream_threads = []

    try:
        # Check if port 8001 is already in use
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8001))
        sock.close()
        if result == 0:
            print("WARNING: Port 8001 is already in use. Backend might fail to start.")
            print("Please stop any running instances (e.g., Docker) if you want to run locally.")

        # Start Backend
        print("Starting Backend (waseda-grade-api)...")
        backend_python = os.path.join(backend_dir, ".venv/bin/python")
        if not os.path.exists(backend_python):
             print(f"Error: Virtual environment python not found at {backend_python}")
             print("Please run 'make install' first.")
             sys.exit(1)
             
        backend_env = os.environ.copy()
        backend_env["PYTHONUNBUFFERED"] = "1"
        backend_cmd = [backend_python, "-u", "main.py"]
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=backend_dir,
            env=backend_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        processes.append(backend_proc)
        stream_threads.append(start_stream_forwarder(backend_proc.stdout, sys.stdout))
        stream_threads.append(start_stream_forwarder(backend_proc.stderr, sys.stderr))
        
        # Wait for backend to be ready
        print("Waiting for backend to start on port 8001...")
        backend_ready = False
        for _ in range(30):  # Wait up to 30 seconds
            if backend_proc.poll() is not None:
                print(f"Backend process exited unexpectedly with code {backend_proc.returncode}")
                break
            
            try:
                with socket.create_connection(("127.0.0.1", 8001), timeout=1):
                    backend_ready = True
                    print("Backend is ready!")
                    break
            except (OSError, ConnectionRefusedError):
                time.sleep(1)
        
        if not backend_ready and backend_proc.poll() is None:
             print("Warning: Backend did not respond on port 8001 within 30 seconds.")
        
        # Start Frontend
        print("Starting Frontend (Next.js)...")
        frontend_cmd = ["npm", "start"]
        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=frontend_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        processes.append(frontend_proc)
        stream_threads.append(start_stream_forwarder(frontend_proc.stdout, sys.stdout))
        stream_threads.append(start_stream_forwarder(frontend_proc.stderr, sys.stderr))
        
        print("Both servers are running. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print(f"Backend process exited with code {backend_proc.returncode}")
                break
            if frontend_proc.poll() is not None:
                print(f"Frontend process exited with code {frontend_proc.returncode}")
                break
                
    except KeyboardInterrupt:
        print("\nStopping servers...")
    finally:
        print("Terminating processes...")
        for p in processes:
            if p.poll() is None:
                p.terminate()
        
        # Wait for termination
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        
        print("Servers stopped.")
        for t in stream_threads:
            t.join(timeout=2)
        try:
            log_file.flush()
            log_file.close()
        except Exception:
            pass
        sys.stdout = original_stdout
        sys.stderr = original_stderr

if __name__ == "__main__":
    run_server()
