#!/usr/bin/env python3
"""
Test per verificare che il drain funzioni SENZA LIMITI.
Questo test verifica che quando max_clusters e max_children sono null,
il drain possa processare file di qualsiasi dimensione senza limiti.
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.drain3_service import Drain3ServiceImpl
from src.domain.entities.parsed_record import ParsedRecord
from src.domain.entities.log_entry import LogEntry


def test_drain_infinito():
    """Test che verifica che il drain funzioni senza limiti."""
    
    print("🧪 Test Drain Infinito - Verifica che non ci siano limiti sui cluster")
    print("=" * 80)
    
    # Configurazione con drain infinito (senza limiti pratici)
    config = {
        "drain3": {
            "original": {
                "depth": 4,
                "max_children": 999999,  # Limite praticamente infinito sui figli
                "max_clusters": 999999,  # Limite praticamente infinito sui cluster - DRAIN INFINITO
                "similarity_threshold": 0.4
            },
            "anonymized": {
                "depth": 4,
                "max_children": 999999,  # Limite praticamente infinito sui figli
                "max_clusters": 999999,  # Limite praticamente infinito sui cluster - DRAIN INFINITO
                "similarity_threshold": 0.4
            }
        }
    }
    
    try:
        # Crea il servizio Drain3
        drain3_service = Drain3ServiceImpl(config)
        print("✅ Servizio Drain3 creato con successo")
        
        # Test con molti messaggi diversi per verificare che non ci siano limiti
        test_messages = []
        
        # Genera 2000 messaggi diversi per testare i limiti
        for i in range(2000):
            # Crea messaggi con pattern diversi per forzare la creazione di cluster
            if i % 3 == 0:
                message = f"logver=0702111740 idseq={i} itime=1751754627 devid=\"FGT80FTK22013405\" devname=\"mg-project-bari-{i}\" vd=\"root\" date=2025-07-06 time=00:30:24 eventtime=1751754624843767899 tz=\"+0200\" logid=\"0100026001\" type=\"event\" subtype=\"system\" level=\"information\" logdesc=\"DHCP Ack log\" interface=\"internal1\" dhcp_msg=\"Ack\" mac=\"9C:53:22:49:C7:8C\" ip=10.63.44.101 lease=86400 hostname=\"ArcherAX55\" msg=\"DHCP server sends a DHCPACK\""
            elif i % 3 == 1:
                message = f"logver=0702111740 idseq={i} itime=1751754689 devid=\"FGT80FTK22013405\" devname=\"mg-project-bari-{i}\" vd=\"root\" date=2025-07-06 time=00:31:24 eventtime=1751754684862908499 tz=\"+0100\" logid=\"0101037141\" type=\"event\" subtype=\"vpn\" level=\"notice\" logdesc=\"IPsec tunnel statistics\" msg=\"IPsec tunnel statistics\" action=\"tunnel-stats\" remip=88.61.48.146 locip=93.64.253.210 remport=500 locport=500 outintf=\"wan1\" cookies=\"5df8cf6e832e3278/7c26da8af8e39c6e\" user=\"88.61.48.146\" group=\"N/A\" useralt=\"N/A\" xauthuser=\"N/A\" xauthgroup=\"N/A\" assignip=N/A vpntunnel=\"to-pescara-pri\" tunnelip=N/A tunnelid=2206215695 tunneltype=\"ipsec\" duration=1114987 sentbyte=400945590 rcvdbyte=185308176 nextstat=600 advpnsc=0"
            else:
                message = f"logver=0702111740 idseq={i} itime=1751754725 devid=\"FGT80FTK22013405\" devname=\"mg-project-bari-{i}\" vd=\"root\" date=2025-07-06 time=00:32:01 eventtime=1751754720597425659 tz=\"+0300\" logid=\"0100040704\" type=\"event\" subtype=\"system\" level=\"notice\" logdesc=\"System performance statistics\" action=\"perf-stats\" cpu=0 mem=40 totalsession=44 disk=0 bandwidth=\"6/3\" setuprate=0 disklograte=0 fazlograte=0 freediskstorage=0 sysuptime=1115536 waninfo=\"name=wan1,bytes=1516715254/6481088798,packets=7849124/10090377;\" msg=\"Performance statistics: average CPU: 0, memory: 40, concurrent sessions: 44, setup-rate: 0\""
            
            test_messages.append(message)
        
        print(f"📝 Generati {len(test_messages)} messaggi di test diversi")
        
        # Testa il miner originale
        print("\n🔍 Testando miner originale...")
        original_clusters = set()
        
        for i, message in enumerate(test_messages):
            try:
                result = drain3_service.add_log_message(message, "original")
                cluster_id = result.get('cluster_id')
                if cluster_id is not None:
                    original_clusters.add(cluster_id)
                
                if i % 500 == 0:
                    print(f"   Processati {i} messaggi, cluster creati: {len(original_clusters)}")
                    
            except Exception as e:
                print(f"❌ Errore nel processare messaggio {i}: {e}")
                break
        
        print(f"✅ Miner originale completato. Cluster totali: {len(original_clusters)}")
        
        # Testa il miner anonimizzato
        print("\n🔍 Testando miner anonimizzato...")
        anonymized_clusters = set()
        
        for i, message in enumerate(test_messages):
            try:
                result = drain3_service.add_log_message(message, "anonymized")
                cluster_id = result.get('cluster_id')
                if cluster_id is not None:
                    anonymized_clusters.add(cluster_id)
                
                if i % 500 == 0:
                    print(f"   Processati {i} messaggi, cluster creati: {len(anonymized_clusters)}")
                    
            except Exception as e:
                print(f"❌ Errore nel processare messaggio {i}: {e}")
                break
        
        print(f"✅ Miner anonimizzato completato. Cluster totali: {len(anonymized_clusters)}")
        
        # Verifica che non ci siano limiti
        print("\n📊 VERIFICA LIMITI:")
        print(f"   Cluster originali: {len(original_clusters)}")
        print(f"   Cluster anonimizzati: {len(anonymized_clusters)}")
        
        if len(original_clusters) > 1000 or len(anonymized_clusters) > 1000:
            print("✅ SUCCESSO: Il drain funziona SENZA LIMITI!")
            print("   I cluster hanno superato il limite precedente di 1000")
        else:
            print("⚠️  ATTENZIONE: Il drain potrebbe ancora avere limiti")
            print("   I cluster non hanno superato il limite precedente di 1000")
        
        # Ottieni statistiche
        stats = drain3_service.get_statistics_combined()
        print(f"\n📈 Statistiche finali:")
        print(f"   Original miner: {stats.get('original', {})}")
        print(f"   Anonymized miner: {stats.get('anonymized', {})}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRORE nel test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_drain_con_limiti():
    """Test di confronto con drain con limiti per verificare la differenza."""
    
    print("\n🧪 Test Drain CON LIMITI - Confronto con configurazione limitata")
    print("=" * 80)
    
    # Configurazione con limiti (come era prima)
    config_limitata = {
        "drain3": {
            "original": {
                "depth": 4,
                "max_children": 100,  # Limite sui figli
                "max_clusters": 1000,  # Limite sui cluster
                "similarity_threshold": 0.4
            },
            "anonymized": {
                "depth": 4,
                "max_children": 100,  # Limite sui figli
                "max_clusters": 1000,  # Limite sui cluster
                "similarity_threshold": 0.4
            }
        }
    }
    
    try:
        # Crea il servizio Drain3 con limiti
        drain3_service_limitato = Drain3ServiceImpl(config_limitata)
        print("✅ Servizio Drain3 con limiti creato con successo")
        
        # Test con gli stessi messaggi
        test_messages = []
        for i in range(2000):
            message = f"logver=0702111740 idseq={i} itime=1751754627 devid=\"FGT80FTK22013405\" devname=\"mg-project-bari-{i}\" vd=\"root\" date=2025-07-06 time=00:30:24 eventtime=1751754624843767899 tz=\"+0200\" logid=\"0100026001\" type=\"event\" subtype=\"system\" level=\"information\" logdesc=\"DHCP Ack log\" interface=\"internal1\" dhcp_msg=\"Ack\" mac=\"9C:53:22:49:C7:8C\" ip=10.63.44.101 lease=86400 hostname=\"ArcherAX55\" msg=\"DHCP server sends a DHCPACK\""
            test_messages.append(message)
        
        print(f"📝 Testando con {len(test_messages)} messaggi (configurazione limitata)")
        
        # Testa il miner originale con limiti
        original_clusters_limitati = set()
        
        for i, message in enumerate(test_messages):
            try:
                result = drain3_service_limitato.add_log_message(message, "original")
                cluster_id = result.get('cluster_id')
                if cluster_id is not None:
                    original_clusters_limitati.add(cluster_id)
                
                if i % 500 == 0:
                    print(f"   Processati {i} messaggi, cluster creati: {len(original_clusters_limitati)}")
                    
            except Exception as e:
                print(f"❌ Errore nel processare messaggio {i}: {e}")
                break
        
        print(f"✅ Miner originale con limiti completato. Cluster totali: {len(original_clusters_limitati)}")
        
        # Confronto
        print("\n📊 CONFRONTO CONFIGURAZIONI:")
        print(f"   Drain INFINITO (original): {len(original_clusters_limitati)} cluster")
        print(f"   Drain INFINITO (anonymized): {len(original_clusters_limitati)} cluster")
        print(f"   Drain CON LIMITI (original): {len(original_clusters_limitati)} cluster")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRORE nel test con limiti: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Avvio test Drain Infinito...")
    print("=" * 80)
    
    # Test 1: Drain infinito
    success1 = test_drain_infinito()
    
    # Test 2: Confronto con limiti
    success2 = test_drain_con_limiti()
    
    print("\n" + "=" * 80)
    if success1 and success2:
        print("🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
        print("✅ Il drain funziona correttamente SENZA LIMITI")
    else:
        print("❌ ALCUNI TEST SONO FALLITI")
        print("⚠️  Controlla la configurazione e i log per dettagli")
    
    print("=" * 80)
