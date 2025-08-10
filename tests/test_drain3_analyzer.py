#!/usr/bin/env python3
"""
Test del Drain3Analyzer per analisi template e metadati.
"""

import sys
import json
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from src.core.services.drain3_analyzer import Drain3Analyzer


def test_drain3_analyzer():
    """Test del Drain3Analyzer."""
    print("🧪 Testando Drain3Analyzer...")
    
    # Inizializza l'analizzatore
    analyzer = Drain3Analyzer()
    
    # Crea un file di test con log unificati
    test_logs = [
        {
            "id": "1",
            "original_content": "2024-01-01 10:00:00 INFO User login successful from 192.168.1.100",
            "source_file": "test1.log"
        },
        {
            "id": "2", 
            "original_content": "2024-01-01 10:01:00 INFO User login successful from 192.168.1.101",
            "source_file": "test1.log"
        },
        {
            "id": "3",
            "original_content": "2024-01-01 10:02:00 ERROR Database connection failed",
            "source_file": "test2.log"
        },
        {
            "id": "4",
            "original_content": "2024-01-01 10:03:00 ERROR Database connection failed",
            "source_file": "test2.log"
        },
        {
            "id": "5",
            "original_content": "2024-01-01 10:04:00 WARN High memory usage detected: 85%",
            "source_file": "test3.log"
        }
    ]
    
    # Salva file di test
    test_file = Path("test_unified_logs.json")
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_logs, f, indent=2)
    
    print(f"📝 File di test creato: {test_file}")
    
    # Test 1: Analisi log unificati
    print("\n🔍 Test analisi log unificati:")
    try:
        results = analyzer.analyze_unified_logs(test_file)
        print(f"   - Analisi completata: {'✅' if results else '❌'}")
        
        if results:
            print(f"   - Record analizzati: {results.get('total_records_analyzed', 0)}")
            print(f"   - File analizzati: {results.get('files_analyzed', 0)}")
            
            global_analysis = results.get('global_analysis', {})
            if global_analysis:
                stats = global_analysis.get('statistics', {})
                print(f"   - Template globali: {stats.get('total_templates', 0)}")
                print(f"   - Media log per template: {stats.get('avg_logs_per_template', 0)}")
            
            # Stampa riassunto
            analyzer.print_summary(results)
            
    except Exception as e:
        print(f"   - Errore analisi: {e}")
    
    # Test 2: Salva risultati
    print("\n💾 Test salvataggio risultati:")
    try:
        output_file = Path("outputs/drain3_analysis.json")
        analyzer.save_analysis_results(results, output_file)
        print(f"   - Risultati salvati: {'✅' if output_file.exists() else '❌'}")
    except Exception as e:
        print(f"   - Errore salvataggio: {e}")
    
    # Pulisci file di test
    if test_file.exists():
        test_file.unlink()
        print(f"\n🗑️ File di test rimosso: {test_file}")
    
    print("\n✅ Test Drain3Analyzer completato!")


if __name__ == "__main__":
    test_drain3_analyzer() 