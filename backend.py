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

if not API_KEY:
    print("❌ ERROR: BAMBUDY_API_KEY not found in .env file!")
    sys.exit(1)

print(f"✅ BamBuddy Proxy Server starting...")
print(f"   API URL: {API_URL}")
print(f"   API Key: {'*' * 20}{API_KEY[-4:]}")
print(f"   Listening on http://localhost:8080")
print()

# Simple HTTP client using urllib (no external dependencies)
import urllib.request
import urllib.error


class BambuddyProxyHandler(SimpleHTTPRequestHandler):
    """Handles API proxy requests from the frontend."""

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
                if response:
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
        # Try X-API-Key first, fallback to Bearer token
        if API_KEY.startswith('eyJ'):  # JWT token from login
            req.add_header('Authorization', f'Bearer {API_KEY}')
        else:
            req.add_header('X-API-Key', API_KEY)
        req.add_header('Accept', 'application/json')
        
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
        req.add_header('X-API-Key', API_KEY)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')
        
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
