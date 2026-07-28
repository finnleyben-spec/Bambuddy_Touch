#!/bin/bash
# Kill old processes
pkill -9 cloudflared 2>/dev/null
pkill -9 -f "python3.*backend.py" 2>/dev/null
sleep 1

# Start backend
cd /home/finnley/Bambuddy_Touch
nohup python3 backend.py > /tmp/backend.log 2>&1 &
echo "Backend started (PID: $!)"

# Wait for backend to be ready
for i in {1..10}; do
    if lsof -i :8080 >/dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    sleep 1
done

# Start tunnel
nohup cloudflared tunnel --url http://localhost:8080 > /tmp/cloudflared.log 2>&1 &
echo "Tunnel started (PID: $!)"

# Wait for tunnel URL
sleep 5
grep -o 'https://[a-z0-9\-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
