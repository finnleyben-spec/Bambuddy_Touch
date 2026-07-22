# Bambuddy Clear Plate Controller - Session Notes

## 📋 Zusammenfassung der Session

### Was wir gemacht haben:
- ✅ Bambu Studio API-Dokumentation studiert (Clear Plate Endpoint gefunden)
- ✅ Sichere Architektur mit lokalem Python Proxy-Server geplant
- ✅ Backend-Server (`backend.py`) erstellt - verbirgt API-Keys vor dem Browser
- ✅ Frontend-Seite (`frontend.html`) erstellt - schönes Design mit blinkenden Buttons
- ✅ `.env` Datei Template für API-Credentials erstellt (NICHT committen!)
- ✅ Setup-Skript (`setup.sh`) für einfache Installation auf Raspberry Pi

### Wichtige Erkenntnisse:
- **API Endpoint:** `POST /api/v1/printers/{printer_id}/clear-plate`
- **Drucker IDs:** 1 (X1C #2), 2 (X1C #1), 3 (X1C #3), 4 (H2D)
- **Sicherheit:** API-Keys dürfen NIE im Browser sichtbar sein!

---

## 📁 Projektstruktur

```
/home/finnley/bambuddy-clearplate/
├── .env              ← 🔐 API-Credentials (NICHT teilen!)
├── backend.py        ← Python Server (hat die Keys!)
├── frontend.html     ← Web-Interface (kein API-Key sichtbar)
├── setup.sh          ← Installationsskript für Raspberry Pi
└── SESSION_NOTES.md  ← Diese Datei
```

---

## 🔐 Konfiguration (.env)

```bash
# Erstelle .env manuell mit deinen Credentials!
cat > .env << 'EOF'
BAMBUDY_API_URL=https://DEINE-API-URL.de/api/v1
BAMBUDY_API_KEY=DEIN_API_KEY_HIER
EOF
```

**⚠️ WICHTIG:** Die `.env` Datei wird NICHT im Git gespeichert! Trage deinen API-Key manuell ein.

---

## 🚀 Installation auf Raspberry Pi

### Option 1: Setup-Skript verwenden (empfohlen)
```bash
# Vom PC mit Hermes kopieren:
scp /home/finnley/bambuddy-clearplate/setup.sh pi@RASPBERRY-IP:/tmp/

# Auf Raspberry Pi ausführen:
chmod +x /tmp/setup.sh
sudo bash /tmp/setup.sh

# Server starten:
cd /home/pi/bambuddy-clearplate
python3 backend.py &

# Browser öffnen:
```

### Option 2: Manuell kopieren
```bash
# Dateien einzeln auf Pi kopieren:
scp backend.py frontend.html pi@RASPBERRY-IP:/home/pi/bambuddy-clearplate/

# .env manuell erstellen (NICHT scp!)
ssh pi@RASPBERRY-IP
cd /home/pi/bambuddy-clearplate
nano .env  # Manuell eintragen!
```

---

## 🏠 Autostart mit systemd

```bash
# Service-Datei kopieren:
sudo cp bambuddy-clearplate.service /etc/systemd/system/

# Aktivieren und starten:
sudo systemctl daemon-reload
sudo systemctl enable --now bambuddy-clearplate

# Status prüfen:
sudo systemctl status bambuddy-clearplate
```

---

## 🔧 Technische Details

### Backend Architektur
- **Python HTTP Server** auf Port 8080
- **Proxy-Modus**: Frontend fragt lokalen Server → Server fragt Bambu API
- **Sicherheitsvorteil**: API-Key nie im Browser sichtbar!

### Frontend Features
- Responsive Design (funktioniert auf Handy + Desktop)
- Touch-optimierte Buttons für Raspberry Pi
- Animierter "Clear Plate" Button mit Blink-Effekt
- Modal-Dialog zur Bestätigung

---

## 🔗 Wichtige Links

- **API Endpoint:** `POST /api/v1/printers/{printer_id}/clear-plate`
- **Drucker IDs:** 1, 2, 3 (X1C), 4 (H2D)

---

## 💡 Tipps

### Server im Hintergrund starten:
```bash
python3 backend.py &
```

### Server stoppen:
```bash
# Finde die PID:
ps aux | grep backend.py

# Stoppe den Prozess:
kill <PID>
```

### Logs ansehen:
Der Python Server loggt alle API-Calls in die Konsole.

---

## 📞 Support

Bei Fragen oder Problemen:
1. Prüfe ob der Backend-Server läuft (`ps aux | grep backend.py`)
2. Prüfe die Logs im Terminal wo der Server gestartet wurde
3. Stelle sicher dass die `.env` Datei korrekt ist
4. Teste den API-Endpoint manuell mit curl

---

**Erstellt:** 2026-07-22  
**Status:** ✅ Bereit für Installation auf Raspberry Pi
