#!/usr/bin/env python3
"""
Test script per l'integrazione LogPPT + Ollama.
Verifica che il parsing locale funzioni correttamente.
"""

import sys
import time
from pathlib import Path

# Aggiungi il path per i moduli logppt
sys.path.append(str(Path(__file__).parent / "logppt"))

from logppt.models.logppt_ollama_client import LogPPTOllamaClient


def test_logppt_ollama_integration():
    """Test dell'integrazione LogPPT + Ollama."""
    
    print("🚀 Test integrazione LogPPT + Ollama")
    print("=" * 50)
    
    # Inizializza client
    client = LogPPTOllamaClient()
    
    # Test 1: Health Check
    print("\n1️⃣ Health Check Ollama...")
    if client.health_check():
        print("✅ Ollama è attivo")
    else:
        print("❌ Ollama non è attivo - verifica che il container sia in esecuzione")
        return False
    
    # Test 2: Lista Modelli
    print("\n2️⃣ Verifica modelli disponibili...")
    models = client.list_models()
    if models:
        print(f"✅ Modelli trovati: {len(models)}")
        for model in models:
            print(f"   - {model.get('name', 'N/A')} ({model.get('size', 'N/A')})")
    else:
        print("❌ Nessun modello trovato")
        return False
    
    # Test 3: Parsing Logs
    print("\n3️⃣ Test parsing logs...")
    
    # Log di test universali
    test_logs = [
        # Android
        "03-17 16:13:38.811 1702 2395 D WindowManager: test message",
        
        # Apache
        "192.168.1.100 - - [25/Dec/2023:10:30:45 +0100] \"GET /api/users/12345 HTTP/1.1\" 200 1456",
        
        # Linux Kernel
        "Dec 25 10:36:45 linux-server kernel: [12345.678901] CPU: 0 PID: 1234 comm: test_process"
    ]
    
    print(f"📝 Parsing {len(test_logs)} log di test...")
    
    # Parsing batch
    start_time = time.time()
    results = client.parse_logs_batch(test_logs)
    total_time = time.time() - start_time
    
    # Analisi risultati
    successful = [r for r in results if r.get("success", False)]
    failed = [r for r in results if not r.get("success", False)]
    
    print(f"\n📊 Risultati parsing:")
    print(f"   ✅ Successi: {len(successful)}")
    print(f"   ❌ Fallimenti: {len(failed)}")
    print(f"   ⏱️  Tempo totale: {total_time:.2f}s")
    
    # Mostra dettagli per ogni log
    for i, result in enumerate(results):
        print(f"\n📋 Log {i+1}: {result['original_log'][:50]}...")
        if result.get("success"):
            print(f"   Template: {result.get('template', 'N/A')}")
            print(f"   Tipo: {result.get('log_type', 'N/A')}")
            print(f"   Campi: {len(result.get('fields', {}))}")
            print(f"   Tempo: {result.get('response_time', 0):.3f}s")
        else:
            print(f"   ❌ Errore: {result.get('error', 'N/A')}")
    
    # Test 4: Salvataggio Risultati
    print("\n4️⃣ Salvataggio risultati...")
    output_file = "outputs/logppt_ollama_results.json"
    if client.save_results(results, output_file):
        print(f"✅ Risultati salvati in: {output_file}")
    else:
        print("❌ Errore nel salvare i risultati")
    
    # Test 5: Generazione Report
    print("\n5️⃣ Generazione report...")
    report = client.generate_report(results)
    print("📈 Report generato:")
    for key, value in report.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 50)
    print("🎉 Test completato!")
    
    return len(successful) == len(test_logs)


if __name__ == "__main__":
    try:
        success = test_logppt_ollama_integration()
        if success:
            print("✅ Tutti i test sono passati!")
            sys.exit(0)
        else:
            print("❌ Alcuni test sono falliti")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Errore durante i test: {e}")
        sys.exit(1)
