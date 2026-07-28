#!/bin/bash
# Bambuddy Touch - Ein-Klick Setup auf Raspberry Pi
set -e

echo "🚀 Bambuddy Touch Autostart Setup"
echo "=================================="

# 1. Repository klonen (falls nicht vorhanden)
if [ ! -d "/home/pi/Bambuddy_Touch" ]; then
    echo ""
    echo "📦 Repository wird geklont..."
    git clone https://github.com/finnleyben-spec/Bambuddy_Touch.git /home/pi/Bambuddy_Touch
else
    echo "✅ Bambuddy_Touch Verzeichnis existiert bereits"
fi

cd /home/pi/Bambuddy_Touch

# 2. .env prüfen
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  .env Datei fehlt!"
    echo ""
    echo "Bitte trage deine API-Credentials ein:"
    read -p "BAMBUDY_API_URL: " api_url
    read -p "BAMBUDY_API_KEY: " api_key
    
    cat > .env << EOF
BAMBUDY_API_URL=$api_url
BAMBUDY_API_KEY=$api_key
EOF
    echo "✅ .env erstellt"
else
    echo "✅ .env existiert bereits"
fi

# 3. systemd Service installieren
echo ""
echo "🔧 systemd Service wird eingerichtet..."
sudo cp bambuddy-touch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bambuddy-touch

# 4. Status anzeigen
echo ""
echo "=================================="
echo "✅ Setup abgeschlossen!"
echo ""
echo "Server läuft: $(systemctl is-active bambuddy-touch)"
echo ""
echo "🌐 Öffne im Browser: http://localhost:8080"
echo ""
echo "Logs anzeigen: sudo journalctl -u bambuddy-touch -f"
echo "=================================="
