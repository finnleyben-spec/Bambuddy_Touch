#!/usr/bin/env python3
"""
BamBuddy Clear Plate Proxy Server - FIXED VERSION
Sicherer lokaler Server, der die API-Keys vor dem Browser verbirgt.

Start: python3 backend.py
Stop:  Ctrl+C oder kill den Prozess
"""

import os
import sys
import json
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import urllib.request
import urllib.error
import ssl  # For SSL verification bypass

# SSL Context with proper certificate validation (not completely disabled)
def create_ssl_context():
    """Create SSL context with certificate verification enabled."""
    try:
        # Try to use system certificates first
        context = ssl.create_default_context()
        return context
    except Exception as e:
        print(f"⚠️  Could not load system CA certificates: {e}")
        print("   Falling back to unverified SSL (not recommended for production)")
        return SSL_CONTEXT

SSL_CONTEXT = create_ssl_context()

# Load .env file securely (only server-side)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Loads .env file in same directory
except ImportError:
    pass  # Fallback to manual loading below

# Manual fallback if python-dotenv not installed
if 'BAMBUDY_API_URL' not in os.environ and Path('.env').exists():
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value

# Configuration - ONLY accessible to this server
API_URL = os.getenv('BAMBUDY_API_URL', 'https://DEINE-API-URL.de/api/v1')
API_KEY = os.getenv('BAMBUDY_API_KEY', '')
AUTH_USERNAME = os.getenv('BAMBUDY_AUTH_USERNAME', '')
AUTH_PASSWORD = os.getenv('BAMBUDY_AUTH_PASSWORD', '')

# API-Schutz: Key der vom Frontend mitgesendet werden muss (X-API-Key Header)
BACKEND_API_KEY = os.getenv('BACKEND_API_KEY', 'bambuddy-local-key')

# JWT token (loaded at startup via login)
JWT_TOKEN = None


def do_login():
    """Login to Bambu API and store JWT token."""
    global JWT_TOKEN
    
    if not AUTH_USERNAME or not AUTH_PASSWORD:
        print("⚠️  No credentials in .env — using X-API-Key auth")
        return True
    
    url = f"{API_URL}/auth/login"
    payload = json.dumps({"username": AUTH_USERNAME, "password": AUTH_PASSWORD}).encode()
    
    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    
    try:
        with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
            data = json.loads(response.read().decode())
            JWT_TOKEN = data.get('access_token', '')
            if JWT_TOKEN:
                print(f"✅ Logged in successfully (JWT token obtained)")
                return True
            else:
                print(f"⚠️  Login returned no access_token")
                return False
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ''
        print(f"❌ Login failed (HTTP {e.code}): {error_body}")
        return False
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False


# Try login at startup if credentials provided
if AUTH_USERNAME and AUTH_PASSWORD:
    do_login()


