#!/usr/bin/env python3
"""
Test che dimostra come usare i template generati da Ollama per parsare nuovi log.
Questo test carica i template salvati e li usa per parsare nuovi log dello stesso tipo.
"""

import sys
import os
sys.path.append('/app')

from logppt.models.template_parser import TemplateLogParser

def test_template_usage():
    """Test dell'uso dei template per il parsing di nuovi log."""
    
    print("🚀 Test dell'Uso dei Template per il Parsing")
    print("=" * 60)
    print("Obiettivo: Usare i template generati da Ollama per parsare nuovi log")
    print("=" * 60)
    
    # Inizializza il parser dei template
    parser = TemplateLogParser()
    
    # Mostra riepilogo dei template caricati
    print("\n📋 Template caricati:")
    summary = parser.get_template_summary()
    print(f"   - Totale template: {summary['total_templates']}")
    print(f"   - Tipi supportati: {', '.join(summary['template_types'])}")
    
    # Log di test per ogni tipo (simili ma diversi da quelli usati per generare i template)
    test_logs = {
        "Android": [
            "03-17 16:15:42.123  1899  3456 D ActivityManager: Starting activity com.example.app/.MainActivity",
            "03-17 16:16:15.789  1899  4567 D PackageManager: Installing package com.test.app version 1.2.3"
        ],
        "Apache": [
            '192.168.1.200 - - [25/Dec/2023:11:45:30 +0100] "POST /api/upload HTTP/1.1" 201 234 "https://example.com/upload" "Mozilla/5.0 (Linux; x86_64) AppleWebKit/537.36"',
            '10.0.0.100 - - [25/Dec/2023:11:46:12 +0100] "GET /api/status HTTP/2.0" 200 89 "https://example.com/status" "curl/7.68.0"'
        ],
        "Linux": [
            'Dec 25 11:47:30 linux-server sshd[8901]: Accepted publickey for admin from 192.168.1.50 port 54321 ssh2',
            'Dec 25 11:48:45 linux-server kernel: [67890.123456] CPU: 1 PID: 5678 at /path/to/another/module.c:456 another_function+0x67/0x89'
        ]
    }
    
    # Test del parsing per ogni tipo
    all_results = []
    
    for log_type, logs in test_logs.items():
        print(f"\n🔍 Test parsing per log {log_type}:")
        print("-" * 50)
        
        for i, log in enumerate(logs):
            print(f"\n📝 {log_type} Log {i+1}:")
            print(f"Originale: {log[:80]}...")
            
            # Parsing usando i template
            result = parser.parse_log(log)
            
            if result.get("success"):
                print(f"✅ Parsing riuscito!")
                print(f"   🎯 Tipo: {result['log_type']}")
                print(f"   📋 Template usato: {result['template_used'][:60]}...")
                
                # Mostra i parametri estratti
                if result.get("parameters"):
                    print(f"   🔍 Parametri estratti:")
                    for key, value in result["parameters"].items():
                        print(f"      - {key}: {value}")
                else:
                    print(f"   ⚠️  Nessun parametro estratto")
                
                # Mostra metadata del template
                if result.get("metadata"):
                    print(f"   📊 Metadata template:")
                    print(f"      - Modello: {result['metadata'].get('model_used', 'N/A')}")
                    print(f"      - Tempo generazione: {result['metadata'].get('response_time', 0):.3f}s")
                    print(f"      - Token utilizzati: {result['metadata'].get('tokens_used', 0)}")
                
            else:
                print(f"❌ Parsing fallito: {result.get('error', 'Errore sconosciuto')}")
                if result.get("pattern"):
                    print(f"   🔍 Pattern tentato: {result['pattern']}")
            
            all_results.append(result)
    
    # Salva i risultati del parsing
    print(f"\n💾 Salvataggio dei risultati del parsing...")
    
    # Crea directory outputs se non esiste
    os.makedirs("/app/outputs", exist_ok=True)
    
    # Salva risultati del parsing
    parsing_results_file = "/app/outputs/template_parsing_results.json"
    if parser.save_parsing_results(all_results, parsing_results_file):
        print(f"✅ Risultati del parsing salvati in: {parsing_results_file}")
    else:
        print("❌ Errore nel salvare i risultati del parsing")
    
    # Genera e salva report
    successful_parses = sum(1 for r in all_results if r.get("success", False))
    total_logs = len(all_results)
    
    report = {
        "summary": {
            "total_logs": total_logs,
            "successful_parses": successful_parses,
            "failed_parses": total_logs - successful_parses,
            "success_rate": (successful_parses / total_logs * 100) if total_logs > 0 else 0
        },
        "template_usage": {
            "templates_loaded": summary["total_templates"],
            "template_types": summary["template_types"]
        },
        "results": all_results
    }
    
    report_file = "/app/outputs/template_parsing_report.json"
    if parser.save_parsing_results([report], report_file):
        print(f"✅ Report salvato in: {report_file}")
    else:
        print("❌ Errore nel salvare il report")
    
    # Mostra riepilogo finale
    print(f"\n" + "="*60)
    print("📊 RISULTATI FINALI DEL PARSING CON TEMPLATE")
    print("="*60)
    print(f"✅ Log parsati con successo: {successful_parses}/{total_logs}")
    print(f"📈 Tasso di successo: {report['summary']['success_rate']:.1f}%")
    print(f"🤖 Template utilizzati: {summary['total_templates']}")
    print(f"🎯 Tipi di log supportati: {len(summary['template_types'])}")
    
    # Mostra dove sono salvati i file
    print(f"\n💾 File di output:")
    print(f"   - Risultati parsing: {parsing_results_file}")
    print(f"   - Report riassuntivo: {report_file}")
    
    # Verifica che i file siano stati creati
    print(f"\n🔍 Verifica file di output:")
    if os.path.exists(parsing_results_file):
        size = os.path.getsize(parsing_results_file)
        print(f"   - {parsing_results_file}: {size} bytes")
    else:
        print(f"   - {parsing_results_file}: NON TROVATO")
    
    if os.path.exists(report_file):
        size = os.path.getsize(report_file)
        print(f"   - {report_file}: {size} bytes")
    else:
        print(f"   - {report_file}: NON TROVATO")
    
    print(f"\n💡 Come usare i template:")
    print(f"   1. I template sono stati generati da Ollama e salvati")
    print(f"   2. Il TemplateLogParser li carica automaticamente")
    print(f"   3. Nuovi log vengono classificati e parsati usando i template")
    print(f"   4. I parametri dinamici vengono estratti e strutturati")
    print(f"   5. I risultati sono salvati in formato JSON per uso successivo")

if __name__ == "__main__":
    test_template_usage()
