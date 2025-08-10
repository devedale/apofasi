"""
Debug Unparsed Records - Analisi dei record non parsati

Questo script analizza i record non parsati per capire
perché ci sono errori e warning durante il parsing.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.core import LoggerService, MetricsService, CacheService, ValidatorService, CacheStrategy
from src.infrastructure.parsers import create_specific_parser


def analyze_unparsed_records(file_path: str, parser_type: str = 'adaptive'):
    """
    Analizza i record non parsati per un file specifico.
    
    WHY: Per capire perché alcuni record non vengono parsati
    correttamente e identificare pattern di errore.
    
    Args:
        file_path: Percorso del file da analizzare
        parser_type: Tipo di parser da utilizzare
    """
    print(f"🔍 Analizzando record non parsati per: {file_path}")
    print("=" * 80)
    
    # Setup servizi
    logger = LoggerService(log_level="DEBUG", console_output=True)
    metrics = MetricsService(auto_collect=False)
    cache = CacheService(strategy=CacheStrategy.MEMORY, max_size=1024*1024)
    validator = ValidatorService(validation_level="basic")
    
    # Leggi il file
    path = Path(file_path)
    if not path.exists():
        print(f"❌ File non trovato: {file_path}")
        return
    
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    print(f"📄 Contenuto file: {len(content)} caratteri")
    print(f"📊 Righe totali: {len(content.splitlines())}")
    
    # Crea parser
    parser = create_specific_parser(parser_type)
    if not parser:
        print(f"❌ Parser {parser_type} non disponibile")
        return
    
    # Parsing con debug
    print(f"\n🔧 Parsing con {parser_type}...")
    
    try:
        parsed_records = list(parser.parse(content, str(path)))
        print(f"✅ Record parsati: {len(parsed_records)}")
        
        # Analizza i record parsati
        if parsed_records:
            print(f"\n📋 PRIMO RECORD PARSATO:")
            first_record = parsed_records[0]
            for key, value in first_record.items():
                print(f"   {key}: {value}")
        
        # Analizza record non parsati
        lines = content.splitlines()
        parsed_lines = len(parsed_records)
        unparsed_lines = len(lines) - parsed_lines
        
        print(f"\n📊 STATISTICHE PARSING:")
        print(f"   📄 Righe totali: {len(lines)}")
        print(f"   ✅ Righe parsate: {parsed_lines}")
        print(f"   ❌ Righe non parsate: {unparsed_lines}")
        print(f"   📈 Success rate: {(parsed_lines/len(lines)*100):.1f}%")
        
        # Trova righe non parsate
        if unparsed_lines > 0:
            print(f"\n❌ PRIME 10 RIGHE NON PARSATE:")
            for i, line in enumerate(lines):
                if i >= 10:  # Mostra solo le prime 10
                    break
                if line.strip():  # Ignora righe vuote
                    # Verifica se questa riga è stata parsata
                    line_parsed = False
                    for record in parsed_records:
                        if any(line in str(value) for value in record.values()):
                            line_parsed = True
                            break
                    
                    if not line_parsed:
                        print(f"   [{i+1}] {line[:100]}{'...' if len(line) > 100 else ''}")
        
        # Validazione risultati
        print(f"\n🔍 VALIDAZIONE RISULTATI:")
        validation_result = validator.validate_data(parsed_records)
        
        if validation_result.get('errors'):
            print(f"   ❌ Errori di validazione: {len(validation_result['errors'])}")
            for error in validation_result['errors'][:5]:  # Primi 5 errori
                print(f"      - {error}")
        else:
            print("   ✅ Nessun errore di validazione")
        
        if validation_result.get('warnings'):
            print(f"   ⚠️  Warning di validazione: {len(validation_result['warnings'])}")
            for warning in validation_result['warnings'][:5]:  # Primi 5 warning
                print(f"      - {warning}")
        else:
            print("   ✅ Nessun warning di validazione")
        
        # Analisi dettagliata per parser adattivo
        if parser_type == 'adaptive' and hasattr(parser, '_identify_structure'):
            print(f"\n🔬 ANALISI STRUTTURA (Adaptive Parser):")
            try:
                # Analizza la struttura identificata
                structure = parser._identify_structure(content)
                if structure:
                    print(f"   📐 Separatore identificato: '{structure.separator}'")
                    print(f"   📊 Campi identificati: {len(structure.fields)}")
                    print(f"   🎯 Confidence: {structure.confidence:.2f}")
                    
                    for field in structure.fields[:5]:  # Primi 5 campi
                        print(f"      - {field.name} ({field.field_type}): {field.confidence:.2f}")
                else:
                    print("   ❌ Nessuna struttura identificata")
            except Exception as e:
                print(f"   ❌ Errore analisi struttura: {e}")
        
    except Exception as e:
        print(f"❌ Errore durante il parsing: {e}")
        import traceback
        traceback.print_exc()


def analyze_multiple_files():
    """Analizza più file per identificare pattern comuni."""
    print("🔍 ANALISI MULTIPLA FILE")
    print("=" * 80)
    
    # File di esempio da analizzare
    test_files = [
        "examples/example_syslog.txt",
        "examples/example_csv.csv", 
        "examples/example_json.json",
        "examples/loghub/Android/Android_2k.log",
        "examples/loghub/Apache/Apache_2k.log"
    ]
    
    for file_path in test_files:
        if Path(file_path).exists():
            print(f"\n{'='*40}")
            analyze_unparsed_records(file_path, 'adaptive')
        else:
            print(f"\n❌ File non trovato: {file_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Analizza file specifico
        file_path = sys.argv[1]
        parser_type = sys.argv[2] if len(sys.argv) > 2 else 'adaptive'
        analyze_unparsed_records(file_path, parser_type)
    else:
        # Analisi multipla
        analyze_multiple_files() 