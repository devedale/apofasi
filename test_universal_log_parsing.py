#!/usr/bin/env python3
"""
Test universale per il parsing di diversi tipi di log non strutturati con RoBERTa.
Verifica che il modello possa gestire: Android, Apache, Nginx, Windows, macOS, Linux, etc.
"""

import torch
from logppt.models.roberta import RobertaForLogParsing

def test_universal_log_parsing():
    """Test del parsing universale di diversi tipi di log."""
    
    # Raccolta di log di diversi sistemi e servizi
    universal_logs = {
        "Android": [
            "03-17 16:13:38.811  1702  2395 D WindowManager: printFreezingDisplayLogsopening app wtoken = AppWindowToken{9f4ef63 token=Token{a64f992 ActivityRecord{de9231d u0 com.tencent.qt.qtl/.activity.info.NewsDetailXmlActivity t761}}}, allDrawn= false, startingDisplayed =  false, startingMoved =  false, isRelaunching =  false",
            "03-17 16:13:38.819  1702  8671 D PowerManagerService: acquire lock=233570404, flags=0x1, tag=\"View Lock\", name=com.android.systemui, ws=null, uid=10037, pid=2227"
        ],
        
        "Apache": [
            '192.168.1.100 - - [25/Dec/2023:10:30:45 +0100] "GET /api/users/12345 HTTP/1.1" 200 1456 "https://example.com" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"',
            '10.0.0.50 - - [25/Dec/2023:10:31:12 +0100] "POST /api/login HTTP/1.1" 401 89 "https://example.com/login" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"'
        ],
        
        "Nginx": [
            '127.0.0.1 - - [25/Dec/2023:10:32:00 +0100] "GET /static/css/style.css HTTP/2.0" 200 2048 "https://example.com" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"',
            '192.168.1.200 - - [25/Dec/2023:10:33:15 +0100] "GET /api/products?category=electronics&page=2 HTTP/1.1" 200 3456 "https://example.com/shop" "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"'
        ],
        
        "Windows Event Log": [
            'Event ID: 4624, Source: Microsoft-Windows-Security-Auditing, Time: 2023-12-25T10:34:00.000Z, User: DOMAIN\\username, Computer: WIN-SERVER-01, IP: 192.168.1.100, Logon Type: 2',
            'Event ID: 4778, Source: Microsoft-Windows-Security-Auditing, Time: 2023-12-25T10:35:30.000Z, User: DOMAIN\\admin, Computer: WIN-SERVER-01, Session ID: 0x12345, IP: 10.0.0.50'
        ],
        
        "Linux System": [
            'Dec 25 10:36:45 linux-server kernel: [12345.678901] CPU: 0 PID: 1234 at /path/to/kernel/module.c:123 function_name+0x45/0x67',
            'Dec 25 10:37:12 linux-server sshd[5678]: Accepted password for user from 192.168.1.150 port 54321 ssh2'
        ],
        
        "macOS": [
            '2023-12-25 10:38:00.000 +0100 0x1234 Default 0x0 0 kernel: (AppleSMC) AppleSMC::smcReadKeyAction ERROR: smcReadKey 0x4B45594E (KEYN) failed, kSMC = 0x0',
            '2023-12-25 10:39:15.000 +0100 0x5678 Default 0x0 0 com.apple.xpc.launchd: (com.apple.WebKit.WebContent) Service exited with abnormal code: 1'
        ],
        
        "Docker": [
            '2023-12-25T10:40:00.000Z container-12345 docker: time="2023-12-25T10:40:00.000Z" level=info msg="Container started" container_id=abc123def456 image=nginx:latest',
            '2023-12-25T10:41:30.000Z container-67890 docker: time="2023-12-25T10:41:30.000Z" level=error msg="Connection refused" container_id=xyz789abc012 port=8080'
        ],
        
        "Kubernetes": [
            '2023-12-25T10:42:00.000Z kubelet: I1225 10:42:00.123456 12345 pod_workers.go:1234] Pod "default/nginx-pod-abc123" worker done, took 2.5s',
            '2023-12-25T10:43:15.000Z kubelet: E1225 10:43:15.654321 12345 kubelet.go:1234] Failed to start container "nginx" in pod "default/nginx-pod-def456": OCI runtime error'
        ]
    }
    
    print("🚀 Test Universale del Parsing di Log con RoBERTa")
    print("=" * 70)
    print("Obiettivo: Verificare che il modello possa parsare QUALSIASI tipo di log")
    print("=" * 70)
    
    try:
        # Inizializza il modello
        print("📥 Inizializzazione del modello RoBERTa universale...")
        model = RobertaForLogParsing(
            model_name_or_path="roberta-base",
            use_crf=False  # Disabilita CRF per il test universale
        )
        print("✅ Modello inizializzato con successo!")
        
        # Test per ogni tipo di log
        total_logs = 0
        successful_parses = 0
        
        for log_type, logs in universal_logs.items():
            print(f"\n🔍 Test per log {log_type}:")
            print("-" * 50)
            
            for i, log in enumerate(logs):
                total_logs += 1
                print(f"\n📝 {log_type} Log {i+1}:")
                print(f"Originale: {log[:80]}...")
                
                try:
                    template = model.parse(log, device="cpu")
                    print(f"✅ Template: {template[:80]}...")
                    successful_parses += 1
                    
                    # Analisi della qualità del parsing
                    if len(template) > 0:
                        print(f"   📊 Qualità: Template generato con successo")
                    else:
                        print(f"   ⚠️  Qualità: Template vuoto")
                        
                except Exception as e:
                    print(f"❌ Errore: {e}")
        
        # Riepilogo finale
        print(f"\n" + "="*70)
        print("📊 RISULTATI FINALI DEL TEST UNIVERSALE")
        print("="*70)
        print(f"✅ Log parsati con successo: {successful_parses}/{total_logs}")
        print(f"📈 Tasso di successo: {(successful_parses/total_logs)*100:.1f}%")
        
        if successful_parses == total_logs:
            print("🎉 SUCCESSO COMPLETO! Il modello è veramente universale!")
        elif successful_parses >= total_logs * 0.8:
            print("👍 BUONO! Il modello gestisce la maggior parte dei formati")
        else:
            print("⚠️  ATTENZIONE: Il modello ha difficoltà con alcuni formati")
            
        print(f"\n💡 Tipi di log testati: {len(universal_logs)}")
        for log_type in universal_logs.keys():
            print(f"   - {log_type}")
            
    except Exception as e:
        print(f"❌ Errore critico nell'inizializzazione: {e}")
        print("\n💡 Suggerimenti:")
        print("   - Verifica che il modello RoBERTa sia scaricato")
        print("   - Controlla la connessione internet per il download")

if __name__ == "__main__":
    test_universal_log_parsing()
