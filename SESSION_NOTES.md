# Bambuddy Clear Plate Controller - Session Notes

## 📋 Zusammenfassung der Session

### Was wir gemacht haben:
- ✅ Bambuddy API-Dokumentation studiert (Clear Plate Endpoint gefunden)
- ✅ Sichere Architektur mit lokalem Python Proxy-Server geplant
- ✅ Backend-Server (`backend.py`) erstellt - verbirgt API-Keys vor dem Browser
- ✅ Frontend-Seite (`frontend.html`) erstellt - schönes Design mit blinkenden Buttons
- ✅ `.env` Datei mit API-Credentials erstellt
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
BAMBUDY_API_URL=https://bambu.kronos.hs-ruhrwest.de/api/v1
BAMBUDY_API_KEY=bb_2mtNCBXPxgm3TXwfhNZ7rjj-CUPn5kF9GVO7082fll4
```

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
chromium-browser --kiosk http://localhost:8080/
```

### Option 2: Dateien manuell erstellen
1. `.env` mit den API-Credentials erstellen
2. `backend.py` und `frontend.html` von diesem Verzeichnis kopieren
3. Server starten wie oben beschrieben

---

## 🎯 Funktionsweise

### Architektur:
```
Browser (Raspberry Pi)
    ↓ http://localhost:8080/
Python Backend (hat die API-Keys!)
    ↓ https://bambu.kronos.hs-ruhrwest.de/api/v1/printers/{id}/clear-plate
BamBuddy Server
```

### Features:
- ✅ 4 Drucker-Karten mit Echtzeit-Status
- ✅ Blinkende Buttons wenn Drucker idle ist
- ✅ Ausgegraute Buttons wenn Druck läuft (kann nicht gedrückt werden)
- ✅ Bestätigungs-Modal vor jeder Aktion
- ✅ API-Keys bleiben sicher auf dem Raspberry Pi
- ✅ Status-Updates alle 30 Sekunden

### Sicherheit:
- ❌ Keine API-Keys im HTML/JavaScript
- ❌ Kein "Rechtsklick -> Untersuchen" möglich
- ✅ Backend servert nur lokale Dateien
- ✅ API-Calls laufen über den Python Proxy
- ✅ Server läuft nur lokal (localhost:8080)

---

## 🐛 Bekannte Probleme & Lösungen

### Problem: "dotenv not installed"
**Lösung:** Das Skript hat einen Fallback für manuelles Laden der .env Datei.

### Problem: API gibt 404 zurück
**Mögliche Ursachen:**
- Falsche API-URL oder API-Key
- Drucker-ID existiert nicht
- Netzwerkproblem zum Bambuddy Server

### Problem: Button blinkt nicht
**Lösung:** Stelle sicher, dass der Status "idle" ist. Der Button blinkt nur wenn der Drucker bereit ist.

---

## 📝 Nächste Schritte (für nächste Session)

### 1. GitHub einrichten
- [ ] Git Repository erstellen
- [ ] `.env` Datei ausschließen (.gitignore)
- [ ] Code pushen

### 2. Raspberry Pi installieren
- [ ] Setup-Skript auf Raspberry Pi kopieren
- [ ] Server starten und testen
- [ ] Browser im Kiosk-Modus öffnen

### 3. Optional: systemd Service
- [ ] Automatischen Start beim Boot einrichten
- [ ] Service als Systemd-Daemon konfigurieren

---

## 🔗 Wichtige Links

- **BamBuddy API Docs:** https://bambu.kronos.hs-ruhrwest.de/docs
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
