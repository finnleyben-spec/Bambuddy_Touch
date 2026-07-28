#!/bin/bash
# Bambuddy Touch - Autostart Script
# Starts the backend server and launches Chromium in kiosk mode

sleep 5  # Wait for system to be ready

# Start backend server (if not already running)
cd /home/pi/Bambuddy_Touch
python3 backend.py &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Launch Chromium in kiosk mode
chromium-browser --kiosk --noerrdialogs --disable-features=TranslateUI http://localhost:8080 &

echo "Bambuddy Touch started successfully!"