#!/usr/bin/env python3
"""Stresstest für die Polling-Optimierung"""

import time
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8080/api"
PRINTER_IDS = [1, 2, 3, 4]

def test_single_printer(printer_id):
    """Testet einen einzelnen Drucker"""
    start = time.time()
    try:
        url = f"{BASE_URL}/printers/{printer_id}/status"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            elapsed = (time.time() - start) * 1000
            return {
                "id": printer_id,
                "success": True,
                "time_ms": round(elapsed, 2),
                "state": data.get("state", "unknown")
            }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {
            "id": printer_id,
            "success": False,
            "error": str(e),
            "time_ms": round(elapsed, 2)
        }

def test_parallel_polling():
    """Testet paralleles Polling wie im Frontend"""
    print("\n🔄 Test: Paralleles Polling (Promise.all)")
    
    start = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(test_single_printer, pid): pid for pid in PRINTER_IDS}
        
        results = []
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    total_time = (time.time() - start) * 1000
    
    print(f"   Zeit: {total_time:.2f}ms")
    print(f"   Drucker: {len(results)} abgefragt")
    
    success_count = sum(1 for r in results if r["success"])
    error_count = len(results) - success_count
    
    print(f"   ✅ Erfolg: {success_count}/{len(results)}")
    if error_count > 0:
        print(f"   ❌ Fehler: {error_count}")
        for r in results:
            if not r["success"]:
                print(f"      Drucker {r['id']}: {r['error']}")
    
    return total_time, success_count == len(results)

def test_rapid_polling(iterations=10):
    """Testet schnelles wiederholtes Polling"""
    print(f"\n🔄 Test: Schnelles Polling ({iterations}x)")
    
    times = []
    errors = 0
    
    for i in range(iterations):
        start = time.time()
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(test_single_printer, pid) for pid in PRINTER_IDS]
                results = [f.result() for f in futures]
            
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            if any(not r["success"] for r in results):
                errors += 1
                
        except Exception as e:
            errors += 1
            print(f"   ❌ Iteration {i+1}: {e}")
    
    avg_time = sum(times) / len(times) if times else 0
    max_time = max(times) if times else 0
    
    print(f"   Durchschnitt: {avg_time:.2f}ms")
    print(f"   Maximal: {max_time:.2f}ms")
    print(f"   Fehler: {errors}/{iterations}")
    
    return avg_time, errors == 0

def test_concurrent_load():
    """Testet gleichzeitige Last von mehreren Clients"""
    print("\n🔄 Test: Gleichzeitige Last (5 parallele Polling-Zyklen)")
    
    start = time.time()
    
    def poll_cycle():
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(test_single_printer, pid) for pid in PRINTER_IDS]
            return [f.result() for f in futures]
    
    # 5 parallele Polling-Zyklen starten
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(poll_cycle) for _ in range(5)]
        
        all_results = []
        for future in as_completed(futures):
            results = future.result()
            all_results.extend(results)
    
    total_time = (time.time() - start) * 1000
    
    success_count = sum(1 for r in all_results if r["success"])
    error_count = len(all_results) - success_count
    
    print(f"   Gesamtzeit: {total_time:.2f}ms")
    print(f"   Requests: {len(all_results)}")
    print(f"   ✅ Erfolg: {success_count}/{len(all_results)}")
    
    return total_time, error_count == 0

def main():
    print("=" * 60)
    print("🧪 Bambuddy Touch - Polling Stresstest")
    print("=" * 60)
    
    # Test 1: Einzelne parallele Abfrage
    time1, ok1 = test_parallel_polling()
    
    # Test 2: Schnelles wiederholtes Polling
    time2, ok2 = test_rapid_polling(iterations=10)
    
    # Test 3: Gleichzeitige Last
    time3, ok3 = test_concurrent_load()
    
    print("\n" + "=" * 60)
    print("📊 Ergebnis:")
    print("=" * 60)
    print(f"✅ Paralleles Polling: {'ERFOLG' if ok1 else 'FEHLER'} ({time1:.2f}ms)")
    print(f"✅ Schnelles Polling: {'ERFOLG' if ok2 else 'FEHLER'} (Ø {time2:.2f}ms)")
    print(f"✅ Gleichzeitige Last: {'ERFOLG' if ok3 else 'FEHLER'} ({time3:.2f}ms)")
    
    all_ok = ok1 and ok2 and ok3
    print("\n" + ("🎉 Alle Tests bestanden!" if all_ok else "❌ Einige Tests fehlgeschlagen"))
    print("=" * 60)

if __name__ == "__main__":
    main()