"""
BHOOMI V2 — ONE-CLICK DEMONSTRATION LAUNCHER
Starts the FastAPI Backend on http://127.0.0.1:8000
and serves the Web Application on http://127.0.0.1:3000.
"""

import os
import sys
import time
import subprocess
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
WEB_BUILD_DIR = os.path.join(ROOT_DIR, "frontend", "web")

import socket
import urllib.request
import urllib.error

def find_free_port(preferred_port: int, max_tries: int = 50) -> int:
    """Finds a guaranteed free TCP port on localhost starting from preferred_port."""
    for port in range(preferred_port, preferred_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Could not find free port near {preferred_port}")

BACKEND_PORT = find_free_port(int(os.environ.get("BACKEND_PORT", 8085)))
FRONTEND_PORT = find_free_port(int(os.environ.get("FRONTEND_PORT", 3055)))

class WebAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_BUILD_DIR, **kwargs)

    def do_OPTIONS(self):
        if self.path.startswith("/api/"):
            self._proxy_request("OPTIONS")
            return
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy_request("POST")
            return
        super().do_POST()

    def do_PUT(self):
        if self.path.startswith("/api/"):
            self._proxy_request("PUT")
            return
        self.send_response(405)
        self.end_headers()

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self._proxy_request("DELETE")
            return
        self.send_response(405)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy_request("GET")
            return
        # SPA routing: if path does not exist as file, serve index.html
        path_without_query = self.path.split("?")[0].lstrip("/")
        full_path = os.path.join(WEB_BUILD_DIR, path_without_query)
        if not os.path.exists(full_path) and not os.path.splitext(path_without_query)[1]:
            self.path = "/index.html"
        return super().do_GET()

    def _proxy_request(self, method):
        backend_url = f"http://127.0.0.1:{BACKEND_PORT}{self.path}"
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length")}
        req = urllib.request.Request(backend_url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                resp_bytes = resp.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "content-length", "connection"):
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(resp_bytes)))
                self.end_headers()
                self.wfile.write(resp_bytes)
        except urllib.error.HTTPError as err:
            try:
                err_bytes = err.read()
                self.send_response(err.code)
                for k, v in err.headers.items():
                    if k.lower() not in ("transfer-encoding", "content-length", "connection"):
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(err_bytes)))
                self.end_headers()
                self.wfile.write(err_bytes)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                pass
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass
        except Exception as exc:
            try:
                err_msg = str(exc).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Length", str(len(err_msg)))
                self.end_headers()
                self.wfile.write(err_msg)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

def run_backend():
    print(f"[1/2] Starting BHOOMI V2 FastAPI Backend on http://127.0.0.1:{BACKEND_PORT} ...")
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(BACKEND_PORT)]
    backend_env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    proc = subprocess.Popen(cmd, cwd=BACKEND_DIR, env=backend_env)
    return proc

def run_frontend():
    print(f"[2/2] Serving BHOOMI V2 Web Application on http://127.0.0.1:{FRONTEND_PORT} ...")
    server = ThreadingHTTPServer(("0.0.0.0", FRONTEND_PORT), WebAppHandler)
    server.serve_forever()

if __name__ == "__main__":
    print("=" * 65)
    print("   BHOOMI V2 -- PERSONAL AI FARM MANAGER (WEB DEMONSTRATION)")
    print("=" * 65)

    backend_proc = run_backend()

    time.sleep(2)

    web_thread = threading.Thread(target=run_frontend, daemon=True)
    web_thread.start()

    print(f"\n[OK] Backend API active at:    http://127.0.0.1:{BACKEND_PORT}")
    print(f"[OK] Web Application active at: http://127.0.0.1:{FRONTEND_PORT}")
    print(f"[OK] Swagger Docs available at: http://127.0.0.1:{BACKEND_PORT}/docs")
    print("\nKeep this window open during your demonstration.\nPress Ctrl+C to stop both servers.\n")

    try:
        while True:
            ret = backend_proc.poll()
            if ret is not None:
                print(f"\nBackend process exited with code {ret}. Shutting down...")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping BHOOMI servers...")
    except Exception as e:
        print(f"\nUnexpected error in server monitor: {e}")
    finally:
        if backend_proc.poll() is None:
            backend_proc.terminate()
        sys.exit(0)
