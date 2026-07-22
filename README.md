# 🖨️ Bambuddy Clear Plate Controller

Ein Web-basiertes Interface zum Steuern von Bambu Lab Druckern über die Bambu Studio API. Besonders geeignet für den Einsatz auf dem Raspberry Pi mit Touchscreen.

## ✨ Features

- **Multi-Printer Support** — Steuerung mehrerer Drucker gleichzeitig
- **Clear Plate Funktion** — Markiere Druckplatten als "leer" nach dem Druck
- **Echtzeit-Status** — Zeigt aktuellen Status jedes Druckers an
- **Touch-optimiert** — Perfekt für Raspberry Pi Touchscreens
- **Sicher** — API-Credentials bleiben serverseitig, nie im Browser sichtbar

## 📋 Voraussetzungen

- Python 3.7+ (vorinstalliert auf Raspberry Pi OS)
- Raspberry Pi mit Netzwerkzugang
- Bambu Lab Drucker mit Bambu Studio API aktiviert

## 🚀 Installation

### 1. Repository klonen

```bash
cd /home/pi
git clone https://github.com/finnleyben-spec/Bambuddy_Touch.git
cd Bambuddy_Touch
```

### 2. API-Credentials konfigurieren

Erstelle die `.env` Datei mit deinen Bambu Studio Credentials:

```bash
cat > .env << 'EOF'
BAMBUDY_API_URL=https://bambu.kronos.hs-ruhrwest.de/api/v1
BAMBUDY_API_KEY=dein_api_key_hier
EOF
```

**Wichtig:** Die `.env` Datei ist im `.gitignore`, also werden deine Credentials nicht mitgepushed!

### 3. Server starten

```bash
python3 backend.py
```

Der Server läuft jetzt auf `http://localhost:8080`

## 🏠 Autostart einrichten (systemd)

Damit der Server automatisch beim Systemstart startet und bei Crash neustartet:

```bash
# Service-Datei installieren
sudo cp bambuddy-clearplate.service /etc/systemd/system/

# Service aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable bambuddy-clearplate
sudo systemctl start bambuddy-clearplate

# Status prüfen
sudo systemctl status bambuddy-clearplate
```

### Logs anzeigen

```bash
# Live-Logs
sudo journalctl -u bambuddy-clearplate -f

# Letzte Einträge
sudo journalctl -u bambuddy-clearplate --since today
```

## 🌐 Zugriff

Öffne im Browser:

- **Auf dem Raspberry Pi:** `http://localhost:8080`
- **Im lokalen Netzwerk:** `http://<raspberry-pi-ip>:8080`

### Touchscreen optimieren (optional)

Für einen kiosk-modus ohne Adressleiste:

```bash
# Chromium im Kiosk-Modus starten
chromium-browser --kiosk --noerrdialogs http://localhost:8080 &
```

## 📁 Projektstruktur

```
Bambuddy_Touch/
├── backend.py          # Python Proxy-Server (Port 8080)
├── frontend.html       # Web-Oberfläche (Touch-optimiert)
├── .env                # API-Credentials (NICHT committen!)
├── .gitignore          # Schützt die .env Datei
├── README.md           # Diese Datei
└── bambuddy-clearplate.service  # systemd Service für Autostart
```

## 🔧 Konfiguration

### Drucker anpassen

In der `frontend.html` kannst du die Drucker-Konfiguration ändern:

```javascript
const printerStates = {
    1: { status: 'idle', name: 'X1 Carbon #2' },
    2: { status: 'idle', name: 'X1 Carbon #1' },
    // ... weitere Drucker
};
```

### API-Endpoint ändern

In der `.env` Datei:

```bash
BAMBUDY_API_URL=https://deine-api-url.de/api/v1
```

## 🛠️ Troubleshooting

### Server startet nicht

```bash
# Logs prüfen
sudo journalctl -u bambuddy-clearplate -n 50

# Port prüfen (muss frei sein)
netstat -tlnp | grep 8080
```

### "Permission denied" bei systemd

```bash
# Service-Datei Rechte setzen
sudo chmod 644 /etc/systemd/system/bambuddy-clearplate.service
```

### API-Fehler

Die `.env` Datei muss korrekt sein:
```bash
cat .env
# Sollte enthalten: BAMBUDY_API_KEY=dein_key
```

## 🔒 Sicherheit

- **API-Credentials** bleiben auf dem Raspberry Pi, nie im Browser sichtbar
- **Keine externen Abhängigkeiten** — nur Python Standardbibliothek
- **Lokaler Zugriff** — Server hört nur auf `127.0.0.1` (localhost)

## 📝 Lizenz

MIT License - Frei für private und kommerzielle Nutzung

## 🤝 Mitwirken

Issues und Pull Requests willkommen!

---

**Erstellt mit ❤️ für die Bambu Lab Community**
