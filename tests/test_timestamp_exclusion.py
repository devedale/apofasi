#!/usr/bin/env python3
"""
Test per verificare l'esclusione di parsed_at dalla normalizzazione temporale.

Questo script testa che il campo parsed_at non interferisca
con la normalizzazione dei timestamp originali.
"""

import sys
import json
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from src.application.services.reporting_service_refactored import ReportingService


def test_timestamp_exclusion():
    """Test dell'esclusione di parsed_at."""
    print("🧪 Testando esclusione parsed_at...")
    
    # Crea directory di output temporanea
    test_output_dir = Path("test_timestamp_exclusion")
    test_output_dir.mkdir(exist_ok=True)
    
    # Inizializza il reporting service
    reporting_service = ReportingService(test_output_dir)
    
    # Crea dati di test con timestamp reali e parsed_at
    test_results = [
        {
            "success": True,
            "file_path": "test_logs.json",
            "detected_format": "json",
            "parsed_data": [
                {
                    "line_number": 1,
                    "raw_line": '{"timestamp": "2024-01-15T10:30:45Z", "message": "first event", "parsed_at": "2025-08-06T22:40:14.332223"}',
                    "parser_type": "json",
                    "timestamp": "2024-01-15T10:30:45Z",
                    "message": "first event",
                    "parsed_at": "2025-08-06T22:40:14.332223"  # Questo dovrebbe essere ignorato
                },
                {
                    "line_number": 2,
                    "raw_line": '{"timestamp": "2024-01-15T10:35:00Z", "message": "third event", "parsed_at": "2025-08-06T22:40:15.123456"}',
                    "parser_type": "json",
                    "timestamp": "2024-01-15T10:35:00Z",
                    "message": "third event",
                    "parsed_at": "2025-08-06T22:40:15.123456"  # Questo dovrebbe essere ignorato
                },
                {
                    "line_number": 3,
                    "raw_line": '{"timestamp": "2024-01-15T10:32:30Z", "message": "second event", "parsed_at": "2025-08-06T22:40:16.789012"}',
                    "parser_type": "json",
                    "timestamp": "2024-01-15T10:32:30Z",
                    "message": "second event",
                    "parsed_at": "2025-08-06T22:40:16.789012"  # Questo dovrebbe essere ignorato
                }
            ]
        }
    ]
    
    try:
        # Genera dati organizzati temporalmente
        print("📊 Generando dati temporali...")
        reporting_service.generate_temporal_organized_data(test_results)
        
        # Verifica il file temporale
        temporal_json = test_output_dir / "temporal_data.json"
        if temporal_json.exists():
            with open(temporal_json, 'r') as f:
                data = json.load(f)
            
            print(f"📝 Record nel file temporale: {len(data)}")
            
            # Verifica che i timestamp siano quelli originali, non parsed_at
            timestamps = []
            parsed_at_timestamps = []
            
            for record in data:
                normalized_ts = record.get('normalized_timestamp')
                parsed_at_ts = record.get('parsed_at')
                
                if normalized_ts:
                    timestamps.append(normalized_ts)
                if parsed_at_ts:
                    parsed_at_timestamps.append(parsed_at_ts)
            
            print(f"⏰ Timestamp normalizzati: {len(timestamps)}")
            print(f"📅 Primo timestamp normalizzato: {timestamps[0] if timestamps else 'N/A'}")
            print(f"📅 Ultimo timestamp normalizzato: {timestamps[-1] if timestamps else 'N/A'}")
            
            print(f"🔄 Timestamp parsed_at: {len(parsed_at_timestamps)}")
            print(f"📅 Primo parsed_at: {parsed_at_timestamps[0] if parsed_at_timestamps else 'N/A'}")
            print(f"📅 Ultimo parsed_at: {parsed_at_timestamps[-1] if parsed_at_timestamps else 'N/A'}")
            
            # Verifica che i timestamp normalizzati siano quelli originali (2024-01-15)
            # e non quelli di processing (2025-08-06)
            if timestamps:
                original_timestamps = [ts for ts in timestamps if ts.startswith('2024-01-15')]
                processing_timestamps = [ts for ts in timestamps if ts.startswith('2025-08-06')]
                
                print(f"📅 Timestamp originali (2024): {len(original_timestamps)}")
                print(f"📅 Timestamp processing (2025): {len(processing_timestamps)}")
                
                if len(original_timestamps) > 0 and len(processing_timestamps) == 0:
                    print("✅ parsed_at escluso correttamente!")
                    print("✅ Timestamp originali utilizzati per la normalizzazione")
                    return True
                else:
                    print("❌ parsed_at non escluso correttamente")
                    print("❌ Timestamp di processing utilizzati invece di quelli originali")
                    return False
            else:
                print("❌ Nessun timestamp trovato")
                return False
        else:
            print("❌ File temporale non trovato")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Pulisci i file di test
        import shutil
        if test_output_dir.exists():
            shutil.rmtree(test_output_dir)


def main():
    """Esegue il test."""
    print("🚀 Test esclusione parsed_at")
    print("=" * 50)
    
    success = test_timestamp_exclusion()
    
    if success:
        print("\n🎉 Test completato con successo!")
        print("✅ parsed_at viene escluso correttamente dalla normalizzazione")
    else:
        print("\n⚠️  Test fallito!")
        print("❌ parsed_at interferisce ancora con la normalizzazione")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 