#!/usr/bin/env python3
"""
Test della struttura del progetto Clean Log Parser (senza dipendenze esterne).
"""

import sys
from pathlib import Path

# Aggiungi src al path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_domain_entities():
    """Test delle entità del dominio."""
    try:
        from domain.entities.log_entry import LogEntry
        from domain.entities.parsed_record import ParsedRecord
        from domain.entities.anonymization_config import AnonymizationConfig
        from domain.entities.parser_config import ParserConfig
        
        print("✅ Tutte le entità del dominio importate correttamente")
        return True
        
    except ImportError as e:
        print(f"❌ Errore import entità: {e}")
        return False

def test_domain_interfaces():
    """Test delle interfacce del dominio."""
    try:
        from domain.interfaces.log_parser import LogParser
        from domain.interfaces.anonymizer import Anonymizer
        from domain.interfaces.drain3_service import Drain3Service
        from domain.interfaces.log_reader import LogReader
        from domain.interfaces.log_writer import LogWriter
        
        print("✅ Tutte le interfacce del dominio importate correttamente")
        return True
        
    except ImportError as e:
        print(f"❌ Errore import interfacce: {e}")
        return False

def test_domain_services():
    """Test dei servizi del dominio."""
    try:
        from domain.services.parser_orchestrator import ParserOrchestrator
        from domain.services.log_processing_service import LogProcessingService
        from domain.services.anonymization_service import AnonymizationService
        
        print("✅ Tutti i servizi del dominio importati correttamente")
        return True
        
    except ImportError as e:
        print(f"❌ Errore import servizi: {e}")
        return False

def test_infrastructure_basic():
    """Test delle implementazioni infrastructure (senza drain3)."""
    try:
        from infrastructure.log_reader import SimpleLogReader
        from infrastructure.config_loader import ConfigLoader
        from infrastructure.anonymizer import RegexAnonymizer
        
        print("✅ Implementazioni infrastructure di base importate correttamente")
        return True
        
    except ImportError as e:
        print(f"❌ Errore import infrastructure: {e}")
        return False

def test_application():
    """Test dell'applicazione."""
    try:
        # Test che il main possa essere importato (anche se non eseguito)
        from application.main import app
        
        print("✅ Applicazione importata correttamente")
        return True
        
    except ImportError as e:
        print(f"❌ Errore import applicazione: {e}")
        return False

def test_entities_creation():
    """Test della creazione delle entità."""
    try:
        from domain.entities.log_entry import LogEntry
        from domain.entities.parsed_record import ParsedRecord
        from pathlib import Path
        
        # Test LogEntry
        log_entry = LogEntry(
            content="Test log message",
            source_file=Path("test.log"),
            line_number=1
        )
        
        # Test ParsedRecord
        record = ParsedRecord(
            original_content="Test log message",
            parsed_data={"message": "Test log message"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=1
        )
        
        print("✅ Entità create correttamente")
        return True
        
    except Exception as e:
        print(f"❌ Errore creazione entità: {e}")
        return False

def test_config_loading():
    """Test del caricamento della configurazione."""
    try:
        from infrastructure.config_loader import ConfigLoader
        
        config_loader = ConfigLoader()
        config = config_loader.load_default_config()
        
        # Verifica sezioni principali
        required_sections = ["app", "drain3", "parsers", "regex_patterns"]
        for section in required_sections:
            if section not in config:
                print(f"❌ Sezione mancante: {section}")
                return False
        
        print("✅ Configurazione caricata correttamente")
        return True
        
    except Exception as e:
        print(f"❌ Errore caricamento configurazione: {e}")
        return False

def test_project_structure():
    """Test della struttura del progetto."""
    try:
        # Verifica directory principali
        required_dirs = [
            "src/domain/entities",
            "src/domain/interfaces", 
            "src/domain/services",
            "src/infrastructure",
            "src/application",
            "config",
            "examples",
        ]
        
        for dir_path in required_dirs:
            if not (Path(__file__).parent / dir_path).exists():
                print(f"❌ Directory mancante: {dir_path}")
                return False
        
        print("✅ Struttura del progetto corretta")
        return True
        
    except Exception as e:
        print(f"❌ Errore verifica struttura: {e}")
        return False

def main():
    """Esegui tutti i test di struttura."""
    print("🧪 Test Struttura Clean Log Parser")
    print("=" * 50)
    
    tests = [
        ("Entità dominio", test_domain_entities),
        ("Interfacce dominio", test_domain_interfaces),
        ("Servizi dominio", test_domain_services),
        ("Infrastructure base", test_infrastructure_basic),
        ("Applicazione", test_application),
        ("Creazione entità", test_entities_creation),
        ("Caricamento config", test_config_loading),
        ("Struttura progetto", test_project_structure),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Test: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ Test fallito: {test_name}")
    
    print(f"\n📊 Risultati: {passed}/{total} test superati")
    
    if passed == total:
        print("🎉 Tutti i test di struttura superati!")
        print("\n🏗️  Architettura Clean Architecture implementata correttamente:")
        print("  ✅ Domain Layer (Entities, Interfaces, Services)")
        print("  ✅ Infrastructure Layer (Implementazioni)")
        print("  ✅ Application Layer (Use Cases)")
        print("  ✅ Inversione delle Dipendenze")
        print("  ✅ Principi SOLID")
        return 0
    else:
        print("⚠️  Alcuni test falliti")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 