#!/usr/bin/env python3
"""
BamBuddy Clear Plate Proxy Server
Sicherer lokaler Server, der die API-Keys vor dem Browser verbirgt.

Start: python3 backend.py
Stop:  Ctrl+C oder kill den Prozess
"""

import os
import sys
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

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
        with urllib.request.urlopen(req, timeout=10) as response:
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


# Simple HTTP client using urllib (no external dependencies)
import urllib.request
import urllib.error

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

    def do_GET(self):
        """Handle GET requests - serve static files or fetch printer status."""
        
        # Serve frontend HTML
        if self.path == '/' or self.path == '/frontend.html':
            self.serve_file('frontend.html', 'text/html')
            return
        
        # API proxy: /api/printers -> forward to real API
        if self.path.startswith('/api/'):
            try:
                response = self.proxy_request(self.path)
                if response is not None:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
                    return
            except Exception as e:
                print(f"❌ API Error: {e}")
        
        # Serve other static files
        if self.path.startswith('/'):
            filename = self.path.lstrip('/')
            if os.path.exists(filename):
                self.serve_file(filename)
                return
        
        self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests - proxy to API."""
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
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
        
        # Handle printer status endpoint specially
        if path == '/api/printers':
            url = f"{API_URL}/printers/"  # Add trailing slash!
        elif path.startswith('/api/') and 'clear-plate' in path:
            # Extract printer ID from /api/{id}/clear-plate
            parts = path.split('/')  # ['', 'api', '2', 'clear-plate']
            if len(parts) >= 4:
                printer_id = parts[2]
                url = f"{API_URL}/printers/{printer_id}/clear-plate/"  # Add trailing slash!
            else:
                raise Exception(f"Invalid path format: {path}")
        else:
            # Default: forward as-is (but strip /api/ prefix)
            if path.startswith('/api/'):
                url = f"{API_URL}{path[4:]}/"  # Remove '/api' prefix and add trailing slash
            else:
                url = f"{API_URL}{path}"
        
        print(f"📡 Proxying to: {url}")
        
        req = urllib.request.Request(url)
        headers = self.get_auth_headers()
        for k, v in headers.items():
            req.add_header(k, v)
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                return data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ''
            raise Exception(f"HTTP {e.code}: {error_body}")

    def proxy_request_with_body(self, path, body):
        """Forward POST request to the real API."""
        url = f"{API_URL}{path}"
        
        req = urllib.request.Request(url, data=body.encode(), method='POST')
        headers = self.get_auth_headers()
        for k, v in headers.items():
            req.add_header(k, v)
        req.add_header('Content-Type', 'application/json')
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
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

    def log_message(self, format, *args):
        """Log requests to console."""
        print(f"📡 {self.client_address[0]} - {format % args}")


def main():
    server = HTTPServer(('127.0.0.1', 8080), BambuddyProxyHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        sys.exit(0)


if __name__ == '__main__':
    main()
