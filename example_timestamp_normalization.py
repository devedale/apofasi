#!/usr/bin/env python3
"""
Esempio pratico di normalizzazione temporale.

Questo script dimostra come utilizzare il servizio di normalizzazione
temporale per ordinare i log rispetto al tempo.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from src.domain.services.timestamp_normalization_service import TimestampNormalizationService
from src.domain.entities.parsed_record import ParsedRecord


def create_sample_records():
    """Crea record di esempio con diversi formati di timestamp."""
    return [
        # JSON con timestamp ISO
        ParsedRecord(
            original_content='{"timestamp": "2024-01-15T10:30:45.123Z", "level": "ERROR", "message": "Database connection failed"}',
            parsed_data={
                "timestamp": "2024-01-15T10:30:45.123Z",
                "level": "ERROR",
                "message": "Database connection failed"
            },
            parser_name="json",
            source_file=Path("app.log"),
            line_number=1
        ),
        
        # Syslog RFC3164
        ParsedRecord(
            original_content='<134>Jan 15 10:32:30 server1 sshd[1234]: Failed password for user admin from 192.168.1.100',
            parsed_data={
                "priority": "134",
                "timestamp": "Jan 15 10:32:30",
                "hostname": "server1",
                "tag": "sshd",
                "pid": "1234",
                "message": "Failed password for user admin from 192.168.1.100"
            },
            parser_name="syslog",
            source_file=Path("auth.log"),
            line_number=45
        ),
        
        # LogHub format
        ParsedRecord(
            original_content='20240115-10:35:15:456|firewall|12345|Blocked connection from suspicious IP',
            parsed_data={
                "timestamp": "20240115-10:35:15:456",
                "component": "firewall",
                "user_id": "12345",
                "message": "Blocked connection from suspicious IP"
            },
            parser_name="loghub",
            source_file=Path("firewall.log"),
            line_number=12
        ),
        
        # Standard format
        ParsedRecord(
            original_content='2024-01-15 10:37:00 WARNING: High CPU usage detected',
            parsed_data={
                "timestamp": "2024-01-15 10:37:00",
                "level": "WARNING",
                "message": "High CPU usage detected"
            },
            parser_name="standard",
            source_file=Path("system.log"),
            line_number=78
        ),
        
        # Record senza timestamp (verrà assegnato timestamp di processing)
        ParsedRecord(
            original_content='Application started successfully',
            parsed_data={
                "message": "Application started successfully"
            },
            parser_name="fallback",
            source_file=Path("app.log"),
            line_number=100
        )
    ]


def demonstrate_timestamp_normalization():
    """Dimostra la normalizzazione temporale."""
    print("🕐 DIMOSTRAZIONE NORMALIZZAZIONE TEMPORALE")
    print("=" * 60)
    
    # Inizializza il servizio
    normalizer = TimestampNormalizationService()
    
    # Crea record di esempio
    records = create_sample_records()
    
    print("📝 Record originali (non ordinati):")
    for i, record in enumerate(records, 1):
        timestamp = record.timestamp
        message = record.parsed_data.get("message", "N/A")
        parser = record.parser_name
        print(f"  {i}. [{parser}] {timestamp} - {message}")
    
    print("\n🔧 Normalizzazione timestamp...")
    
    # Normalizza tutti i record
    normalized_records = []
    for record in records:
        normalized_record = normalizer.normalize_parsed_record(record)
        normalized_records.append(normalized_record)
        
        # Mostra informazioni di normalizzazione
        timestamp_info = normalized_record.parsed_data.get("timestamp_info", {})
        confidence = timestamp_info.get("confidence", 0.0)
        source = timestamp_info.get("source", "unknown")
        
        print(f"  ✅ {record.parser_name}: {normalized_record.timestamp} (confidence: {confidence:.2f}, source: {source})")
    
    print("\n📅 Ordinamento per timestamp normalizzato...")
    
    # Ordina i record per timestamp
    sorted_records = normalizer.sort_records_by_timestamp(normalized_records)
    
    print("📊 Record ordinati cronologicamente:")
    for i, record in enumerate(sorted_records, 1):
        timestamp = record.timestamp
        message = record.parsed_data.get("message", "N/A")
        parser = record.parser_name
        confidence = record.parsed_data.get("timestamp_info", {}).get("confidence", 0.0)
        
        if timestamp:
            print(f"  {i}. [{parser}] {timestamp.isoformat()} (confidence: {confidence:.2f}) - {message}")
        else:
            print(f"  {i}. [{parser}] NO TIMESTAMP - {message}")
    
    print("\n📈 Statistiche timeline:")
    stats = normalizer.get_timeline_statistics(sorted_records)
    
    print(f"  📝 Total records: {stats['total_records']}")
    print(f"  ⏰ Records with timestamp: {stats['records_with_timestamp']}")
    print(f"  📈 Timestamp coverage: {stats['timestamp_coverage']:.1%}")
    print(f"  🎯 Average confidence: {stats['average_confidence']:.2f}")
    
    if stats['time_span']:
        print(f"  ⏱️  Time span: {stats['time_span']['start']} to {stats['time_span']['end']}")
        print(f"  ⏱️  Duration: {stats['time_span']['duration_seconds']:.1f} seconds")
    
    return sorted_records


def demonstrate_confidence_hierarchy():
    """Dimostra la gerarchia di attendibilità dei timestamp."""
    print("\n🎯 GERARCHIA DI ATTENDIBILITÀ TIMESTAMP")
    print("=" * 60)
    
    normalizer = TimestampNormalizationService()
    
    # Esempi con diversi livelli di attendibilità
    examples = [
        {
            "name": "Timestamp esplicito in JSON",
            "content": '{"timestamp": "2024-01-15T10:30:45Z", "message": "test"}',
            "expected_confidence": 0.85,
            "description": "Timestamp esplicito nei dati parsati"
        },
        {
            "name": "Pattern recognition ISO 8601",
            "content": '2024-01-15T10:30:45.123Z test message',
            "expected_confidence": 0.95,
            "description": "Timestamp riconosciuto tramite pattern"
        },
        {
            "name": "Pattern recognition Syslog",
            "content": 'Jan 15 10:30:45 server1 test message',
            "expected_confidence": 0.8,
            "description": "Timestamp syslog riconosciuto"
        },
        {
            "name": "Solo data",
            "content": '2024-01-15 test message',
            "expected_confidence": 0.6,
            "description": "Solo data, ora inferita"
        },
        {
            "name": "Nessun timestamp",
            "content": 'test message without timestamp',
            "expected_confidence": 0.3,
            "description": "Timestamp di processing assegnato"
        }
    ]
    
    print("📊 Confronto livelli di attendibilità:")
    for example in examples:
        record = ParsedRecord(
            original_content=example["content"],
            parsed_data={"message": "test"},
            parser_name="test",
            source_file=Path("test.log"),
            line_number=1
        )
        
        normalized_record = normalizer.normalize_parsed_record(record)
        timestamp_info = normalized_record.parsed_data.get("timestamp_info", {})
        confidence = timestamp_info.get("confidence", 0.0)
        source = timestamp_info.get("source", "unknown")
        
        print(f"  📝 {example['name']}")
        print(f"     Confidence: {confidence:.2f} (expected: {example['expected_confidence']:.2f})")
        print(f"     Source: {source}")
        print(f"     Timestamp: {normalized_record.timestamp}")
        print()


def main():
    """Esegue la dimostrazione completa."""
    print("🚀 DIMOSTRAZIONE NORMALIZZAZIONE TEMPORALE")
    print("=" * 60)
    
    # Dimostra normalizzazione e ordinamento
    sorted_records = demonstrate_timestamp_normalization()
    
    # Dimostra gerarchia di attendibilità
    demonstrate_confidence_hierarchy()
    
    print("✅ Dimostrazione completata!")
    print("\n💡 Punti chiave:")
    print("  • Ogni record ottiene un timestamp normalizzato")
    print("  • Gerarchia di attendibilità: esplicito > pattern > processing")
    print("  • Ordinamento cronologico automatico")
    print("  • Statistiche timeline per analisi")
    print("  • Compatibilità con tutti i formati di log")


if __name__ == "__main__":
    main() 