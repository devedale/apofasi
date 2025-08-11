#!/usr/bin/env python3
"""
Test di debug per Presidio - vede esattamente dove fallisce l'inizializzazione
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

def test_presidio_imports():
    """Testa gli import di Presidio."""
    print("🔍 Test import Presidio...")
    
    try:
        from presidio_analyzer import AnalyzerEngine, BatchAnalyzerEngine
        print("✅ presidio_analyzer importato")
    except Exception as e:
        print(f"❌ presidio_analyzer fallito: {e}")
        return False
    
    try:
        from presidio_anonymizer import AnonymizerEngine
        print("✅ presidio_anonymizer importato")
    except Exception as e:
        print(f"❌ presidio_anonymizer fallito: {e}")
        return False
    
    try:
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        print("✅ NlpEngineProvider importato")
    except Exception as e:
        print(f"❌ NlpEngineProvider fallito: {e}")
        return False
    
    return True

def test_spacy_models():
    """Testa i modelli spaCy."""
    print("\n🔍 Test modelli spaCy...")
    
    try:
        import spacy
        print("✅ spacy importato")
        
        # Test modello inglese
        try:
            nlp_en = spacy.load("en_core_web_sm")
            print("✅ modello en_core_web_sm caricato")
        except Exception as e:
            print(f"❌ modello en_core_web_sm fallito: {e}")
            print("   Installa con: python -m spacy download en_core_web_sm")
            return False
        
        # Test modello italiano
        try:
            nlp_it = spacy.load("it_core_news_sm")
            print("✅ modello it_core_news_sm caricato")
        except Exception as e:
            print(f"⚠️ modello it_core_news_sm fallito: {e}")
            print("   Installa con: python -m spacy download it_core_news_sm")
            # Non è critico per il test base
        
    except Exception as e:
        print(f"❌ spacy fallito: {e}")
        return False
    
    return True

def test_presidio_service():
    """Testa il PresidioService."""
    print("\n🔍 Test PresidioService...")
    
    try:
        from src.infrastructure.presidio_service import PresidioService
        print("✅ PresidioService importato")
        
        # Configurazione di test
        config = {
            "presidio": {
                "enabled": True,
                "anonymization_mode": "hybrid",
                "analyzer": {
                    "languages": ["en"],
                    "entities": {
                        "PERSON": True,
                        "IP_ADDRESS": True
                    }
                }
            }
        }
        
        print("   Configurazione creata")
        
        # Prova a creare il servizio
        try:
            service = PresidioService(config)
            print("✅ PresidioService creato")
            
            if service.analyzer_engine:
                print("✅ Analyzer Engine disponibile")
            else:
                print("❌ Analyzer Engine non disponibile")
                
            if service.anonymizer_engine:
                print("✅ Anonymizer Engine disponibile")
            else:
                print("❌ Anonymizer Engine non disponibile")
                
        except Exception as e:
            print(f"❌ Creazione PresidioService fallita: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Import PresidioService fallito: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_hybrid_service():
    """Testa il HybridAnonymizerService."""
    print("\n🔍 Test HybridAnonymizerService...")
    
    try:
        from src.infrastructure.hybrid_anonymizer_service import HybridAnonymizerService
        print("✅ HybridAnonymizerService importato")
        
        # Configurazione di test
        config = {
            "presidio": {
                "enabled": True,
                "anonymization_mode": "hybrid",
                "analyzer": {
                    "languages": ["en"],
                    "entities": {
                        "PERSON": True,
                        "IP_ADDRESS": True
                    }
                }
            }
        }
        
        print("   Configurazione creata")
        
        # Prova a creare il servizio
        try:
            service = HybridAnonymizerService(config)
            print("✅ HybridAnonymizerService creato")
            
            if service.presidio_service:
                print("✅ Presidio Service disponibile")
            else:
                print("❌ Presidio Service non disponibile")
                
        except Exception as e:
            print(f"❌ Creazione HybridAnonymizerService fallita: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Import HybridAnonymizerService fallito: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 DEBUG PRESIDIO - Test completo")
    print("=" * 60)
    
    # Test 1: Import base
    success1 = test_presidio_imports()
    
    # Test 2: Modelli spaCy
    if success1:
        success2 = test_spacy_models()
    else:
        success2 = False
    
    # Test 3: PresidioService
    if success2:
        success3 = test_presidio_service()
    else:
        success3 = False
    
    # Test 4: HybridAnonymizerService
    if success3:
        success4 = test_hybrid_service()
    else:
        success4 = False
    
    print("\n" + "=" * 60)
    print("🎯 RISULTATO FINALE:")
    
    if success4:
        print("✅ TUTTO FUNZIONA! Presidio è completamente operativo")
    elif success3:
        print("⚠️ Presidio funziona ma HybridAnonymizerService fallisce")
    elif success2:
        print("⚠️ Modelli spaCy funzionano ma PresidioService fallisce")
    elif success1:
        print("⚠️ Import base funzionano ma modelli spaCy falliscono")
    else:
        print("❌ Import base falliscono")
    
    print("=" * 60)
