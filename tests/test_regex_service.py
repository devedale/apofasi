#!/usr/bin/env python3
"""
Test del servizio regex centralizzato.

WHY: Verifica che tutti i pattern regex siano caricati correttamente
e che il servizio funzioni come previsto.
"""

import sys
import logging
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from src.core.services.regex_service import RegexService


def test_regex_service():
    """Test del servizio regex centralizzato."""
    print("🧪 Testando RegexService...")
    
    # Inizializza il servizio
    regex_service = RegexService()
    # Abilita debug
    regex_service.logger.setLevel(logging.DEBUG)
    
    # Test 1: Verifica caricamento pattern
    print("\n📊 Statistiche pattern:")
    stats = regex_service.get_statistics()
    print(f"   - Pattern totali: {stats['total_patterns']}")
    print(f"   - Pattern compilati: {stats['compiled_patterns']}")
    print(f"   - Categorie: {stats['categories']}")
    
    # Test 2: Lista pattern per categoria
    print("\n📋 Pattern per categoria:")
    for category in ['anonymization', 'parsing', 'security', 'cleaning']:
        patterns = regex_service.list_patterns(category)
        print(f"   - {category}: {len(patterns)} pattern")
        for pattern in patterns[:3]:  # Mostra solo i primi 3
            print(f"     * {pattern}")
        if len(patterns) > 3:
            print(f"     * ... e altri {len(patterns) - 3}")
    
    # Test 3: Test pattern specifici
    print("\n🔍 Test pattern specifici:")
    
    # Test pattern CEF
    test_cef = "CEF:0|Fortinet|FortiGate|v6.0.0|0000000013|virus detected|1|src=192.168.1.100 dst=10.0.0.1"
    result = regex_service.test_pattern('parsing_cef', test_cef)
    print(f"   - CEF pattern: {'✅' if result['success'] else '❌'}")
    if result['success']:
        print(f"     Match count: {result['match_count']}")
        if result['matches']:
            print(f"     Matches: {result['matches']}")
    
    # Test pattern IP
    test_ip = "192.168.1.100"
    result = regex_service.test_pattern('anonymization_ip_address', test_ip)
    print(f"   - IP pattern: {'✅' if result['success'] else '❌'}")
    if result['success']:
        print(f"     Match count: {result['match_count']}")
        if result['matches']:
            print(f"     Matches: {result['matches']}")
    
    # Test pattern Apache CLF
    test_apache = '192.168.1.100 - - [25/Dec/2023:10:30:45 +0000] "GET /index.html HTTP/1.1" 200 2326'
    result = regex_service.test_pattern('parsing_apache_clf', test_apache)
    print(f"   - Apache CLF pattern: {'✅' if result['success'] else '❌'}")
    if result['success']:
        print(f"     Match count: {result['match_count']}")
        if result['matches']:
            print(f"     Matches: {result['matches']}")
    
    # Debug: mostra pattern compilati
    print("\n🔧 Debug pattern compilati:")
    cef_pattern = regex_service.get_compiled_pattern('parsing_cef')
    ip_pattern = regex_service.get_compiled_pattern('anonymization_ip_address')
    apache_pattern = regex_service.get_compiled_pattern('parsing_apache_clf')
    
    print(f"   - CEF pattern compilato: {'✅' if cef_pattern else '❌'}")
    print(f"   - IP pattern compilato: {'✅' if ip_pattern else '❌'}")
    print(f"   - Apache pattern compilato: {'✅' if apache_pattern else '❌'}")
    
    if cef_pattern:
        print(f"   - CEF pattern string: {cef_pattern.pattern}")
        print(f"   - CEF pattern starts with ^: {cef_pattern.pattern.startswith('^')}")
        # Debug: mostra la stringa originale dal dizionario
        cef_config = regex_service._patterns.get('parsing_cef', {})
        print(f"   - CEF original pattern: {cef_config.get('pattern', 'N/A')}")
        print(f"   - CEF original starts with ^: {cef_config.get('pattern', '').startswith('^')}")
        # Debug: testa la pulizia del pattern
        clean_pattern = cef_config.get('pattern', '')
        if clean_pattern.startswith("r'") and clean_pattern.endswith("'"):
            clean_pattern = clean_pattern[2:-1]
        print(f"   - CEF clean pattern: {clean_pattern}")
        print(f"   - CEF clean starts with ^: {clean_pattern.startswith('^')}")
    if ip_pattern:
        print(f"   - IP pattern string: {ip_pattern.pattern}")
        print(f"   - IP pattern starts with ^: {ip_pattern.pattern.startswith('^')}")
        ip_config = regex_service._patterns.get('anonymization_ip_address', {})
        print(f"   - IP original pattern: {ip_config.get('pattern', 'N/A')}")
        print(f"   - IP original starts with ^: {ip_config.get('pattern', '').startswith('^')}")
        clean_pattern = ip_config.get('pattern', '')
        if clean_pattern.startswith("r'") and clean_pattern.endswith("'"):
            clean_pattern = clean_pattern[2:-1]
        print(f"   - IP clean pattern: {clean_pattern}")
        print(f"   - IP clean starts with ^: {clean_pattern.startswith('^')}")
    if apache_pattern:
        print(f"   - Apache pattern string: {apache_pattern.pattern}")
        print(f"   - Apache pattern starts with ^: {apache_pattern.pattern.startswith('^')}")
        apache_config = regex_service._patterns.get('parsing_apache_clf', {})
        print(f"   - Apache original pattern: {apache_config.get('pattern', 'N/A')}")
        print(f"   - Apache original starts with ^: {apache_config.get('pattern', '').startswith('^')}")
        clean_pattern = apache_config.get('pattern', '')
        if clean_pattern.startswith("r'") and clean_pattern.endswith("'"):
            clean_pattern = clean_pattern[2:-1]
        print(f"   - Apache clean pattern: {clean_pattern}")
        print(f"   - Apache clean starts with ^: {clean_pattern.startswith('^')}")
    
    # Test 4: Test applicazione pattern
    print("\n🔄 Test applicazione pattern:")
    
    # Test anonimizzazione
    test_text = "IP: 192.168.1.100, MAC: 00:11:22:33:44:55, Email: test@example.com"
    anonymized = regex_service.apply_patterns_by_category(test_text, 'anonymization')
    print(f"   - Testo originale: {test_text}")
    print(f"   - Testo anonimizzato: {anonymized}")
    
    # Test 5: Test pattern mancanti
    print("\n⚠️ Test pattern mancanti:")
    missing_pattern = regex_service.get_compiled_pattern('pattern_inesistente')
    print(f"   - Pattern inesistente: {'❌' if missing_pattern is None else '✅'}")
    
    print("\n✅ Test RegexService completato!")


if __name__ == "__main__":
    test_regex_service() 