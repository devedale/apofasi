#!/usr/bin/env python3
"""
Test script per verificare il sistema con i file loghub.
"""

import sys
import os
from pathlib import Path

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from application.services.parsing_service import ParsingService
from application.services.configuration_service import ConfigurationService

def test_loghub_processing():
    """Test del processing dei file loghub."""
    
    print("🧪 Test Processing Loghub Files")
    print("=" * 50)
    
    # Carica configurazione
    config_service = ConfigurationService()
    config = config_service.load_configuration("config/config.yaml")
    
    # Crea parsing service
    parsing_service = ParsingService(config)
    
    # Test con directory examples (include loghub)
    print("📁 Processing directory examples/ (include loghub)...")
    
    try:
        results = parsing_service.parse_files("examples/")
        print(f"✅ Processati {len(results)} record totali")
        
        # Analizza risultati
        parser_stats = {}
        for result in results:
            parser_name = result.get("parser_name", "unknown")
            if parser_name not in parser_stats:
                parser_stats[parser_name] = 0
            parser_stats[parser_name] += 1
        
        print("\n📊 Statistiche per Parser:")
        for parser, count in parser_stats.items():
            print(f"  • {parser}: {count} record")
        
        # Conta file processati
        files_processed = set()
        for result in results:
            source_file = result.get("source_file", "unknown")
            files_processed.add(source_file)
        
        print(f"\n📄 File processati: {len(files_processed)}")
        for file in sorted(files_processed):
            print(f"  - {file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il processing: {e}")
        return False

if __name__ == "__main__":
    success = test_loghub_processing()
    sys.exit(0 if success else 1) 