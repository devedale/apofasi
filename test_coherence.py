#!/usr/bin/env python3
"""
Test per verificare la coerenza tra template anonimizzati e messaggi anonimizzati.

DESIGN: Verifica che il sistema centralizzato generi template coerenti
con l'anonimizzazione applicata ai messaggi.
"""

import sys
import os
from pathlib import Path

# Aggiungi il percorso src al Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from domain.services.centralized_regex_service import CentralizedRegexServiceImpl
    from domain.entities.parsed_record import ParsedRecord
    from infrastructure.drain3_service import Drain3ServiceImpl
    print("✅ Import completati con successo")
except ImportError as e:
    print(f"❌ Errore import: {e}")
    print("Verifica che tutti i file siano presenti e gli import siano corretti")
    sys.exit(1)


def test_template_coherence():
    """Testa la coerenza tra template anonimizzati e messaggi anonimizzati."""
    print("🧪 Test Coerenza Template Anonimizzati")
    print("=" * 50)
    
    # Configurazione di test
    config = {
        "centralized_regex": {
            "generate_anonymized_templates": True
        },
        "drain3": {
            "original": {"depth": 4, "max_children": 100, "max_clusters": 1000, "similarity_threshold": 0.4},
            "anonymized": {"depth": 4, "max_children": 100, "max_clusters": 1000, "similarity_threshold": 0.4}
        }
    }
    
    # Inizializza servizi
    regex_service = CentralizedRegexServiceImpl(config)
    drain3_service = Drain3ServiceImpl(config)
    
    # Messaggio di test Fortinet
    test_message = 'logver=0702111740 idseq=19900372806008868 itime=1751754739 devid="FGT80FTK22013405" devname="mg-project-bari" vd="root" date=2025-07-06 time=00:32:15 eventtime=1751754735214176279 tz="+0200" logid="0100026001" type="event" subtype="system" level="information" logdesc="DHCP Ack log" interface="internal1" dhcp_msg="Ack" mac="9C:53:22:49:C7:8C" ip=10.63.44.101 lease=86400 hostname="ArcherAX55" msg="DHCP server sends a DHCPACK"'
    
    print(f"📝 Messaggio Originale:")
    print(f"   {test_message}")
    print()
    
    # Test 1: Anonimizzazione diretta
    print("🔒 Test 1: Anonimizzazione Diretta")
    anonymized_message = regex_service.anonymize_content(test_message)
    print(f"   Messaggio Anonimizzato:")
    print(f"   {anonymized_message}")
    print()
    
    # Test 2: Template generato dal contenuto originale
    print("📋 Test 2: Template dal Contenuto Originale")
    original_template = regex_service.get_template_from_content(test_message, anonymized=False)
    print(f"   Template Originale:")
    print(f"   {original_template}")
    print()
    
    # Test 3: Template generato dal contenuto anonimizzato
    print("🔒📋 Test 3: Template dal Contenuto Anonimizzato")
    anonymized_template = regex_service.get_template_from_content(test_message, anonymized=True)
    print(f"   Template Anonimizzato:")
    print(f"   {anonymized_template}")
    print()
    
    # Test 4: Pattern detection
    print("🔍 Test 4: Pattern Detection")
    detected_patterns = regex_service.detect_patterns(test_message)
    print(f"   Pattern Rilevati:")
    for pattern_type, matches in detected_patterns.items():
        print(f"     {pattern_type}: {matches}")
    print()
    
    # Test 5: Creazione record e processamento Drain3
    print("🔄 Test 5: Processamento Record Completo")
    
    # Crea un record di test
    test_record = ParsedRecord(
        original_content=test_message,
        parsed_data={"line_number": 1},
        parser_name="test_parser",
        source_file=Path("test.log"),
        line_number=1,
        anonymized_template=anonymized_template  # Template anonimizzato coerente
    )
    
    # Processa con Drain3
    processed_record = drain3_service.process_record(test_record)
    
    print(f"   Record Processato:")
    print(f"     Template Originale: {processed_record.template}")
    print(f"     Template Anonimizzato: {processed_record.anonymized_template}")
    
    if "drain3_original" in processed_record.parsed_data:
        orig_info = processed_record.parsed_data["drain3_original"]
        print(f"     Drain3 Originale - Cluster ID: {orig_info.get('cluster_id')}, Size: {orig_info.get('cluster_size')}")
    
    if "drain3_anonymized" in processed_record.parsed_data:
        anon_info = processed_record.parsed_data["drain3_anonymized"]
        print(f"     Drain3 Anonimizzato - Cluster ID: {anon_info.get('cluster_id')}, Size: {anon_info.get('cluster_size')}")
    
    print()
    
    # Test 6: Verifica Coerenza
    print("✅ Test 6: Verifica Coerenza")
    
    # Verifica che il template anonimizzato sia coerente con il messaggio anonimizzato
    template_anonymized = anonymized_template
    message_anonymized = anonymized_message
    
    # Controlla che i pattern anonimizzati siano presenti in entrambi
    coherence_issues = []
    
    # Verifica IP
    if "<IP>" in template_anonymized and "<IP>" in message_anonymized:
        print("   ✅ IP anonimizzato coerente")
    else:
        coherence_issues.append("IP anonimizzazione incoerente")
    
    # Verifica MAC
    if "<MAC>" in template_anonymized and "<MAC>" in message_anonymized:
        print("   ✅ MAC anonimizzato coerente")
    else:
        coherence_issues.append("MAC anonimizzazione incoerente")
    
    # Verifica Device ID
    if "<FORTINET_DEVICE>" in template_anonymized and "<FORTINET_DEVICE>" in message_anonymized:
        print("   ✅ Device ID anonimizzato coerente")
    else:
        coherence_issues.append("Device ID anonimizzazione incoerente")
    
    # Verifica Hostname
    if "<HOSTNAME>" in template_anonymized and "<HOSTNAME>" in message_anonymized:
        print("   ✅ Hostname anonimizzato coerente")
    else:
        coherence_issues.append("Hostname anonimizzazione incoerente")
    
    if coherence_issues:
        print(f"   ❌ Problemi di coerenza rilevati:")
        for issue in coherence_issues:
            print(f"      - {issue}")
    else:
        print("   🎉 Tutti i pattern sono coerenti!")
    
    print()
    
    # Test 7: Statistiche Drain3
    print("📊 Test 7: Statistiche Drain3")
    stats = drain3_service.get_statistics()
    print(f"   Statistiche Originale: {stats.get('original', {})}")
    print(f"   Statistiche Anonimizzato: {stats.get('anonymized', {})}")
    
    print()
    print("🏁 Test Completato!")


if __name__ == "__main__":
    test_template_coherence()
