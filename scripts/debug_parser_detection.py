"""
Debug Parser Detection

Script per debuggare il rilevamento automatico dei parser.
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.parsers import (
    get_available_parsers, create_specific_parser
)


def test_parser_detection():
    """Testa il rilevamento dei parser su file specifici."""
    
    # File di test
    test_files = {
        'examples/example_syslog.txt': 'syslog',
        'examples/FGT80FTK22013405.root.tlog.txt': 'fortinet',
        'examples/FGT80FTK22013405.root.elog.txt': 'fortinet'
    }
    
    available_parsers = get_available_parsers()
    print(f"Parser disponibili: {available_parsers}")
    
    for file_path_str, expected_parser in test_files.items():
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            print(f"❌ File non trovato: {file_path}")
            continue
        
        print(f"\n🧪 Testando {file_path.name} (atteso: {expected_parser})")
        
        # Leggi le prime righe
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample_lines = []
            for i, line in enumerate(f):
                if i >= 5:
                    break
                sample_lines.append(line.strip())
        
        sample_content = '\n'.join(sample_lines)
        print(f"📄 Prime righe: {sample_content[:200]}...")
        
        # Testa ogni parser
        for parser_name in available_parsers:
            try:
                parser = create_specific_parser(parser_name)
                if parser:
                    can_parse = parser.can_parse(sample_content, str(file_path))
                    status = "✅" if can_parse else "❌"
                    print(f"   {status} {parser_name}: {can_parse}")
                    
                    if can_parse and parser_name == expected_parser:
                        print(f"   🎯 CORRETTO! {parser_name} rilevato per {file_path.name}")
                    elif can_parse:
                        print(f"   ⚠️  INASPETTATO! {parser_name} rilevato invece di {expected_parser}")
                else:
                    print(f"   ❌ {parser_name}: Parser non disponibile")
                    
            except Exception as e:
                print(f"   ❌ {parser_name}: Errore - {e}")


if __name__ == "__main__":
    test_parser_detection() 