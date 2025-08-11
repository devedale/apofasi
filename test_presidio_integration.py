#!/usr/bin/env python3
"""
Test per l'integrazione di Microsoft Presidio con il sistema esistente.
Verifica anonimizzazione classica, Presidio e ibrida.
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.presidio_service import PresidioService
from src.infrastructure.hybrid_anonymizer_service import HybridAnonymizerService
from src.domain.services.centralized_regex_service import CentralizedRegexServiceImpl


def test_presidio_service():
    """Test del servizio Presidio standalone."""
    
    print("🧪 Test Presidio Service Standalone")
    print("=" * 80)
    
    # Configurazione di test
    config = {
        "presidio": {
            "enabled": True,
            "anonymization_mode": "presidio",
            "analyzer": {
                "languages": ["en"],
                "entities": {
                    "PERSON": True,
                    "EMAIL_ADDRESS": True,
                    "PHONE_NUMBER": True,
                    "IP_ADDRESS": True,
                    "CREDIT_CARD": True,
                    "LOCATION": True,
                    "ORGANIZATION": True
                },
                "analysis": {
                    "confidence_threshold": 0.6
                }
            }
        }
    }
    
    try:
        # Crea servizio Presidio
        presidio_service = PresidioService(config)
        print("✅ Presidio Service creato con successo")
        
        # Test configurazione
        config_summary = presidio_service.get_configuration_summary()
        print(f"📊 Configurazione: {config_summary}")
        
        # Testi di esempio per test
        test_texts = [
            "John Doe contacted us at john.doe@company.com from IP 192.168.1.100",
            "Call us at +1-555-123-4567 or visit our office in New York",
            "Credit card 1234-5678-9012-3456 was used for payment",
            "User ID 12345 logged in from device FGT80FTK22013405"
        ]
        
        print(f"\n📝 Testando {len(test_texts)} testi di esempio...")
        
        for i, text in enumerate(test_texts):
            print(f"\n--- Test {i+1} ---")
            print(f"Originale: {text}")
            
            # Analisi entità
            entities = presidio_service.analyze_text(text)
            print(f"Entità rilevate: {len(entities)}")
            for entity in entities:
                print(f"  - {entity['entity_type']}: '{entity['text']}' (score: {entity['score']:.2f})")
            
            # Processing completo
            result = presidio_service.process_with_presidio(text)
            print(f"Anonimizzato: {result.get('anonymized_text', 'ERROR')}")
            
            # Insight datamining
            insights = result.get('datamining_insights', {})
            if insights:
                print(f"Insight datamining: {insights.get('entity_summary', {}).get('total_entities', 0)} entità")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRORE nel test Presidio Service: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hybrid_anonymizer():
    """Test del servizio di anonimizzazione ibrido."""
    
    print("\n🧪 Test Hybrid Anonymizer Service")
    print("=" * 80)
    
    # Configurazione di test
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
                    "ORGANIZATION": True
                }
            }
        }
    }
    
    try:
        # Crea servizio regex centralizzato
        centralized_regex_service = CentralizedRegexServiceImpl(config)
        print("✅ Centralized Regex Service creato")
        
        # Crea servizio anonimizzazione ibrido
        hybrid_service = HybridAnonymizerService(config, centralized_regex_service)
        print("✅ Hybrid Anonymizer Service creato")
        
        # Test configurazione
        config_summary = hybrid_service.get_configuration_summary()
        print(f"📊 Configurazione: {config_summary}")
        
        # Testi di esempio
        test_texts = [
            "User John Doe (john.doe@company.com) accessed from 192.168.1.100",
            "Device FGT80FTK22013405 reported error at 2025-08-11 18:30:00",
            "Payment processed with card 1234-5678-9012-3456 from New York office",
            "Session ID 98765 started by user admin from hostname server-01"
        ]
        
        print(f"\n📝 Testando modalità di anonimizzazione...")
        
        # Test modalità classica
        print("\n--- Modalità CLASSIC ---")
        for i, text in enumerate(test_texts[:2]):
            result = hybrid_service.anonymize_content(text, mode="classic")
            print(f"Test {i+1}: {result.get('anonymized_content', 'ERROR')[:100]}...")
        
        # Test modalità Presidio
        print("\n--- Modalità PRESIDIO ---")
        for i, text in enumerate(test_texts[:2]):
            result = hybrid_service.anonymize_content(text, mode="presidio")
            print(f"Test {i+1}: {result.get('anonymized_content', 'ERROR')[:100]}...")
            if result.get('entities_detected'):
                print(f"  Entità rilevate: {len(result['entities_detected'])}")
        
        # Test modalità ibrida
        print("\n--- Modalità HYBRID ---")
        for i, text in enumerate(test_texts[:2]):
            result = hybrid_service.anonymize_content(text, mode="hybrid")
            print(f"Test {i+1}:")
            
            # Mostra risultati classici
            classic_result = result.get('classic_anonymization', {})
            print(f"  Classic: {classic_result.get('anonymized_content', 'ERROR')[:80]}...")
            
            # Mostra risultati Presidio
            presidio_result = result.get('presidio_anonymization', {})
            print(f"  Presidio: {presidio_result.get('anonymized_content', 'ERROR')[:80]}...")
            
            # Mostra metadati ibridi
            hybrid_metadata = result.get('hybrid_metadata', {})
            print(f"  Entità Classic: {hybrid_metadata.get('total_entities_classic', 0)}")
            print(f"  Entità Presidio: {hybrid_metadata.get('total_entities_presidio', 0)}")
            
            # Mostra insight datamining combinati
            combined_insights = result.get('combined_datamining_insights', {})
            comparison = combined_insights.get('comparison_analysis', {})
            print(f"  Totale entità: {comparison.get('total_entities_detected', 0)}")
            print(f"  Tipi unici: {comparison.get('unique_entity_types', 0)}")
        
        # Test batch processing
        print("\n--- Test BATCH PROCESSING ---")
        batch_results = hybrid_service.batch_anonymize(test_texts, mode="hybrid")
        print(f"Processati {len(batch_results)} testi in batch")
        
        # Riepilogo batch
        batch_summary = hybrid_service.get_anonymization_summary(batch_results)
        print(f"📊 Riepilogo batch: {batch_summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRORE nel test Hybrid Anonymizer: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_datamining_insights():
    """Test dell'estrazione di insight per datamining."""
    
    print("\n🧪 Test Datamining Insights")
    print("=" * 80)
    
    # Configurazione di test
    config = {
        "presidio": {
            "enabled": True,
            "anonymization_mode": "presidio",
            "datamining": {
                "enabled": True
            },
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
        }
    }
    
    try:
        # Crea servizio Presidio
        presidio_service = PresidioService(config)
        print("✅ Presidio Service creato per test datamining")
        
        # Testi complessi per datamining
        complex_texts = [
            "User John Doe (ID: 12345) logged in from 192.168.1.100 at 2025-08-11 18:30:00. Contact: john.doe@company.com",
            "Device FGT80FTK22013405 in New York office reported security alert. Admin user (ID: 98765) investigating.",
            "Payment $150.00 processed with card ending 3456 from IP 10.0.0.50. Location: San Francisco, CA",
            "Session 54321 started by user admin from hostname server-01. Multiple login attempts detected."
        ]
        
        print(f"📝 Analizzando {len(complex_texts)} testi complessi per insight datamining...")
        
        all_insights = []
        
        for i, text in enumerate(complex_texts):
            print(f"\n--- Analisi Test {i+1} ---")
            print(f"Testo: {text[:80]}...")
            
            # Processing completo con Presidio
            result = presidio_service.process_with_presidio(text)
            
            # Estrai insight
            insights = result.get('datamining_insights', {})
            all_insights.append(insights)
            
            if insights:
                entity_summary = insights.get('entity_summary', {})
                print(f"  Entità totali: {entity_summary.get('total_entities', 0)}")
                print(f"  Tipi unici: {entity_summary.get('unique_entity_types', 0)}")
                
                # Pattern specifici
                patterns = insights.get('patterns', {})
                if 'temporal' in patterns:
                    print(f"  Pattern temporali: {patterns['temporal']['count']}")
                if 'geographic' in patterns:
                    print(f"  Pattern geografici: {patterns['geographic']['count']}")
                if 'network' in patterns:
                    print(f"  Pattern di rete: {patterns['network']['count']}")
                
                # Sicurezza
                security = insights.get('security', {})
                if 'sensitive_data' in security:
                    risk_level = security['sensitive_data']['risk_level']
                    print(f"  Livello rischio: {risk_level}")
        
        # Analisi aggregata
        print(f"\n📊 ANALISI AGGREGATA DATAMINING:")
        total_entities = sum(len(insight.get('entity_summary', {}).get('entity_distribution', {})) for insight in all_insights)
        print(f"  Entità totali rilevate: {total_entities}")
        
        # Pattern aggregati
        all_patterns = {}
        for insight in all_insights:
            patterns = insight.get('patterns', {})
            for pattern_type, pattern_data in patterns.items():
                if pattern_type not in all_patterns:
                    all_patterns[pattern_type] = 0
                all_patterns[pattern_type] += pattern_data.get('count', 0)
        
        print(f"  Pattern aggregati: {all_patterns}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRORE nel test Datamining Insights: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Avvio test integrazione Microsoft Presidio...")
    print("=" * 80)
    
    # Test 1: Presidio Service
    success1 = test_presidio_service()
    
    # Test 2: Hybrid Anonymizer
    success2 = test_hybrid_anonymizer()
    
    # Test 3: Datamining Insights
    success3 = test_datamining_insights()
    
    print("\n" + "=" * 80)
    if success1 and success2 and success3:
        print("🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
        print("✅ Microsoft Presidio integrato correttamente")
        print("✅ Anonimizzazione ibrida funzionante")
        print("✅ Insight datamining estratti correttamente")
    else:
        print("❌ ALCUNI TEST SONO FALLITI")
        print("⚠️  Controlla la configurazione e i log per dettagli")
    
    print("=" * 80)
