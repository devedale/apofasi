#!/usr/bin/env python3
"""
Test del vero approccio LogPPT usando RoBERTa direttamente.
Questo test segue l'implementazione originale di LogPPT.
"""

import sys
import os
sys.path.append('/app')

from logppt.models.logppt_parser import LogPPTParser

def test_real_logppt():
    """Test del parsing usando l'approccio LogPPT originale."""
    
    print("🚀 Test del Vero Approccio LogPPT")
    print("=" * 60)
    print("Obiettivo: Usare RoBERTa direttamente come nel codice originale")
    print("=" * 60)
    
    # Log di test universali
    test_logs = {
        "Android": [
            "03-17 16:13:38.811  1702  2395 D WindowManager: printFreezingDisplayLogsopening app wtoken = AppWindowToken{9f4ef63 token=Token{a64f992 ActivityRecord{de9231d u0 com.tencent.qt.qtl/.activity.info.NewsDetailXmlActivity t761}}}, allDrawn= false, startingDisplayed =  false, startingMoved =  false, isRelaunching =  false",
            "03-17 16:15:42.123  1899  3456 D ActivityManager: Starting activity com.example.app/.MainActivity"
        ],
        "Apache": [
            '192.168.1.100 - - [25/Dec/2023:10:30:45 +0100] "GET /api/users/12345 HTTP/1.1" 200 1456 "https://example.com" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"',
            '10.0.0.100 - - [25/Dec/2023:11:46:12 +0100] "GET /api/status HTTP/2.0" 200 89 "https://example.com/status" "curl/7.68.0"'
        ],
        "Linux": [
            'Dec 25 10:36:45 linux-server kernel: [12345.678901] CPU: 0 PID: 1234 at /path/to/kernel/module.c:123 function_name+0x45/0x67',
            'Dec 25 11:47:30 linux-server sshd[8901]: Accepted publickey for admin from 192.168.1.50 port 54321 ssh2'
        ]
    }
    
    try:
        # Inizializza il parser LogPPT originale
        print("📥 Inizializzazione del parser LogPPT...")
        parser = LogPPTParser(
            model_path="roberta-base",
            vtoken="<*>",
            use_crf=False
        )
        print("✅ Parser LogPPT inizializzato con successo!")
        
        # Test del parsing per ogni tipo di log
        all_results = []
        
        for log_type, logs in test_logs.items():
            print(f"\n🔍 Test per log {log_type}:")
            print("-" * 50)
            
            for i, log in enumerate(logs):
                print(f"\n📝 {log_type} Log {i+1}:")
                print(f"Originale: {log[:80]}...")
                
                try:
                    # Parsing usando l'approccio LogPPT originale
                    template = parser.parse_log(log, device="cpu")
                    print(f"✅ Template: {template}")
                    
                    all_results.append({
                        "success": True,
                        "log_type": log_type,
                        "original_log": log,
                        "template": template,
                        "index": i
                    })
                    
                except Exception as e:
                    print(f"❌ Errore: {e}")
                    all_results.append({
                        "success": False,
                        "log_type": log_type,
                        "original_log": log,
                        "error": str(e),
                        "index": i
                    })
        
        # Salva i risultati
        print(f"\n💾 Salvataggio dei risultati...")
        
        # Crea directory outputs se non esiste
        os.makedirs("/app/outputs", exist_ok=True)
        
        # Salva risultati del parsing
        results_file = "/app/outputs/real_logppt_results.json"
        if parser.save_results(all_results, results_file):
            print(f"✅ Risultati salvati in: {results_file}")
        else:
            print("❌ Errore nel salvare i risultati")
        
        # Genera report
        successful_parses = sum(1 for r in all_results if r.get("success", False))
        total_logs = len(all_results)
        
        print(f"\n" + "="*60)
        print("📊 RISULTATI FINALI DEL PARSING LOGPPT")
        print("="*60)
        print(f"✅ Log parsati con successo: {successful_parses}/{total_logs}")
        print(f"📈 Tasso di successo: {(successful_parses/total_logs)*100:.1f}%")
        print(f"🤖 Modello utilizzato: roberta-base")
        print(f"🎯 Virtual token: <*>")
        
        # Mostra dove sono salvati i file
        print(f"\n💾 File di output:")
        print(f"   - Risultati parsing: {results_file}")
        
        # Verifica che i file siano stati creati
        print(f"\n🔍 Verifica file di output:")
        if os.path.exists(results_file):
            size = os.path.getsize(results_file)
            print(f"   - {results_file}: {size} bytes")
        else:
            print(f"   - {results_file}: NON TROVATO")
        
        print(f"\n💡 Vantaggi dell'approccio LogPPT originale:")
        print(f"   1. ✅ Usa RoBERTa direttamente (no Ollama)")
        print(f"   2. ✅ Tokenizzazione intelligente con delimiters")
        print(f"   3. ✅ Parsing diretto senza pattern matching")
        print(f"   4. ✅ Virtual token <*> per i parametri")
        print(f"   5. ✅ Correzione automatica dei template")
        
    except Exception as e:
        print(f"❌ Errore critico: {e}")
        print("\n💡 Suggerimenti:")
        print("   - Verifica che transformers sia installato")
        print("   - Controlla la connessione internet per il modello")

if __name__ == "__main__":
    test_real_logppt()
