"""
Debug Parser Availability

Script per debuggare i parser disponibili e il loro funzionamento.
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.parsers import get_available_parsers, create_specific_parser


def test_parser_availability():
    """Testa la disponibilità e funzionamento dei parser."""
    
    print("🔍 Test Parser Availability")
    print("=" * 50)
    
    # Ottieni parser disponibili
    available_parsers = get_available_parsers()
    print(f"📋 Parser disponibili: {available_parsers}")
    
    # Testa creazione di ogni parser
    for parser_name in available_parsers:
        print(f"\n🧪 Testando parser: {parser_name}")
        
        try:
            parser = create_specific_parser(parser_name)
            if parser:
                print(f"   ✅ Parser creato con successo")
                print(f"   📝 Tipo: {type(parser).__name__}")
                
                # Testa can_parse con contenuto di esempio
                test_content = "2024-01-15T10:30:45.123Z server1 kernel: [ERROR] Out of memory"
                can_parse_result = parser.can_parse(test_content, "test.txt")
                print(f"   🔍 can_parse() risultato: {can_parse_result}")
            else:
                print(f"   ❌ Parser non creato")
        except Exception as e:
            print(f"   ❌ Errore creazione parser: {e}")


if __name__ == "__main__":
    test_parser_availability() 