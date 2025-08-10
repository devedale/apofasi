#!/usr/bin/env python3
"""
Test del RegexManager per gestione dinamica pattern.
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from src.core.services.regex_manager import RegexManager


def test_regex_manager():
    """Test del RegexManager."""
    print("🧪 Testando RegexManager...")
    
    # Inizializza il manager
    manager = RegexManager()
    
    # Test 1: Statistiche iniziali
    print("\n📊 Statistiche iniziali:")
    stats = manager.get_statistics()
    print(f"   - Pattern totali: {stats['total_patterns']}")
    print(f"   - Categorie: {stats['categories']}")
    
    # Test 2: Aggiungi nuovo pattern
    print("\n➕ Test aggiunta pattern:")
    success = manager.add_pattern(
        category='anonymization',
        name='test_custom_ip',
        pattern=r'\b(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)\d+\.\d+\b',
        replacement='<PRIVATE_IP>',
        priority=5,
        description='Private IP addresses'
    )
    print(f"   - Pattern aggiunto: {'✅' if success else '❌'}")
    
    # Test 3: Valida pattern
    print("\n🔍 Test validazione pattern:")
    result = manager.validate_pattern(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
    print(f"   - Pattern valido: {'✅' if result['valid'] else '❌'}")
    if not result['valid']:
        print(f"   - Errore: {result['error']}")
    
    # Test 4: Test pattern
    print("\n🧪 Test pattern su testo:")
    test_text = "IP: 192.168.1.100, 10.0.0.1, 172.16.0.1"
    result = manager.test_pattern(r'\b(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)\d+\.\d+\b', test_text)
    print(f"   - Pattern valido: {'✅' if result['valid'] else '❌'}")
    if result['valid']:
        print(f"   - Match count: {result['match_count']}")
        print(f"   - Matches: {result['matches']}")
    
    # Test 5: Lista pattern
    print("\n📋 Lista pattern anonymization:")
    patterns = manager.list_patterns('anonymization')
    for name, config in list(patterns.items())[:5]:  # Mostra solo i primi 5
        print(f"   - {name}: {config.get('description', 'No description')}")
    
    # Test 6: Aggiorna pattern
    print("\n🔄 Test aggiornamento pattern:")
    success = manager.update_pattern(
        category='anonymization',
        name='test_custom_ip',
        description='Updated: Private IP addresses for internal networks'
    )
    print(f"   - Pattern aggiornato: {'✅' if success else '❌'}")
    
    # Test 7: Rimuovi pattern
    print("\n🗑️ Test rimozione pattern:")
    success = manager.remove_pattern('anonymization', 'test_custom_ip')
    print(f"   - Pattern rimosso: {'✅' if success else '❌'}")
    
    # Test 8: Statistiche finali
    print("\n📊 Statistiche finali:")
    stats = manager.get_statistics()
    print(f"   - Pattern totali: {stats['total_patterns']}")
    print(f"   - Categorie: {stats['categories']}")
    
    print("\n✅ Test RegexManager completato!")


if __name__ == "__main__":
    test_regex_manager() 