#!/usr/bin/env python3
"""
Test per il dual mining Drain3 (messaggi originali + anonimizzati).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

# Import locali
import sys
sys.path.append('src')

from infrastructure.drain3_service import Drain3ServiceImpl
from domain.entities.parsed_record import ParsedRecord


def test_dual_drain3_mining():
    """Test del dual mining con messaggi originali e anonimizzati."""
    
    # Configurazione di test
    config = {
        "drain3": {
            "depth": 4,
            "max_children": 100,
            "max_clusters": 1000,
            "similarity_threshold": 0.4
        }
    }
    
    # Crea il servizio Drain3
    drain3_service = Drain3ServiceImpl(config)
    
    # Messaggi di test (simili ma con valori diversi)
    test_messages = [
        "logver=1.0 idseq=123 itime=2024-01-01 devid=\"FGT123\" devname=\"Firewall1\" srcip=192.168.1.100 dstip=10.0.0.50",
        "logver=1.0 idseq=124 itime=2024-01-01 devid=\"FGT123\" devname=\"Firewall1\" srcip=192.168.1.101 dstip=10.0.0.51",
        "logver=1.0 idseq=125 itime=2024-01-01 devid=\"FGT123\" devname=\"Firewall1\" srcip=192.168.1.102 dstip=10.0.0.52",
        "logver=1.0 idseq=126 itime=2024-01-01 devid=\"FGT456\" devname=\"Firewall2\" srcip=192.168.2.100 dstip=10.0.1.50",
        "logver=1.0 idseq=127 itime=2024-01-01 devid=\"FGT456\" devname=\"Firewall2\" srcip=192.168.2.101 dstip=10.0.1.51"
    ]
    
    print("🧪 Testando dual mining Drain3...")
    print(f"📝 Messaggi di test: {len(test_messages)}")
    
    # Test 1: Mining sui messaggi originali
    print("\n🔍 Test 1: Mining sui messaggi originali")
    original_clusters = {}
    
    for i, message in enumerate(test_messages):
        cluster_id = drain3_service.add_log_message(message, "original")
        template = drain3_service.get_template(cluster_id, "original")
        cluster_info = drain3_service.get_cluster_info(cluster_id, "original")
        
        print(f"   Messaggio {i+1}: Cluster {cluster_id}, Template: {template[:50]}...")
        original_clusters[cluster_id] = cluster_info
    
    # Test 2: Mining sui messaggi anonimizzati
    print("\n🔒 Test 2: Mining sui messaggi anonimizzati")
    anonymized_clusters = {}
    
    for i, message in enumerate(test_messages):
        cluster_id = drain3_service.add_log_message(message, "anonymized")
        template = drain3_service.get_template(cluster_id, "anonymized")
        cluster_info = drain3_service.get_cluster_info(cluster_id, "anonymized")
        
        print(f"   Messaggio {i+1}: Cluster {cluster_id}, Template: {template[:50]}...")
        anonymized_clusters[cluster_id] = cluster_info
    
    # Test 3: Statistiche combinate
    print("\n📊 Test 3: Statistiche combinate")
    stats = drain3_service.get_statistics()
    print(f"   Cluster originali: {stats['original']['total_clusters']}")
    print(f"   Cluster anonimizzati: {stats['anonymized']['total_clusters']}")
    print(f"   Totale combinato: {stats['combined']['total_clusters']}")
    
    # Test 4: Template combinati
    print("\n🔗 Test 4: Template combinati")
    all_templates = drain3_service.get_all_templates_combined()
    print(f"   Template originali: {len(all_templates['original'])}")
    print(f"   Template anonimizzati: {len(all_templates['anonymized'])}")
    
    # Test 5: Processamento record completo
    print("\n📋 Test 5: Processamento record completo")
    test_record = ParsedRecord(
        original_content=test_messages[0],
        parsed_data={},
        parser_name="test",
        source_file="test.log",
        line_number=1
    )
    
    processed_record = drain3_service.process_record(test_record)
    
    print(f"   Record originale cluster ID: {processed_record.parsed_data.get('drain3_original', {}).get('cluster_id')}")
    print(f"   Record anonimizzato cluster ID: {processed_record.parsed_data.get('drain3_anonymized', {}).get('cluster_id')}")
    
    # Test 6: Salvataggio e caricamento stato
    print("\n💾 Test 6: Salvataggio e caricamento stato")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp_file:
        state_path = tmp_file.name
    
    try:
        # Salva stato
        drain3_service.save_state(state_path)
        print(f"   Stato salvato in: {state_path}")
        
        # Crea nuovo servizio e carica stato
        new_drain3_service = Drain3ServiceImpl(config)
        new_drain3_service.load_state(state_path)
        
        # Verifica che i template siano stati caricati
        new_stats = new_drain3_service.get_statistics()
        print(f"   Stato caricato - Cluster originali: {new_stats['original']['total_clusters']}")
        print(f"   Stato caricato - Cluster anonimizzati: {new_stats['anonymized']['total_clusters']}")
        
    finally:
        # Pulisci file temporanei
        Path(state_path + "_original").unlink(missing_ok=True)
        Path(state_path + "_anonymized").unlink(missing_ok=True)
    
    print("\n✅ Test dual mining Drain3 completato con successo!")
    
    return {
        "original_clusters": len(original_clusters),
        "anonymized_clusters": len(anonymized_clusters),
        "stats": stats
    }


def test_drain3_integration():
    """Test dell'integrazione con il sistema di parsing."""
    
    print("\n🔧 Test integrazione Drain3 con sistema di parsing...")
    
    # Simula un record parsato
    config = {"drain3": {"depth": 4, "max_children": 100, "max_clusters": 1000, "similarity_threshold": 0.4}}
    drain3_service = Drain3ServiceImpl(config)
    
    # Record di test
    test_record = ParsedRecord(
        original_content="logver=1.0 idseq=123 itime=2024-01-01 devid=\"FGT123\" srcip=192.168.1.100 dstip=10.0.0.50",
        parsed_data={"parser_name": "test_parser"},
        parser_name="test_parser",
        source_file="test.log",
        line_number=1
    )
    
    # Processa con Drain3
    processed_record = drain3_service.process_record(test_record)
    
    # Verifica risultati
    assert "drain3_original" in processed_record.parsed_data
    assert "drain3_anonymized" in processed_record.parsed_data
    assert "drain3_cluster_id" in processed_record.parsed_data  # Compatibilità
    
    print("   ✅ Integrazione funzionante")
    print(f"   📊 Dati originali: {processed_record.parsed_data['drain3_original']}")
    print(f"   📊 Dati anonimizzati: {processed_record.parsed_data['drain3_anonymized']}")


if __name__ == "__main__":
    print("🚀 Avvio test dual mining Drain3...")
    
    try:
        # Test principale
        results = test_dual_drain3_mining()
        
        # Test integrazione
        test_drain3_integration()
        
        print(f"\n🎯 Risultati finali:")
        print(f"   Cluster originali: {results['original_clusters']}")
        print(f"   Cluster anonimizzati: {results['anonymized_clusters']}")
        print(f"   Totale: {results['stats']['combined']['total_clusters']}")
        
        print("\n🎉 Tutti i test sono passati con successo!")
        
    except Exception as e:
        print(f"\n❌ Errore durante i test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
