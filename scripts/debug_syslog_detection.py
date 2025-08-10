"""
Script di debug per testare il rilevamento di Syslog tramite il MultiStrategyParser.

Questo script carica un file di log, lo passa al MultiStrategyParser e stampa i risultati,
consentendo di verificare se i pattern regex per syslog vengono applicati correttamente.
"""
import yaml
from pathlib import Path
import sys

# Aggiunge il percorso principale del progetto per importare i moduli correttamente
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.infrastructure.parsers.multi_strategy_parser import MultiStrategyParser
from src.domain.entities.log_entry import LogEntry

def debug_syslog_parsing(file_path: Path):
    """
    Esegue il parsing di un file di log e stampa i risultati per il debug.
    """
    print(f"--- 🧪  Debug Syslog Parsing per il file: {file_path} ---")

    if not file_path.exists():
        print(f"❌ Errore: Il file {file_path} non esiste.")
        return

    # Carica una configurazione di base per il parser
    config = {'config_path': 'config/parser_config.yaml'}
    parser = MultiStrategyParser(config)
    
    print(f"✅ Parser {parser.name} inizializzato.")
    print("--- Inizio Parsing ---")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                
                log_entry = LogEntry(content=line, source_file=file_path, line_number=i + 1)
                
                print(f"\n[L:{i+1}] Original: {line}")
                
                parsed_records = list(parser.parse(log_entry))
                
                if parsed_records:
                    for record in parsed_records:
                        print(f"  Parser: {record.parser_name}")
                        print(f"  Parsed Data: {record.parsed_data}")
                        if record.errors:
                            print(f"  Errors: {record.errors}")
                else:
                    print("  ❌ Nessun record prodotto dal parser.")
                print("-" * 20)

    except Exception as e:
        print(f"\n--- 💥 Errore Critico Durante il Parsing ---")
        print(f"Errore: {e}")

    print("\n--- ✅ Debug completato ---")

if __name__ == "__main__":
    # Esempio di utilizzo: python scripts/debug_syslog_detection.py examples/example_syslog.txt
    if len(sys.argv) > 1:
        file_to_debug = Path(sys.argv[1])
        debug_syslog_parsing(file_to_debug)
    else:
        print("Usage: python scripts/debug_syslog_detection.py <path_to_log_file>")
        # Esegue un test con un file di default se non specificato
        default_file = Path("examples/example_syslog.txt")
        if default_file.exists():
            print(f"\n--- 🧪  Esecuzione con file di default: {default_file} ---")
            debug_syslog_parsing(default_file)