class BambuddyProxyHandler(SimpleHTTPRequestHandler):
    """Handles API proxy requests from the frontend."""

    def get_auth_headers(self):
        """Return appropriate auth headers (JWT or X-API-Key)."""
        headers = {'Accept': 'application/json'}
        
        if JWT_TOKEN:
            # Use Bearer token (preferred)
            headers['Authorization'] = f'Bearer {JWT_TOKEN}'
        elif API_KEY.startswith('eyJ'):
            # Legacy JWT in .env
            headers['Authorization'] = f'Bearer {API_KEY}'
        else:
            # Fallback to X-API-Key
            headers['X-API-Key'] = API_KEY
        
        return headers

    def check_api_key(self):
        """Prüft ob der Frontend einen gültigen API-Key mitgesendet hat."""
        client_key = self.headers.get('X-API-Key', '')
        if not BACKEND_API_KEY or client_key == BACKEND_API_KEY:
            return True  # Key deaktiviert oder korrekt
        
        print(f"⚠️  Ungültiger API-Key von {self.client_address[0]}")
        self.send_json_response(401, {"error": "Unauthorized - Invalid API key"})
        return False

    def do_GET(self):
        """Handle GET requests - serve static files or fetch printer status."""
        
        # API-Schutz: Prüfe API-Key für alle /api/ Endpunkte
        if self.path.startswith('/api/') and not self.check_api_key():
            return
        
        # Update endpoint: /api/update -> run git pull + restart service
        if self.path == '/api/update':
            try:
                print("🔄 Starting update...")
                
                # Step 1: Git pull
                result = subprocess.run(
                    ['bash', '-c', 'cd ~/Bambuddy_Touch && git pull origin master'],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode != 0:
                    error_msg = (result.stderr or result.stdout).strip()
                    print(f"❌ Git pull failed: {error_msg}")
                    self.send_json_response(500, {"status": "error", "message": f"Git pull failed: {error_msg}"})
                    return
                
                # Step 2: Send success response FIRST (before restarting)
                self.send_json_response(200, {"status": "success", "message": "Update completed successfully"})
                
                # Step 3: Restart service in background (don't block the response)
                subprocess.Popen(['sudo', '-n', 'systemctl', 'restart', 'bambuddy-touch'])
                print("✅ Update successful! Service restart triggered.")
            except subprocess.TimeoutExpired:
                print("❌ Update timed out")
                try:
                    self.send_json_response(504, {"status": "error", "message": "Update timed out"})
                except:
                    pass
            except Exception as e:
                import traceback
                print(f"❌ Update error: {e}")
                traceback.print_exc()
                try:
                    self.send_json_response(500, {"status": "error", "message": str(e)})
                except:
                    pass
            return
        
        # Serve frontend HTML
        if self.path == '/' or self.path == '/frontend.html':
            self.serve_file('frontend.html', 'text/html')
            return
        
        # Smart plug control: /api/printers/{id}/smart-plug -> get smart plug for printer
        if self.path.startswith('/api/printers/') and self.path.endswith('/smart-plug'):
            parts = self.path.split('/')  # ['', 'api', 'printers', '1', 'smart-plug']
            if len(parts) >= 5:
                printer_id = parts[3]
                url = f"{API_URL}/smart-plugs/by-printer/{printer_id}"
                print(f"📡 Proxying GET to: {url}")
                
                req = urllib.request.Request(url)
                headers = self.get_auth_headers()
                for k, v in headers.items():
                    req.add_header(k, v)
                
                try:
                    with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
                        data = json.loads(response.read().decode())
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(data).encode())
                        return
                except urllib.error.HTTPError as e:
                    error_body = e.read().decode() if e.fp else ''
                    print(f"❌ API Error: {e.code} - {error_body}")
                    self.send_response(e.code)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": error_body}).encode())
                    return
            else:
                self.send_error(400, "Invalid path format")
                return
        
        # API proxy: /api/printers -> forward to real API
        if self.path.startswith('/api/'):
            try:
                response = self.proxy_request(self.path)
                if response is not None:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
                    return
            except Exception as e:
                print(f"❌ API Error: {e}")
        
        # Serve other static files (NOT /api/ paths)
        if self.path.startswith('/') and not self.path.startswith('/api/'):
            filename = self.path.lstrip('/')
            if os.path.exists(filename):
                self.serve_file(filename)
                return
        
        self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests - proxy to API."""
        
        # API-Schutz: Prüfe API-Key für alle /api/ Endpunkte
        if self.path.startswith('/api/') and not self.check_api_key():
            return
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        # Smart plug control: /api/printers/{id}/smart-plug/control -> POST to control endpoint
        if 'smart-plug' in self.path and 'control' in self.path:
            parts = self.path.split('/')  # ['', 'api', 'printers', '1', 'smart-plug', 'control']
            if len(parts) >= 6:
                printer_id = parts[3]
                
                # First get the smart plug ID for this printer
                try:
                    url = f"{API_URL}/smart-plugs/by-printer/{printer_id}"
                    req = urllib.request.Request(url)
                    headers = self.get_auth_headers()
                    for k, v in headers.items():
                        req.add_header(k, v)
                    
                    with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
                        smart_plug_data = json.loads(response.read().decode())
                        
                        if not smart_plug_data or 'id' not in smart_plug_data:
                            self.send_response(404)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": "No smart plug found for this printer"}).encode())
                            return
                        
                        plug_id = smart_plug_data['id']
                        
                        # Now control the plug
                        control_url = f"{API_URL}/smart-plugs/{plug_id}/control"
                        print(f"📡 Proxying POST to: {control_url}")
                        
                        req2 = urllib.request.Request(control_url, data=body, method='POST')
                        headers2 = self.get_auth_headers()
                        for k, v in headers2.items():
                            req2.add_header(k, v)
                        req2.add_header('Content-Type', 'application/json')
                        
                        with urllib.request.urlopen(req2, timeout=10, context=SSL_CONTEXT) as response:
                            data = json.loads(response.read().decode())
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps(data).encode())
                            return
                except urllib.error.HTTPError as e:
                    error_body = e.read().decode() if e.fp else ''
                    print(f"❌ API Error: {e.code} - {error_body}")
                    self.send_response(e.code)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": error_body}).encode())
                    return
                except Exception as e:
                    print(f"❌ Error: {e}")
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
                    return
        
        # Proxy the request
        try:
            response_data, status_code = self.proxy_request_with_body(
                self.path, 
                body.decode() if body else '{}'
            )
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
        except Exception as e:
            print(f"❌ API Error: {e}")
            error_response = {"error": str(e)}
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

    def proxy_request(self, path):
        """Forward GET request to the real API."""
        
        # Handle printer status endpoint specially: /api/printers/{id}/status
        if path.startswith('/api/printers/') and path.endswith('/status'):
            parts = path.split('/')  # ['', 'api', 'printers', '1', 'status']
            if len(parts) >= 5:
                printer_id = parts[3]
                url = f"{API_URL}/printers/{printer_id}/status"
            else:
                raise Exception(f"Invalid path format: {path}")
        # Handle clear-plate GET: /api/printers/{id}/clear-plate/
        elif path.startswith('/api/printers/') and 'clear-plate' in path:
            parts = path.split('/')  # ['', 'api', 'printers', '1', 'clear-plate']
            if len(parts) >= 5:
                printer_id = parts[3]
                url = f"{API_URL}/printers/{printer_id}/clear-plate"
            else:
                raise Exception(f"Invalid path format: {path}")
        # Legacy clear-plate: /api/{id}/clear-plate/
        elif path.startswith('/api/') and 'clear-plate' in path:
            parts = path.split('/')  # ['', 'api', '2', 'clear-plate']
            if len(parts) >= 4:
                printer_id = parts[2]
                url = f"{API_URL}/printers/{printer_id}/clear-plate"
            else:
                raise Exception(f"Invalid path format: {path}")
        # List printers: /api/printers -> /api/v1/printers/
        elif path == '/api/printers':
            url = f"{API_URL}/printers/"
        else:
            # Default: forward as-is (strip /api prefix, keep rest)
            if path.startswith('/api/'):
                # Remove only the '/api' prefix, keep everything after it
                remainder = path[4:]  # e.g. "/v1/smart-plugs/" or "/printers/1/status"
                url = f"{API_URL}{remainder}"
            else:
                url = f"{API_URL}{path}"
        
        print(f"📡 Proxying GET to: {url}")
        
        req = urllib.request.Request(url)
        headers = self.get_auth_headers()
        for k, v in headers.items():
            req.add_header(k, v)
        
        try:
            with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
                data = json.loads(response.read().decode())
                return data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ''
            raise Exception(f"HTTP {e.code}: {error_body}")

    def proxy_request_with_body(self, path, body):
        """Forward POST request to the real API."""
        
        # Handle clear-plate endpoint (with or without trailing slash)
        if 'clear-plate' in path:
            parts = path.split('/')  # ['', 'api', '1', 'clear-plate'] or ['', 'api', 'printers', '1', 'clear-plate']
            
            # Check if it's /api/printers/{id}/clear-plate format
            if len(parts) >= 5 and parts[2] == 'printers':
                printer_id = parts[3]
                url = f"{API_URL}/printers/{printer_id}/clear-plate"
            elif len(parts) >= 4:
                # It's /api/{id}/clear-plate format - convert to proper format
                printer_id = parts[2]
                url = f"{API_URL}/printers/{printer_id}/clear-plate"
            else:
                raise Exception(f"Invalid path format: {path}")
        else:
            # Default: forward as-is (no trailing slash for POST)
            if path.startswith('/api/'):
                remainder = path[4:]  # Remove only '/api' prefix, keep rest
                url = f"{API_URL}{remainder}"
            else:
                url = f"{API_URL}{path}"
        
        print(f"📡 Proxying POST to: {url}")
        
        req = urllib.request.Request(url, data=body.encode(), method='POST')
        headers = self.get_auth_headers()
        for k, v in headers.items():
            req.add_header(k, v)
        req.add_header('Content-Type', 'application/json')
        
        try:
            with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
                data = json.loads(response.read().decode())
                return data, 200
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ''
            try:
                error_data = json.loads(error_body)
            except:
                error_data = {"error": error_body}
            raise Exception(f"HTTP {e.code}: {error_body}")

    def serve_file(self, filename, content_type='application/octet-stream'):
        """Serve a static file."""
        try:
            with open(filename, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "File not found")

    def send_json_response(self, status_code, data):
        """Send a JSON response."""
        body = json.dumps(data).encode()
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Log requests to console."""
        print(f"📡 {self.client_address[0]} - {format % args}")


def main():
    server = HTTPServer(('0.0.0.0', 8080), BambuddyProxyHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        sys.exit(0)


if __name__ == '__main__':
    main()
