#!/bin/bash
set -e

echo "=== Bambuddy Touch - Starting Services ==="

# Kill old processes
pkill -9 cloudflared 2>/dev/null || true
pkill -9 -f "python3.*backend.py" 2>/dev/null || true
sleep 1

# Start backend
cd /home/finnley/Bambuddy_Touch
echo "Starting backend on port 8080..."
python3 backend.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to be ready
for i in {1..15}; do
    if lsof -i :8080 >/dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    sleep 1
done

# Test backend
echo "Testing backend..."
curl -s http://localhost:8080/api/printers/4/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   State: {d[\"state\"]}, Progress: {d[\"progress\"]}%')"

# Start tunnel
echo ""
echo "Starting Cloudflare Tunnel..."
cloudflared tunnel --url http://localhost:8080 2>&1 | grep -E "https://|tunnel" &
TUNNEL_PID=$!
sleep 5

# Get the URL from cloudflared output
TUNNEL_URL=$(grep -o 'https://[a-z0-9\-]*\.trycloudflare\.com' /proc/$TUNNEL_PID/fd/1 2>/dev/null || echo "")

if [ -z "$TUNNEL_URL" ]; then
    # Try to get it from the running process output
    sleep 3
    TUNNEL_URL=$(ps aux | grep cloudflared | grep -o 'https://[a-z0-9\-]*\.trycloudflare\.com' || echo "")
fi

echo ""
echo "=========================================="
if [ -n "$TUNNEL_URL" ]; then
    echo "🎉 SUCCESS! Open this URL on your Mac:"
    echo ""
    echo "   $TUNNEL_URL"
    echo ""
    echo "The tunnel is running in the background."
else
    echo "⚠️  Tunnel started but couldn't capture URL"
    echo "   Check cloudflared logs for the URL"
fi
echo "=========================================="

# Keep script running
wait
