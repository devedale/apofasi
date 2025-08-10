#!/usr/bin/env python3
"""
Test per la normalizzazione temporale.

Questo script testa il servizio di normalizzazione temporale
con diversi formati di timestamp per verificare la corretta
estrazione e normalizzazione.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from src.domain.services.timestamp_normalization_service import TimestampNormalizationService
from src.domain.entities.parsed_record import ParsedRecord


def test_timestamp_normalization():
    """Test della normalizzazione temporale."""
    print("🧪 Testando normalizzazione temporale...")
    
    # Inizializza il servizio
    normalizer = TimestampNormalizationService()
    
    # Test cases con diversi formati di timestamp
    test_cases = [
        # ISO 8601 completo
        {
            "content": '{"timestamp": "2024-01-15T10:30:45.123Z", "message": "test"}',
            "expected_confidence": 0.85,
            "description": "ISO 8601 con timezone"
        },
        # ISO 8601 senza timezone
        {
            "content": '{"timestamp": "2024-01-15T10:30:45.123", "message": "test"}',
            "expected_confidence": 0.85,
            "description": "ISO 8601 senza timezone"
        },
        # Formato syslog RFC3164
        {
            "content": '<134>Jan 15 10:30:45 server1 sshd[1234]: Failed password for user admin',
            "expected_confidence": 0.8,
            "description": "Syslog RFC3164"
        },
        # Formato loghub
        {
            "content": '20240115-10:30:45:123|component|12345|test message',
            "expected_confidence": 0.75,
            "description": "LogHub format"
        },
        # Formato standard con spazio
        {
            "content": '2024-01-15 10:30:45 ERROR: test message',
            "expected_confidence": 0.85,
            "description": "Standard format with space"
        },
        # Solo data
        {
            "content": '2024-01-15 test message',
            "expected_confidence": 0.6,
            "description": "Date only"
        },
        # Nessun timestamp
        {
            "content": 'test message without timestamp',
            "expected_confidence": 0.0,
            "description": "No timestamp"
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}/{total_tests}: {test_case['description']}")
        
        # Crea un record di test
        record = ParsedRecord(
            original_content=test_case["content"],
            parsed_data={"message": "test"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=1
        )
        
        # Normalizza il record
        normalized_record = normalizer.normalize_parsed_record(record)
        
        # Verifica il risultato
        timestamp_info = normalized_record.parsed_data.get("timestamp_info", {})
        confidence = timestamp_info.get("confidence", 0.0)
        source = timestamp_info.get("source", "none")
        
        print(f"  📊 Confidence: {confidence:.2f} (expected: {test_case['expected_confidence']:.2f})")
        print(f"  🔍 Source: {source}")
        print(f"  ⏰ Timestamp: {normalized_record.timestamp}")
        
        # Verifica che la confidence sia almeno quella attesa
        if confidence >= test_case["expected_confidence"]:
            print(f"  ✅ PASS")
            passed_tests += 1
        else:
            print(f"  ❌ FAIL - Confidence too low")
    
    print(f"\n📊 Risultati: {passed_tests}/{total_tests} test passati")
    return passed_tests == total_tests


def test_timestamp_sorting():
    """Test dell'ordinamento temporale."""
    print("\n🧪 Testando ordinamento temporale...")
    
    normalizer = TimestampNormalizationService()
    
    # Crea record con timestamp diversi
    records = [
        ParsedRecord(
            original_content='{"timestamp": "2024-01-15T10:30:45Z", "message": "first"}',
            parsed_data={"timestamp": "2024-01-15T10:30:45Z", "message": "first"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=1
        ),
        ParsedRecord(
            original_content='{"timestamp": "2024-01-15T10:35:00Z", "message": "third"}',
            parsed_data={"timestamp": "2024-01-15T10:35:00Z", "message": "third"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=3
        ),
        ParsedRecord(
            original_content='{"timestamp": "2024-01-15T10:32:30Z", "message": "second"}',
            parsed_data={"timestamp": "2024-01-15T10:32:30Z", "message": "second"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=2
        ),
        ParsedRecord(
            original_content='test message without timestamp',
            parsed_data={"message": "no timestamp"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=4
        )
    ]
    
    # Ordina i record
    sorted_records = normalizer.sort_records_by_timestamp(records)
    
    print("📅 Record ordinati per timestamp:")
    for i, record in enumerate(sorted_records, 1):
        timestamp = record.timestamp
        message = record.parsed_data.get("message", "unknown")
        if timestamp:
            print(f"  {i}. {timestamp.isoformat()} - {message}")
        else:
            print(f"  {i}. NO TIMESTAMP - {message}")
    
    # Verifica che l'ordinamento sia corretto
    timestamps = [r.timestamp for r in sorted_records if r.timestamp]
    is_sorted = timestamps == sorted(timestamps)
    
    if is_sorted:
        print("  ✅ Ordinamento corretto")
        return True
    else:
        print("  ❌ Ordinamento errato")
        return False


def test_timeline_statistics():
    """Test delle statistiche della timeline."""
    print("\n🧪 Testando statistiche timeline...")
    
    normalizer = TimestampNormalizationService()
    
    # Crea record di test
    records = [
        ParsedRecord(
            original_content='{"timestamp": "2024-01-15T10:30:45Z", "message": "first"}',
            parsed_data={"timestamp": "2024-01-15T10:30:45Z", "message": "first"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=1
        ),
        ParsedRecord(
            original_content='{"timestamp": "2024-01-15T10:35:00Z", "message": "second"}',
            parsed_data={"timestamp": "2024-01-15T10:35:00Z", "message": "second"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=2
        ),
        ParsedRecord(
            original_content='test message without timestamp',
            parsed_data={"message": "no timestamp"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=3
        )
    ]
    
    # Calcola statistiche
    stats = normalizer.get_timeline_statistics(records)
    
    print("📊 Statistiche timeline:")
    print(f"  📝 Total records: {stats['total_records']}")
    print(f"  ⏰ Records with timestamp: {stats['records_with_timestamp']}")
    print(f"  📈 Timestamp coverage: {stats['timestamp_coverage']:.2%}")
    print(f"  🎯 Average confidence: {stats['average_confidence']:.2f}")
    
    if stats['time_span']:
        print(f"  ⏱️  Time span: {stats['time_span']['start']} to {stats['time_span']['end']}")
        print(f"  ⏱️  Duration: {stats['time_span']['duration_seconds']:.1f} seconds")
    
    # Verifica che le statistiche siano ragionevoli
    expected_coverage = 2/3  # 2 record con timestamp su 3 totali
    if abs(stats['timestamp_coverage'] - expected_coverage) < 0.1:
        print("  ✅ Statistiche corrette")
        return True
    else:
        print("  ❌ Statistiche errate")
        return False


def main():
    """Esegue tutti i test."""
    print("🚀 Avvio test normalizzazione temporale...")
    
    # Esegui i test
    test1_passed = test_timestamp_normalization()
    test2_passed = test_timestamp_sorting()
    test3_passed = test_timeline_statistics()
    
    # Risultati finali
    print("\n" + "="*50)
    print("📊 RISULTATI FINALI")
    print("="*50)
    
    tests = [
        ("Normalizzazione timestamp", test1_passed),
        ("Ordinamento temporale", test2_passed),
        ("Statistiche timeline", test3_passed)
    ]
    
    passed = 0
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Totale: {passed}/{len(tests)} test passati")
    
    if passed == len(tests):
        print("🎉 Tutti i test sono passati!")
        return True
    else:
        print("⚠️  Alcuni test sono falliti!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 