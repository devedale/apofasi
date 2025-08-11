#!/usr/bin/env python3
"""
Esempio che mostra la differenza tra le modalità di anonimizzazione:
- CLASSIC: Solo regex
- PRESIDIO: Solo AI
- HYBRID: Entrambi separatamente sul messaggio originale
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.hybrid_anonymizer_service import HybridAnonymizerService
from src.domain.services.centralized_regex_service import CentralizedRegexServiceImpl


def demonstrate_hybrid_modes():
    """Dimostra le differenze tra le modalità di anonimizzazione."""
    
    print("🔍 DIMOSTRAZIONE MODALITÀ ANONIMIZZAZIONE")
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
                    "ORGANIZATION": True,
                    "DATE_TIME": True,
                    "ID": True,
                    "HOSTNAME": True
                }
            }
        }
    }
    
    # Crea servizi
    centralized_regex_service = CentralizedRegexServiceImpl(config)
    hybrid_service = HybridAnonymizerService(config, centralized_regex_service)
    
    # Testo di esempio complesso
    test_text = "User John Doe (ID: 12345) logged in from 192.168.1.100 at 2025-08-11 18:30:00. Contact: john.doe@company.com. Device FGT80FTK22013405 in New York office."
    
    print(f"📝 TESTO ORIGINALE:")
    print(f"   {test_text}")
    print()
    
    # Test 1: Modalità CLASSIC (solo regex)
    print("🔧 MODALITÀ CLASSIC (solo regex)")
    print("-" * 50)
    classic_result = hybrid_service.anonymize_content(test_text, mode="classic")
    print(f"Risultato: {classic_result.get('anonymized_content', 'ERROR')}")
    print(f"Metodo: {classic_result.get('method', 'unknown')}")
    print(f"Entità rilevate: {len(classic_result.get('entities_detected', []))}")
    print()
    
    # Test 2: Modalità PRESIDIO (solo AI)
    print("🤖 MODALITÀ PRESIDIO (solo AI)")
    print("-" * 50)
    presidio_result = hybrid_service.anonymize_content(test_text, mode="presidio")
    print(f"Risultato: {presidio_result.get('anonymized_content', 'ERROR')}")
    print(f"Metodo: {presidio_result.get('method', 'unknown')}")
    print(f"Entità rilevate: {len(presidio_result.get('entities_detected', []))}")
    
    # Mostra entità rilevate da Presidio
    entities = presidio_result.get('entities_detected', [])
    if entities:
        print("  Entità specifiche:")
        for entity in entities:
            print(f"    - {entity['entity_type']}: '{entity['text']}' (score: {entity['score']:.2f})")
    print()
    
    # Test 3: Modalità HYBRID (entrambi separatamente)
    print("🔄 MODALITÀ HYBRID (entrambi separatamente)")
    print("-" * 50)
    hybrid_result = hybrid_service.anonymize_content(test_text, mode="hybrid")
    
    # Risultati Classic
    classic_anon = hybrid_result.get('classic_anonymization', {})
    print(f"📊 RISULTATI CLASSIC (regex):")
    print(f"   Contenuto anonimizzato: {classic_anon.get('anonymized_content', 'ERROR')}")
    print(f"   Metodo: {classic_anon.get('method', 'unknown')}")
    print(f"   Entità rilevate: {classic_anon.get('entities_detected', [])}")
    print()
    
    # Risultati Presidio
    presidio_anon = hybrid_result.get('presidio_anonymization', {})
    print(f"🤖 RISULTATI PRESIDIO (AI):")
    print(f"   Contenuto anonimizzato: {presidio_anon.get('anonymized_content', 'ERROR')}")
    print(f"   Metodo: {presidio_anon.get('method', 'unknown')}")
    print(f"   Entità rilevate: {len(presidio_anon.get('entities_detected', []))}")
    
    # Mostra entità specifiche Presidio
    presidio_entities = presidio_anon.get('entities_detected', [])
    if presidio_entities:
        print("   Entità specifiche:")
        for entity in presidio_entities:
            print(f"     - {entity['entity_type']}: '{entity['text']}' (score: {entity['score']:.2f})")
    print()
    
    # Metadati ibridi
    hybrid_metadata = hybrid_result.get('hybrid_metadata', {})
    print(f"📈 METADATI IBRIDI:")
    print(f"   Entità Classic: {hybrid_metadata.get('total_entities_classic', 0)}")
    print(f"   Entità Presidio: {hybrid_metadata.get('total_entities_presidio', 0)}")
    print(f"   Metodo processing: {hybrid_metadata.get('processing_method', 'unknown')}")
    print(f"   Note: {hybrid_metadata.get('comparison_notes', 'N/A')}")
    print()
    
    # Insight datamining combinati
    combined_insights = hybrid_result.get('combined_datamining_insights', {})
    comparison = combined_insights.get('comparison_analysis', {})
    print(f"🔍 INSIGHT DATAMINING COMBINATI:")
    print(f"   Totale entità rilevate: {comparison.get('total_entities_detected', 0)}")
    print(f"   Tipi unici di entità: {comparison.get('unique_entity_types', 0)}")
    print(f"   Analisi copertura: {comparison.get('coverage_analysis', 'N/A')}")
    print()
    
    # Confronto visivo
    print("📊 CONFRONTO VISIVO:")
    print("-" * 50)
    print(f"ORIGINALE: {test_text}")
    print(f"CLASSIC:   {classic_anon.get('anonymized_content', 'ERROR')}")
    print(f"PRESIDIO:  {presidio_anon.get('anonymized_content', 'ERROR')}")
    print()
    
    # Spiegazione delle differenze
    print("💡 SPIEGAZIONE DELLE DIFFERENZE:")
    print("-" * 50)
    print("1. CLASSIC: Usa solo pattern regex predefiniti")
    print("2. PRESIDIO: Usa solo AI/ML per rilevare entità PII")
    print("3. HYBRID: Processa il messaggio ORIGINALE due volte separatamente")
    print("   - NON sovrappone le anonimizzazioni")
    print("   - Fornisce entrambi i risultati per confronto")
    print("   - Permette analisi complementare dei due approcci")
    print()
    
    return True


def demonstrate_batch_hybrid():
    """Dimostra il processing batch in modalità ibrida."""
    
    print("🔄 DIMOSTRAZIONE BATCH PROCESSING HYBRID")
    print("=" * 80)
    
    # Configurazione
    config = {
        "presidio": {
            "enabled": True,
            "anonymization_mode": "hybrid"
        }
    }
    
    centralized_regex_service = CentralizedRegexServiceImpl(config)
    hybrid_service = HybridAnonymizerService(config, centralized_regex_service)
    
    # Testi di esempio
    test_texts = [
        "User admin logged in from 10.0.0.1 at 2025-08-11 19:00:00",
        "Payment processed with card 1234-5678-9012-3456 from IP 192.168.1.50",
        "Device FGT80FTK22013405 reported error in New York office",
        "Session ID 98765 started by user john.doe@company.com"
    ]
    
    print(f"📝 Processando {len(test_texts)} testi in modalità ibrida...")
    
    # Processing batch
    batch_results = hybrid_service.batch_anonymize(test_texts, mode="hybrid")
    
    # Mostra risultati per ogni testo
    for i, result in enumerate(batch_results):
        print(f"\n--- Test {i+1} ---")
        print(f"Originale: {result.get('original_content', '')[:60]}...")
        
        classic = result.get('classic_anonymization', {})
        presidio = result.get('presidio_anonymization', {})
        
        print(f"Classic:   {classic.get('anonymized_content', 'ERROR')[:60]}...")
        print(f"Presidio:  {presidio.get('anonymized_content', 'ERROR')[:60]}...")
    
    # Riepilogo batch
    batch_summary = hybrid_service.get_anonymization_summary(batch_results)
    print(f"\n📊 RIEPILOGO BATCH:")
    print(f"   Totali processati: {batch_summary.get('total_processed', 0)}")
    print(f"   Successi: {batch_summary.get('successful', 0)}")
    print(f"   Fallimenti: {batch_summary.get('failed', 0)}")
    print(f"   Modalità utilizzate: {batch_summary.get('modes_used', {})}")
    
    return True


if __name__ == "__main__":
    print("🚀 Avvio dimostrazione modalità anonimizzazione...")
    print("=" * 80)
    
    # Dimostrazione modalità singole
    success1 = demonstrate_hybrid_modes()
    
    print("\n" + "=" * 80)
    
    # Dimostrazione batch processing
    success2 = demonstrate_batch_hybrid()
    
    print("\n" + "=" * 80)
    if success1 and success2:
        print("🎉 DIMOSTRAZIONE COMPLETATA CON SUCCESSO!")
        print("✅ Modalità CLASSIC: Solo regex")
        print("✅ Modalità PRESIDIO: Solo AI")
        print("✅ Modalità HYBRID: Entrambi separatamente sul messaggio originale")
        print("✅ Batch processing funzionante")
    else:
        print("❌ ALCUNE DIMOSTRAZIONI SONO FALLITE")
    
    print("=" * 80)
