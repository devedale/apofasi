#!/usr/bin/env python3
"""
Test per l'organizzazione temporale degli output.

Questo script testa la funzionalità di riorganizzazione temporale
degli output del CLI parser.
"""

import sys
import json
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from src.application.services.reporting_service_refactored import ReportingService


def test_temporal_organization():
    """Test dell'organizzazione temporale."""
    print("🧪 Testando organizzazione temporale...")
    
    # Crea directory di output temporanea
    test_output_dir = Path("test_temporal_output")
    test_output_dir.mkdir(exist_ok=True)
    
    # Inizializza il reporting service
    reporting_service = ReportingService(test_output_dir)
    
    # Crea dati di test
    test_results = [
        {
            "success": True,
            "file_path": "test1.csv",
            "detected_format": "adaptive_csv",
            "parsed_data": [
                {
                    "line_number": 1,
                    "raw_line": '{"timestamp": "2024-01-15T10:30:45Z", "message": "first"}',
                    "parser_type": "adaptive_csv",
                    "parsed_at": "2024-01-15T10:30:45Z",
                    "session_id": "SID_00001",
                    "network_packet_size": "599",
                    "protocol_type": "TCP"
                },
                {
                    "line_number": 2,
                    "raw_line": '{"timestamp": "2024-01-15T10:35:00Z", "message": "third"}',
                    "parser_type": "adaptive_csv",
                    "parsed_at": "2024-01-15T10:35:00Z",
                    "session_id": "SID_00002",
                    "network_packet_size": "472",
                    "protocol_type": "UDP"
                },
                {
                    "line_number": 3,
                    "raw_line": '{"timestamp": "2024-01-15T10:32:30Z", "message": "second"}',
                    "parser_type": "adaptive_csv",
                    "parsed_at": "2024-01-15T10:32:30Z",
                    "session_id": "SID_00003",
                    "network_packet_size": "800",
                    "protocol_type": "TCP"
                }
            ]
        }
    ]
    
    try:
        # Genera dati organizzati temporalmente
        print("📊 Generando dati temporali...")
        reporting_service.generate_temporal_organized_data(test_results)
        
        # Verifica che i file siano stati creati
        temporal_files = [
            "temporal_data.json",
            "temporal_data.csv", 
            "temporal_data_anonymized.json",
            "temporal_data_anonymized.csv",
            "temporal_statistics.json"
        ]
        
        created_files = []
        for filename in temporal_files:
            file_path = test_output_dir / filename
            if file_path.exists():
                created_files.append(filename)
                print(f"  ✅ {filename} creato")
            else:
                print(f"  ❌ {filename} mancante")
        
        if len(created_files) == len(temporal_files):
            print(f"✅ Tutti i file temporali creati ({len(created_files)}/{len(temporal_files)})")
            
            # Verifica il contenuto del file JSON
            temporal_json = test_output_dir / "temporal_data.json"
            if temporal_json.exists():
                with open(temporal_json, 'r') as f:
                    data = json.load(f)
                
                print(f"📝 Record nel file temporale: {len(data)}")
                
                # Verifica che i record siano ordinati temporalmente
                timestamps = [record.get('normalized_timestamp') for record in data if record.get('normalized_timestamp')]
                if timestamps:
                    print(f"⏰ Timestamp trovati: {len(timestamps)}")
                    print(f"📅 Primo timestamp: {timestamps[0]}")
                    print(f"📅 Ultimo timestamp: {timestamps[-1]}")
                    
                    # Verifica che siano ordinati
                    sorted_timestamps = sorted(timestamps)
                    if timestamps == sorted_timestamps:
                        print("✅ Record ordinati temporalmente")
                        return True
                    else:
                        print("❌ Record non ordinati temporalmente")
                        return False
                else:
                    print("⚠️  Nessun timestamp trovato")
                    return False
            else:
                print("❌ File JSON temporale non trovato")
                return False
        else:
            print(f"❌ Solo {len(created_files)}/{len(temporal_files)} file creati")
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
    print("🚀 Test organizzazione temporale")
    print("=" * 50)
    
    success = test_temporal_organization()
    
    if success:
        print("\n🎉 Test completato con successo!")
        print("✅ L'organizzazione temporale funziona correttamente")
    else:
        print("\n⚠️  Test fallito!")
        print("❌ L'organizzazione temporale ha problemi")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 