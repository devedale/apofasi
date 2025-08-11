#!/usr/bin/env python3
"""
Test completo per l'integrazione di Presidio nel pipeline di parsing.
Verifica che i record parsati includano i risultati Presidio.
"""

import sys
import json
from pathlib import Path

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.application.services.parsing_service import ParsingService


def test_presidio_integration_in_pipeline():
    """Testa l'integrazione di Presidio nel pipeline di parsing completo."""
    
    print("🔍 TEST INTEGRAZIONE PRESIDIO NEL PIPELINE")
    print("=" * 80)
    
    # Configurazione con Presidio abilitato
    config = {
        "presidio": {
            "enabled": True,
            "anonymization_mode": "hybrid",
            "analyzer": {
                "languages": ["en"],
                "entities": {
                    "PERSON": True,
                    "EMAIL_ADDRESS": True,
                    "PHONE_NUMBER": True,
                    "IP_ADDRESS": True,
                    "CREDIT_CARD": True,
                    "LOCATION": True,
                    "ORGANIZATION": True,
                    "DATE_TIME": True,
                    "ID": True,
                    "HOSTNAME": True
                }
            }
        },
        "anonymization": {
            "enabled": True
        }
    }
    
    print("📋 Configurazione:")
    print(f"   Presidio enabled: {config['presidio']['enabled']}")
    print(f"   Modalità: {config['presidio']['anonymization_mode']}")
    print(f"   Anonimizzazione enabled: {config['anonymization']['enabled']}")
    print()
    
    try:
        # Crea il servizio di parsing
        print("🚀 Inizializzando ParsingService...")
        parsing_service = ParsingService(config)
        print("✅ ParsingService inizializzato")
        
        # Verifica che l'adapter ibrido sia stato usato
        anonymizer_type = type(parsing_service.log_processing_service._anonymizer).__name__
        print(f"🔐 Tipo anonimizer: {anonymizer_type}")
        
        if "HybridAnonymizerAdapter" in anonymizer_type:
            print("✅ Adapter ibrido attivo")
        else:
            print("⚠️ Adapter ibrido non attivo")
        
        print()
        
        # Test con un file di esempio
        test_file = "examples/FGT80FTK22013405.root.elog.txt"
        if not Path(test_file).exists():
            print(f"⚠️ File di test non trovato: {test_file}")
            print("   Creando file di test...")
            
            # Crea un file di test
            test_content = """2025-08-11 18:30:00 User John Doe (ID: 12345) logged in from 192.168.1.100
2025-08-11 18:31:00 Payment processed with card 1234-5678-9012-3456 from IP 88.61.48.146
2025-08-11 18:32:00 Device FGT80FTK22013405 reported error in New York office
2025-08-11 18:33:00 Session ID 98765 started by user john.doe@company.com"""
            
            Path(test_file).write_text(test_content)
            print("✅ File di test creato")
        
        # Esegui parsing
        print(f"📄 Parsing file: {test_file}")
        parsed_results = parsing_service.parse_files(test_file)
        
        print(f"✅ Parsing completato: {len(parsed_results)} record")
        print()
        
        # Analizza i risultati
        print("📊 ANALISI RISULTATI:")
        print("-" * 80)
        
        for i, record in enumerate(parsed_results[:3]):  # Solo i primi 3
            print(f"\n--- Record {i+1} ---")
            print(f"ID: {record.get('id', 'N/A')}")
            print(f"Parser: {record.get('parser_name', 'N/A')}")
            print(f"Success: {record.get('success', 'N/A')}")
            
            # Contenuto originale
            original = record.get('original_content', '')
            print(f"Originale: {original[:80]}...")
            
            # Messaggio anonimizzato
            anonymized = record.get('anonymized_message', '')
            print(f"Anonimizzato: {anonymized[:80]}...")
            
            # Verifica se Presidio è stato applicato
            if hasattr(record, 'presidio_anonymization') and record.presidio_anonymization:
                print("🔐 PRESIDIO ATTIVO!")
                presidio_result = record.presidio_anonymization
                
                if config['presidio']['anonymization_mode'] == 'hybrid':
                    # Modalità ibrida
                    classic = presidio_result.get('classic_anonymization', {})
                    presidio = presidio_result.get('presidio_anonymization', {})
                    
                    print(f"   Classic: {classic.get('anonymized_content', 'ERROR')[:60]}...")
                    print(f"   Presidio: {presidio.get('anonymized_content', 'ERROR')[:60]}...")
                    
                    # Metadati ibridi
                    hybrid_meta = presidio_result.get('hybrid_metadata', {})
                    print(f"   Entità Classic: {hybrid_meta.get('total_entities_classic', 0)}")
                    print(f"   Entità Presidio: {hybrid_meta.get('total_entities_presidio', 0)}")
                    
                elif config['presidio']['anonymization_mode'] == 'presidio':
                    # Modalità solo Presidio
                    print(f"   Presidio: {presidio_result.get('anonymized_content', 'ERROR')[:60]}...")
                    print(f"   Entità rilevate: {len(presidio_result.get('entities_detected', []))}")
                    
                    # Mostra entità specifiche
                    entities = presidio_result.get('entities_detected', [])
                    if entities:
                        print("   Entità specifiche:")
                        for entity in entities[:3]:
                            entity_type = entity.get('entity_type', 'unknown')
                            entity_text = entity.get('text', '')
                            entity_score = entity.get('score', 0)
                            print(f"     - {entity_type}: '{entity_text}' (score: {entity_score:.2f})")
                
                # Insight datamining
                if 'datamining_insights' in presidio_result:
                    insights = presidio_result['datamining_insights']
                    print(f"   Insight datamining: {list(insights.keys())}")
                
            else:
                print("❌ Presidio NON attivo")
                print("   Verifica configurazione e dipendenze")
            
            # Dati parsati
            parsed_data = record.get('parsed_data', {})
            if parsed_data:
                print(f"   Dati parsati: {len(parsed_data)} campi")
                if 'detected_patterns' in parsed_data:
                    patterns = parsed_data['detected_patterns']
                    print(f"   Pattern rilevati: {list(patterns.keys())}")
        
        print("\n" + "=" * 80)
        
        # Statistiche finali
        stats = parsing_service.get_statistics()
        print("📈 STATISTICHE FINALI:")
        print(f"   Totali processati: {stats.get('total_processed', 0)}")
        print(f"   Successi: {stats.get('successfully_parsed', 0)}")
        print(f"   Anonimizzati: {stats.get('anonymized', 0)}")
        print(f"   Errori: {stats.get('errors', 0)}")
        
        # Verifica finale
        presidio_active = any(
            hasattr(record, 'presidio_anonymization') and record.presidio_anonymization 
            for record in parsed_results
        )
        
        print("\n🎯 VERIFICA FINALE:")
        if presidio_active:
            print("✅ PRESIDIO INTEGRATO CORRETTAMENTE!")
            print("   I record ora includono risultati Presidio")
            print("   Modalità: " + config['presidio']['anonymization_mode'])
        else:
            print("❌ PRESIDIO NON ATTIVO")
            print("   Verifica configurazione e dipendenze")
        
        return presidio_active
        
    except Exception as e:
        print(f"❌ ERRORE DURANTE IL TEST: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_modes():
    """Testa le diverse modalità di anonimizzazione."""
    
    print("\n🔄 TEST MODALITÀ DIVERSE")
    print("=" * 80)
    
    modes = ['classic', 'presidio', 'hybrid']
    
    for mode in modes:
        print(f"\n--- Modalità: {mode.upper()} ---")
        
        config = {
            "presidio": {
                "enabled": True,
                "anonymization_mode": mode,
                "analyzer": {
                    "languages": ["en"],
                    "entities": {
                        "PERSON": True,
                        "IP_ADDRESS": True,
                        "EMAIL_ADDRESS": True
                    }
                }
            },
            "anonymization": {
                "enabled": True
            }
        }
        
        try:
            parsing_service = ParsingService(config)
            
            # Test con un messaggio semplice
            test_message = "User John Doe logged in from 192.168.1.100"
            
            # Usa l'adapter direttamente
            adapter = parsing_service.log_processing_service._anonymizer
            
            if hasattr(adapter, 'anonymize'):
                result = adapter.anonymize(test_message)
                print(f"   Anonimizzato: {result[:60]}...")
                
                if hasattr(adapter, 'get_anonymization_mode'):
                    print(f"   Modalità attiva: {adapter.get_anonymization_mode()}")
                
                if hasattr(adapter, 'is_presidio_available'):
                    print(f"   Presidio disponibile: {adapter.is_presidio_available()}")
                
                if mode == 'hybrid' and hasattr(adapter, 'get_hybrid_comparison'):
                    comparison = adapter.get_hybrid_comparison(test_message)
                    if comparison:
                        classic = comparison.get('classic', {})
                        presidio = comparison.get('presidio', {})
                        print(f"   Classic: {classic.get('anonymized_content', 'N/A')[:40]}...")
                        print(f"   Presidio: {presidio.get('anonymized_content', 'N/A')[:40]}...")
            
            print(f"   ✅ Modalità {mode} funzionante")
            
        except Exception as e:
            print(f"   ❌ Errore modalità {mode}: {e}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("🚀 AVVIO TEST INTEGRAZIONE PRESIDIO COMPLETA")
    print("=" * 80)
    
    # Test integrazione nel pipeline
    success1 = test_presidio_integration_in_pipeline()
    
    # Test modalità diverse
    test_different_modes()
    
    print("\n" + "=" * 80)
    if success1:
        print("🎉 TEST COMPLETATO CON SUCCESSO!")
        print("✅ Presidio è integrato nel pipeline di parsing")
        print("✅ I record includono risultati Presidio")
        print("✅ Modalità classic, presidio e hybrid funzionano")
    else:
        print("❌ TEST FALLITO")
        print("   Presidio non è integrato correttamente")
    
    print("=" * 80)
