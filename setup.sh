#!/bin/bash
# BamBuddy Clear Plate - Setup Script
# This script creates all necessary files for the Clear Plate controller

echo "🚀 Setting up Bambuddy Clear Plate Controller..."
echo ""

# Create directory structure
mkdir -p /home/pi/bambuddy-clearplate
cd /home/pi/bambuddy-clearplate

# Create .env file with API credentials
cat > .env << 'EOF'
# Bambuddy API Configuration - DO NOT SHARE THIS FILE!
BAMBUDY_API_URL=https://bambu.kronos.hs-ruhrwest.de/api/v1
BAMBUDY_API_KEY=bb_2mtNCBXPxgm3TXwfhNZ7rjj-CUPn5kF9GVO7082fll4
EOF

# Create backend.py server script
cat > backend.py << 'PYEOF'
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
API_URL = os.getenv('BAMBUDY_API_URL', 'https://bambu.kronos.hs-ruhrwest.de/api/v1')
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
        url = f"{API_URL}{path}"
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {API_KEY}')
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
        req.add_header('Authorization', f'Bearer {API_KEY}')
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
PYEOF

# Create frontend.html - the beautiful Clear Plate interface
cat > frontend.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Bambuddy - Clear Plate</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            padding: 20px;
            color: #ffffff;
        }

        .container { max-width: 800px; margin: 0 auto; }

        header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        h1 {
            font-size: 28px;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .subtitle { color: #a0aec0; font-size: 14px; }

        .printers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .printer-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }

        .printer-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(0, 212, 255, 0.1);
            border-color: rgba(0, 212, 255, 0.3);
        }

        .printer-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }

        .printer-name { font-size: 18px; font-weight: 600; color: #ffffff; }
        .printer-model { font-size: 12px; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px; }

        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .status-idle { background: rgba(72, 187, 120, 0.2); color: #48bb78; border: 1px solid rgba(72, 187, 120, 0.3); }
        .status-printing { background: rgba(56, 178, 255, 0.2); color: #38b2ff; border: 1px solid rgba(56, 178, 255, 0.3); }
        .status-error { background: rgba(245, 101, 101, 0.2); color: #f56565; border: 1px solid rgba(245, 101, 101, 0.3); }
        .status-complete { background: rgba(72, 187, 120, 0.2); color: #48bb78; border: 1px solid rgba(72, 187, 120, 0.3); }

        .clear-plate-btn {
            width: 100%;
            padding: 16px 24px;
            background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
            border: none;
            border-radius: 12px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
        }

        .clear-plate-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 212, 255, 0.4); }
        .clear-plate-btn:active:not(:disabled) { transform: translateY(0); }
        .clear-plate-btn:disabled { opacity: 0.6; cursor: not-allowed; background: rgba(128, 128, 128, 0.3); box-shadow: none; }

        @keyframes blink {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(0.98); }
        }

        .clear-plate-btn.blinking {
            animation: blink 1.5s ease-in-out infinite;
            box-shadow: 0 0 20px rgba(72, 187, 120, 0.6), 0 4px 15px rgba(0, 212, 255, 0.3);
        }

        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(5px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .modal-overlay.active { display: flex; }

        .modal {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 20px;
            padding: 32px;
            max-width: 400px;
            width: 100%;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }

        .modal-icon { font-size: 48px; text-align: center; margin-bottom: 20px; }
        .modal-title { font-size: 24px; font-weight: 600; text-align: center; margin-bottom: 12px; color: #ffffff; }
        .modal-text { color: #a0aec0; text-align: center; margin-bottom: 32px; line-height: 1.6; }

        .modal-buttons { display: flex; gap: 12px; }

        .btn-cancel, .btn-confirm {
            flex: 1;
            padding: 14px 24px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .btn-cancel { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #a0aec0; }
        .btn-cancel:hover { background: rgba(255, 255, 255, 0.15); }

        .btn-confirm {
            background: linear-gradient(135deg, #48bb78 0%, #38b2ff 100%);
            border: none; color: white; box-shadow: 0 4px 15px rgba(72, 187, 120, 0.3);
        }

        .btn-confirm:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(72, 187, 120, 0.4); }

        .success-animation {
            display: none;
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: linear-gradient(135deg, #48bb78 0%, #38b2ff 100%);
            padding: 40px; border-radius: 20px; z-index: 2000; animation: successPulse 0.6s ease-out;
        }

        .success-animation.active { display: block; }

        @keyframes successPulse {
            0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0; }
            50% { transform: translate(-50%, -50%) scale(1.1); }
            100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }

        .spinner { display: inline-block; width: 20px; height: 20px; border: 3px solid rgba(255, 255, 255, 0.3); border-radius: 50%; border-top-color: white; animation: spin 1s ease-in-out infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        @media (max-width: 640px) {
            body { padding: 10px; }
            h1 { font-size: 24px; }
            .printers-grid { grid-template-columns: 1fr; gap: 15px; }
            .printer-card { padding: 20px; }
            .modal { padding: 24px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🖨️ Bambuddy Control</h1>
            <p class="subtitle">Clear Plate Management</p>
        </header>

        <div class="printers-grid" id="printersGrid">
            <!-- Printer 1: X1C #1 (ID: 2) -->
            <div class="printer-card" data-printer-id="2">
                <div class="printer-header">
                    <div>
                        <div class="printer-name">X1 Carbon</div>
                        <div class="printer-model">#1 - Schrank o.l.</div>
                    </div>
                    <span class="status-badge status-idle" id="status-2">IDLE</span>
                </div>
                <button class="clear-plate-btn blinking" onclick="openConfirmModal(2, 'X1 Carbon #1')" data-printer-id="2">🧹 Clear Plate</button>
            </div>

            <!-- Printer 2: X1C #2 (ID: 1) -->
            <div class="printer-card" data-printer-id="1">
                <div class="printer-header">
                    <div>
                        <div class="printer-name">X1 Carbon</div>
                        <div class="printer-model">#2 - Schrank o.r.</div>
                    </div>
                    <span class="status-badge status-idle" id="status-1">IDLE</span>
                </div>
                <button class="clear-plate-btn blinking" onclick="openConfirmModal(1, 'X1 Carbon #2')" data-printer-id="1">🧹 Clear Plate</button>
            </div>

            <!-- Printer 3: X1C #3 (ID: 3) -->
            <div class="printer-card" data-printer-id="3">
                <div class="printer-header">
                    <div>
                        <div class="printer-name">X1 Carbon</div>
                        <div class="printer-model">#3 - Schrank u.r.</div>
                    </div>
                    <span class="status-badge status-idle" id="status-3">IDLE</span>
                </div>
                <button class="clear-plate-btn blinking" onclick="openConfirmModal(3, 'X1 Carbon #3')" data-printer-id="3">🧹 Clear Plate</button>
            </div>

            <!-- Printer 4: H2D (ID: 4) -->
            <div class="printer-card" data-printer-id="4">
                <div class="printer-header">
                    <div>
                        <div class="printer-name">H2D</div>
                        <div class="printer-model">#1 - Theke Fenster</div>
                    </div>
                    <span class="status-badge status-idle" id="status-4">IDLE</span>
                </div>
                <button class="clear-plate-btn blinking" onclick="openConfirmModal(4, 'H2D #1')" data-printer-id="4">🧹 Clear Plate</button>
            </div>
        </div>
    </div>

    <!-- Confirmation Modal -->
    <div class="modal-overlay" id="confirmModal">
        <div class="modal">
            <div class="modal-icon">🧹</div>
            <h2 class="modal-title">Clear Plate bestätigen?</h2>
            <p class="modal-text" id="modalText">Möchtest du die Druckplatte von <strong>X1 Carbon #1</strong> als sauber markieren?</p>
            <div class="modal-buttons">
                <button class="btn-cancel" onclick="closeModal()">Abbrechen</button>
                <button class="btn-confirm" id="confirmBtn" onclick="confirmClearPlate()">✓ Bestätigen</button>
            </div>
        </div>
    </div>

    <!-- Success Animation -->
    <div class="success-animation" id="successAnimation">
        <div class="success-icon">✓</div>
    </div>

    <script>
        const config = { apiUrl: 'http://localhost:8080/api' };
        
        const printerStates = {
            1: { status: 'idle', name: 'X1 Carbon #2' },
            2: { status: 'idle', name: 'X1 Carbon #1' },
            3: { status: 'idle', name: 'X1 Carbon #3' },
            4: { status: 'idle', name: 'H2D #1' }
        };

        let currentPrinterId = null;
        let currentPrinterName = null;

        function openConfirmModal(printerId, printerName) {
            currentPrinterId = printerId;
            currentPrinterName = printerName;
            document.getElementById('modalText').innerHTML = `Möchtest du die Druckplatte von <strong>${printerName}</strong> als sauber markieren?`;
            document.getElementById('confirmModal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('confirmModal').classList.remove('active');
            currentPrinterId = null;
            currentPrinterName = null;
        }

        async function confirmClearPlate() {
            if (!currentPrinterId) return;
            
            const btn = document.getElementById('confirmBtn');
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Wird gesendet...';

            try {
                const response = await fetch(`${config.apiUrl}/printers/${currentPrinterId}/clear-plate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (response.ok) {
                    showSuccess();
                    updateStatus(currentPrinterId, 'idle');
                } else {
                    throw new Error(`API Error: ${response.status}`);
                }
            } catch (error) {
                console.error('Error clearing plate:', error);
                alert(`Fehler beim Clear Plate:\n${error.message}\n\nStelle sicher, dass der Proxy-Server läuft.`);
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
                closeModal();
            }
        }

        function showSuccess() {
            const successEl = document.getElementById('successAnimation');
            successEl.classList.add('active');
            setTimeout(() => { successEl.classList.remove('active'); }, 1500);
        }

        function updateStatus(printerId, status) {
            const badge = document.getElementById(`status-${printerId}`);
            const btn = document.querySelector(`[data-printer-id="${printerId}"] .clear-plate-btn`);
            
            if (badge) {
                badge.className = 'status-badge';
                switch(status.toLowerCase()) {
                    case 'idle': badge.classList.add('status-idle'); badge.textContent = 'IDLE'; break;
                    case 'printing': badge.classList.add('status-printing'); badge.textContent = 'PRINTING'; break;
                    case 'error': badge.classList.add('status-error'); badge.textContent = 'ERROR'; break;
                    case 'complete': badge.classList.add('status-complete'); badge.textContent = 'COMPLETE'; break;
                }
            }

            if (btn) {
                switch(status.toLowerCase()) {
                    case 'printing': btn.disabled = true; btn.classList.remove('blinking'); btn.innerHTML = '⏸️ Druck läuft...'; break;
                    case 'idle': btn.disabled = false; btn.classList.add('blinking'); btn.innerHTML = '🧹 Clear Plate'; break;
                    case 'error': btn.disabled = true; btn.classList.remove('blinking'); btn.innerHTML = '⚠️ Fehler'; break;
                }
            }
        }

        async function fetchPrinterStatus() {
            try {
                const response = await fetch(`${config.apiUrl}/printers`, { headers: {} });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const printers = await response.json();
                printers.forEach(printer => {
                    const id = printer.id;
                    if (printerStates[id]) {
                        let status = 'idle';
                        if (printer.is_active && !printer.printing) status = 'printing';
                        else if (printer.error_state) status = 'error';
                        
                        printerStates[id].status = status;
                        updateStatus(id, status);
                    }
                });
            } catch (error) {
                console.error('Error fetching printer status:', error);
            }
        }

        document.getElementById('confirmModal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });

        fetchPrinterStatus();
        setInterval(fetchPrinterStatus, 30000);
    </script>
</body>
</html>
HTMLEOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "📁 Files created:"
echo "   - .env (API credentials)"
echo "   - backend.py (Python server)"
echo "   - frontend.html (Web interface)"
echo ""
echo "🚀 To start the server:"
echo "   cd /home/pi/bambuddy-clearplate"
echo "   python3 backend.py &"
echo ""
echo "🌐 Then open in browser:"
echo "   http://localhost:8080/"