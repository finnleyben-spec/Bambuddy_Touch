#!/usr/bin/env python3
"""Test für Backend-Sicherheit (API-Key Schutz)"""

import urllib.request
import json
import sys

BASE_URL = "http://localhost:8080"
API_KEY = "bambuddy-local-key"  # Erwarteter Key

def test_without_key():
    """Test ohne API-Key (sollte fehlschlagen)"""
    print("🧪 Test 1: Anfrage OHNE API-Key...")
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/printers/1/status")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            print("❌ FEHLER: Anfrage ohne Key war erfolgreich (sollte fehlschlagen)")
            return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("✅ ERFOLG: Anfrage ohne Key wurde abgelehnt (HTTP 401)")
            return True
        else:
            print(f"❌ FEHLER: Unerwarteter HTTP-Status {e.code}")
            return False

def test_with_wrong_key():
    """Test mit falschem API-Key (sollte fehlschlagen)"""
    print("\n🧪 Test 2: Anfrage MIT FALSCHEM API-Key...")
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/printers/1/status")
        req.add_header('X-API-Key', 'falscher-key')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            print("❌ FEHLER: Anfrage mit falschem Key war erfolgreich (sollte fehlschlagen)")
            return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("✅ ERFOLG: Anfrage mit falschem Key wurde abgelehnt (HTTP 401)")
            return True
        else:
            print(f"❌ FEHLER: Unerwarteter HTTP-Status {e.code}")
            return False

def test_with_correct_key():
    """Test mit korrektem API-Key (sollte funktionieren)"""
    print("\n🧪 Test 3: Anfrage MIT KORREKTEM API-Key...")
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/printers/1/status")
        req.add_header('X-API-Key', API_KEY)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            print("✅ ERFOLG: Anfrage mit korrektem Key war erfolgreich")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("❌ FEHLER: Anfrage mit korrektem Key wurde abgelehnt (HTTP 401)")
            return False
        else:
            print(f"⚠️  HTTP-Status {e.code} - möglicherweise kein Drucker angeschlossen")
            # Das ist okay, wenn kein echter Drucker da ist
            return True

def test_frontend_load():
    """Test ob Frontend ohne Key geladen werden kann"""
    print("\n🧪 Test 4: Frontend laden (soll funktionieren)...")
    try:
        req = urllib.request.Request(f"{BASE_URL}/")
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode()
            if "Bambuddy" in content or "printer" in content.lower():
                print("✅ ERFOLG: Frontend wurde geladen")
                return True
            else:
                print("❌ FEHLER: Frontend enthält keine erwarteten Inhalte")
                return False
    except Exception as e:
        print(f"❌ FEHLER: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔒 Backend-Sicherheitstest")
    print("=" * 60)
    
    results = []
    results.append(("Ohne Key", test_without_key()))
    results.append(("Falscher Key", test_with_wrong_key()))
    results.append(("Korrekter Key", test_with_correct_key()))
    results.append(("Frontend laden", test_frontend_load()))
    
    print("\n" + "=" * 60)
    print("📊 Ergebnis:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 Alle Tests bestanden! Backend-Sicherheit funktioniert.")
    else:
        print("⚠️  Einige Tests fehlgeschlagen. Bitte prüfen.")
    print("=" * 60)