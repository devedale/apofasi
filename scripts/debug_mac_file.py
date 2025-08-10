#!/usr/bin/env python3
"""
Debug script per identificare il problema con il file Mac_2k.log_structured.csv.
"""

import sys
import time
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.parsers.adaptive_parser import AdaptiveParser
from src.domain.services.timestamp_normalization_service import TimestampNormalizationService


def test_parsing_step_by_step():
    """Test del parsing step by step per identificare il blocco."""
    print("🔍 Debug parsing file Mac...")
    
    file_path = "examples/loghub/Mac/Mac_2k.log_structured.csv"
    
    # Step 1: Leggi il file
    print("📖 Step 1: Lettura file...")
    start_time = time.time()
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    read_time = time.time() - start_time
    print(f"  ✅ File letto in {read_time:.3f}s")
    print(f"  📊 Dimensione: {len(content)} caratteri")
    
    # Step 2: Parsing adattivo
    print("🔧 Step 2: Parsing adattivo...")
    start_time = time.time()
    parser = AdaptiveParser()
    
    try:
        records = list(parser.parse(content, file_path))
        parse_time = time.time() - start_time
        print(f"  ✅ Parsing completato in {parse_time:.3f}s")
        print(f"  📊 Record parsati: {len(records)}")
        
        if records:
            print(f"  📋 Primo record: {list(records[0].keys())[:5]}...")
            
    except Exception as e:
        print(f"  ❌ Errore parsing: {e}")
        return False
    
    # Step 3: Normalizzazione timestamp (primi 10 record)
    print("⏰ Step 3: Normalizzazione timestamp (primi 10 record)...")
    start_time = time.time()
    normalizer = TimestampNormalizationService()
    
    try:
        for i, record in enumerate(records[:10]):
            print(f"    Record {i+1}/10...")
            normalized = normalizer.normalize_dict_record(record)
            print(f"      ✅ Normalizzato")
        
        norm_time = time.time() - start_time
        print(f"  ✅ Normalizzazione completata in {norm_time:.3f}s")
        
    except Exception as e:
        print(f"  ❌ Errore normalizzazione: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Test con record problematici
    print("🧪 Step 4: Test record problematici...")
    try:
        for i, record in enumerate(records):
            if i % 500 == 0:  # Ogni 500 record
                print(f"    Test record {i+1}/{len(records)}...")
                normalized = normalizer.normalize_dict_record(record)
        
        print(f"  ✅ Test completato")
        
    except Exception as e:
        print(f"  ❌ Errore al record {i+1}: {e}")
        return False
    
    return True


def test_csv_header_detection():
    """Test del rilevamento header CSV."""
    print("\n🔍 Test rilevamento header CSV...")
    
    from src.infrastructure.parsers.csv_header_detection import CSVHeaderDetector
    
    file_path = "examples/loghub/Mac/Mac_2k.log_structured.csv"
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()[:10]  # Prime 10 righe
    
    detector = CSVHeaderDetector()
    header_info = detector.detect_headers(lines)
    
    if header_info:
        print(f"  ✅ Header rilevati: {header_info.headers}")
        print(f"  📊 Confidence: {header_info.confidence:.2f}")
        print(f"  🔍 Delimiter: '{header_info.delimiter}'")
    else:
        print(f"  ❌ Nessun header rilevato")


def test_memory_usage():
    """Test dell'uso di memoria."""
    print("\n💾 Test uso memoria...")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"  📊 Memoria iniziale: {initial_memory:.1f} MB")
    
    # Simula il parsing
    file_path = "examples/loghub/Mac/Mac_2k.log_structured.csv"
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    parser = AdaptiveParser()
    records = list(parser.parse(content, file_path))
    
    current_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"  📊 Memoria dopo parsing: {current_memory:.1f} MB")
    print(f"  📈 Incremento: {current_memory - initial_memory:.1f} MB")
    
    # Test normalizzazione
    normalizer = TimestampNormalizationService()
    for i, record in enumerate(records[:100]):  # Primi 100 record
        if i % 20 == 0:
            normalized = normalizer.normalize_dict_record(record)
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"  📊 Memoria dopo normalizzazione: {final_memory:.1f} MB")
    print(f"  📈 Incremento totale: {final_memory - initial_memory:.1f} MB")


def main():
    """Esegue tutti i test diagnostici."""
    print("🚀 Debug file Mac_2k.log_structured.csv")
    print("=" * 60)
    
    # Test step by step
    step_success = test_parsing_step_by_step()
    
    # Test header detection
    test_csv_header_detection()
    
    # Test memoria
    test_memory_usage()
    
    if step_success:
        print("\n✅ Tutti i test completati con successo!")
        print("💡 Il problema potrebbe essere nella gestione di file grandi")
    else:
        print("\n❌ Test fallito - problema identificato")
    
    return step_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 