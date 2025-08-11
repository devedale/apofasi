#!/usr/bin/env python3
"""
Test di base per verificare la struttura del progetto Clean Log Parser.
"""

import sys
from pathlib import Path

# Aggiungi src al path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test che tutti i moduli possano essere importati."""
    try:
        # Test domain entities
        from domain.entities.log_entry import LogEntry
        from domain.entities.parsed_record import ParsedRecord
        
        # Test domain interfaces
        from domain.interfaces.log_parser import LogParser
        from domain.interfaces.anonymizer import Anonymizer
        from domain.interfaces.drain3_service import Drain3Service
        
        # Test domain services
        from domain.services.parser_orchestrator import ParserOrchestrator
        from domain.services.log_processing_service import LogProcessingService
        
        print("✅ Tutti i moduli domain importati correttamente")
        
    except ImportError as e:
        print(f"❌ Errore import domain: {e}")
        return False
    
    try:
        # Test infrastructure
        from infrastructure.drain3_service import Drain3ServiceImpl
        
        print("✅ Moduli infrastructure importati correttamente")
        
    except ImportError as e:
        print(f"❌ Errore import infrastructure: {e}")
        return False
    
    return True

def test_entities():
    """Test delle entità del dominio."""
    try:
        from domain.entities.log_entry import LogEntry
        from domain.entities.parsed_record import ParsedRecord
        
        # Test LogEntry
        log_entry = LogEntry(
            content="Test log message",
            source_file=Path("test.log"),
            line_number=1
        )
        
        assert log_entry.content == "Test log message"
        assert log_entry.line_number == 1
        assert not log_entry.is_empty
        
        # Test ParsedRecord
        record = ParsedRecord(
            original_content="Test log message",
            parsed_data={"message": "Test log message"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=1
        )
        
        assert record.parser_name == "test"
        assert record.is_valid
        assert not record.has_warnings
        
        print("✅ Entità del dominio testate correttamente")
        return True
        
    except Exception as e:
        print(f"❌ Errore test entità: {e}")
        return False

def test_config():
    """Test della configurazione."""
    try:
        config_path = Path(__file__).parent / "config" / "config.yaml"
        assert config_path.exists(), f"File di configurazione non trovato: {config_path}"
        
        print("✅ File di configurazione trovato")
        return True
        
    except Exception as e:
        print(f"❌ Errore test configurazione: {e}")
        return False

def test_examples():
    """Test dei file di esempio."""
    try:
        examples_dir = Path(__file__).parent / "examples"
        assert examples_dir.exists(), f"Directory esempi non trovata: {examples_dir}"
        
        example_files = list(examples_dir.glob("*"))
        assert len(example_files) > 0, "Nessun file di esempio trovato"
        
        print(f"✅ Trovati {len(example_files)} file di esempio")
        return True
        
    except Exception as e:
        print(f"❌ Errore test esempi: {e}")
        return False

def main():
    """Esegui tutti i test di base."""
    print("🧪 Test di base Clean Log Parser")
    print("=" * 50)
    
    tests = [
        ("Import moduli", test_imports),
        ("Entità dominio", test_entities),
        ("Configurazione", test_config),
        ("File di esempio", test_examples),
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
        print("🎉 Tutti i test di base superati!")
        return 0
    else:
        print("⚠️  Alcuni test falliti")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 