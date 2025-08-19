#!/usr/bin/env python3
"""
Test del parsing dei log usando Ollama e salvataggio dei risultati.
Questo test verifica l'integrazione con Ollama e salva tutti i risultati.
"""

import sys
import os
sys.path.append('/app')

from logppt.models.ollama_client import OllamaLogParser

def test_ollama_log_parsing():
    """Test del parsing dei log usando Ollama."""
    
    # Log di test universali (solo 1 per tipo per non sforzare troppo)
    test_logs = {
        "Android": [
            "03-17 16:13:38.811  1702  2395 D WindowManager: printFreezingDisplayLogsopening app wtoken = AppWindowToken{9f4ef63 token=Token{a64f992 ActivityRecord{de9231d u0 com.tencent.qt.qtl/.activity.info.NewsDetailXmlActivity t761}}}, allDrawn= false, startingDisplayed =  false, startingMoved =  false, isRelaunching =  false"
        ],
        "Apache": [
            '192.168.1.100 - - [25/Dec/2023:10:30:45 +0100] "GET /api/users/12345 HTTP/1.1" 200 1456 "https://example.com" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"'
        ],
        "Linux": [
            'Dec 25 10:36:45 linux-server kernel: [12345.678901] CPU: 0 PID: 1234 at /path/to/kernel/module.c:123 function_name+0x45/0x67'
        ]
    }
    
    print("🚀 Test del Parsing dei Log con Ollama")
    print("=" * 60)
    
    # Inizializza il parser Ollama
    parser = OllamaLogParser(
        base_url="http://ollama:11434",  # Usa il container Ollama
        model_name="roberta-log-parser"
    )
    
    # Verifica la connessione a Ollama
    print("🔍 Verifica connessione a Ollama...")
    if not parser.health_check():
        print("❌ Ollama non è raggiungibile!")
        print("💡 Verifica che il container Ollama sia attivo")
        return
    
    print("✅ Connessione a Ollama stabilita!")
    
    # Lista i modelli disponibili
    print("\n📋 Modelli disponibili in Ollama:")
    models = parser.list_models()
    if models:
        for model in models:
            print(f"   - {model.get('name', 'Unknown')} ({model.get('size', 'Unknown size')})")
    else:
        print("   Nessun modello trovato")
    
    # Test del parsing per ogni tipo di log
    all_results = []
    
    for log_type, logs in test_logs.items():
        print(f"\n🔍 Test per log {log_type}:")
        print("-" * 40)
        
        for i, log in enumerate(logs):
            print(f"\n📝 {log_type} Log {i+1}:")
            print(f"Originale: {log[:80]}...")
            
            # Parsing con Ollama
            result = parser.parse_log(log, f"Questo è un log {log_type}")
            
            if result.get("success"):
                print(f"✅ Template: {result['template'][:80]}...")
                print(f"   ⏱️  Tempo: {result.get('response_time', 0):.3f}s")
                print(f"   🎯 Token: {result.get('tokens_used', 0)}")
            else:
                print(f"❌ Errore: {result.get('error', 'Errore sconosciuto')}")
            
            all_results.append(result)
    
    # Salva i risultati
    print(f"\n💾 Salvataggio dei risultati...")
    
    # Crea directory outputs se non esiste
    os.makedirs("/app/outputs", exist_ok=True)
    
    # Salva risultati dettagliati
    results_file = "/app/outputs/ollama_parsing_results.json"
    if parser.save_results(all_results, results_file):
        print(f"✅ Risultati salvati in: {results_file}")
    else:
        print("❌ Errore nel salvare i risultati")
    
    # Genera e salva report
    report = parser.generate_report(all_results)
    report_file = "/app/outputs/ollama_parsing_report.json"
    if parser.save_results([report], report_file):
        print(f"✅ Report salvato in: {report_file}")
    else:
        print("❌ Errore nel salvare il report")
    
    # Mostra riepilogo
    print(f"\n" + "="*60)
    print("📊 RISULTATI FINALI")
    print("="*60)
    print(f"✅ Log parsati con successo: {report['summary']['successful_parses']}/{report['summary']['total_logs']}")
    print(f"📈 Tasso di successo: {report['summary']['success_rate']:.1f}%")
    print(f"⏱️  Tempo medio di risposta: {report['performance']['average_response_time']:.3f}s")
    print(f"🎯 Token totali utilizzati: {report['performance']['total_tokens']}")
    print(f"🤖 Modello utilizzato: {report['performance']['model_used']}")
    
    # Mostra dove sono salvati i file
    print(f"\n💾 File di output:")
    print(f"   - Risultati dettagliati: {results_file}")
    print(f"   - Report riassuntivo: {report_file}")
    
    # Verifica che i file siano stati creati
    print(f"\n🔍 Verifica file di output:")
    if os.path.exists(results_file):
        size = os.path.getsize(results_file)
        print(f"   - {results_file}: {size} bytes")
    else:
        print(f"   - {results_file}: NON TROVATO")
    
    if os.path.exists(report_file):
        size = os.path.getsize(report_file)
        print(f"   - {report_file}: {size} bytes")
    else:
        print(f"   - {report_file}: NON TROVATO")

if __name__ == "__main__":
    test_ollama_log_parsing()
