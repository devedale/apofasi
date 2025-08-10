#!/usr/bin/env python3
"""
Debug script per identificare la causa del loop nei file grandi.
"""

import sys
import time
import signal
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.services.pattern_detection_service import PatternDetectionService
from src.infrastructure.parsers.adaptive_parser import AdaptiveParser
from src.domain.entities.log_entry import LogEntry

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Operazione interrotta per timeout")

def test_component(name, func, timeout_seconds=10):
    """Testa un componente con timeout per identificare loop"""
    print(f"\n=== Testing {name} ===")
    
    # Setup timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        start_time = time.time()
        result = func()
        elapsed = time.time() - start_time
        print(f"✅ {name}: OK ({elapsed:.2f}s)")
        return result
    except TimeoutException:
        print(f"❌ {name}: TIMEOUT dopo {timeout_seconds}s - LOOP RILEVATO!")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ {name}: ERROR ({elapsed:.2f}s) - {e}")
        return None
    finally:
        signal.alarm(0)  # Cancel timeout

def main():
    """Test sistematico dei componenti"""
    
    # Leggi una parte del file problematico
    csv_file = Path("examples/ai_ml_cybersecurity_dataset.csv")
    if not csv_file.exists():
        print("❌ File CSV non trovato")
        return
    
    print(f"📄 Analizzando: {csv_file} ({csv_file.stat().st_size / 1024 / 1024:.1f}MB)")
    
    # Leggi prime righe
    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = []
        for i, line in enumerate(f):
            if i >= 5:  # Prime 5 righe
                break
            lines.append(line.strip())
    
    if not lines:
        print("❌ File vuoto")
        return
    
    print(f"📊 Caricate {len(lines)} righe di test")
    
    # Test 1: Pattern Detection Service standalone
    def test_pattern_detection():
        service = PatternDetectionService()
        results = []
        for line in lines:
            if line:  # Skip empty lines
                result = service._detect_patterns(line)
                results.append(result)
        return results
    
    pattern_results = test_component("PatternDetectionService._detect_patterns", test_pattern_detection, 15)
    
    # Test 2: Drain3 standalone
    def test_drain3():
        from drain3 import TemplateMiner
        miner = TemplateMiner()
        results = []
        for line in lines:
            if line:
                result = miner.add_log_message(line)
                results.append(result)
        return results
    
    drain_results = test_component("Drain3.TemplateMiner", test_drain3, 15)
    
    # Test 3: Full Pattern Detection Service
    def test_full_pattern_service():
        service = PatternDetectionService()
        results = []
        for line in lines:
            if line:
                result = service.add_template_and_patterns(line, {})
                results.append(result)
        return results
    
    full_results = test_component("PatternDetectionService.add_template_and_patterns", test_full_pattern_service, 20)
    
    # Test 4: Adaptive Parser completo
    def test_adaptive_parser():
        parser = AdaptiveParser()
        results = []
        for i, line in enumerate(lines):
            if line:
                log_entry = LogEntry(content=line, source_file=csv_file, line_number=i+1)
                result = list(parser.parse(log_entry))
                results.extend(result)
        return results
    
    parser_results = test_component("AdaptiveParser.parse", test_adaptive_parser, 30)
    
    # Report finale
    print(f"\n" + "="*50)
    print("🎯 RISULTATI ANALISI LOOP:")
    print(f"   Pattern Detection: {'✅ OK' if pattern_results else '❌ PROBLEMATICO'}")
    print(f"   Drain3 Miner: {'✅ OK' if drain_results else '❌ PROBLEMATICO'}")
    print(f"   Full Service: {'✅ OK' if full_results else '❌ PROBLEMATICO'}")
    print(f"   Adaptive Parser: {'✅ OK' if parser_results else '❌ PROBLEMATICO'}")
    
    # Se qualcosa è problematico, mostra le prime righe per debug
    if not (pattern_results and drain_results and full_results and parser_results):
        print(f"\n📝 Prime righe del file per debug:")
        for i, line in enumerate(lines[:3]):
            print(f"   [{i+1}] {line[:100]}{'...' if len(line) > 100 else ''}")

if __name__ == "__main__":
    main()
