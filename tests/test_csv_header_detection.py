#!/usr/bin/env python3
"""
Test per il rilevamento degli header CSV.

Questo script testa il rilevamento intelligente degli header CSV
per verificare che non vengano più generati campi field_0, field_1, etc.
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.parsers.csv_header_detection import CSVHeaderDetector
from src.infrastructure.parsers.adaptive_parser import AdaptiveParser


def test_csv_header_detection():
    """Test del rilevamento degli header CSV."""
    print("🧪 Testando rilevamento header CSV...")
    
    # Inizializza il rilevatore
    detector = CSVHeaderDetector()
    
    # Test case con dati di cybersecurity
    test_cases = [
        {
            "name": "Cybersecurity Intrusion Data",
            "lines": [
                "session_id,network_packet_size,protocol_type,login_attempts,session_duration,encryption_used,ip_reputation_score,failed_logins,browser_type,unusual_time_access,attack_detected",
                "SID_00001,599,TCP,4,492.9832634426563,DES,0.606818080396889,1,Edge,0,1",
                "SID_00002,472,TCP,3,1557.9964611204384,DES,0.30156896759608937,0,Firefox,0,0"
            ],
            "expected_headers": [
                "session_id", "network_packet_size", "protocol_type", "login_attempts",
                "session_duration", "encryption_used", "ip_reputation_score", "failed_logins",
                "browser_type", "unusual_time_access", "attack_detected"
            ],
            "description": "Dataset di cybersecurity con header significativi"
        },
        {
            "name": "Log Data with Timestamp",
            "lines": [
                "timestamp,source_ip,destination_ip,protocol,port,action,status",
                "2024-01-15T10:30:45Z,192.168.1.100,192.168.1.200,TCP,80,ALLOW,200",
                "2024-01-15T10:31:00Z,192.168.1.101,192.168.1.201,UDP,53,DENY,403"
            ],
            "expected_headers": [
                "timestamp", "source_ip", "destination_ip", "protocol", "port", "action", "status"
            ],
            "description": "Log con timestamp e IP"
        },
        {
            "name": "Simple Data",
            "lines": [
                "id,name,value",
                "1,test1,100",
                "2,test2,200"
            ],
            "expected_headers": ["id", "name", "value"],
            "description": "Dati semplici con header base"
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}/{total_tests}: {test_case['description']}")
        
        # Rileva header
        header_info = detector.detect_headers(test_case["lines"])
        
        if header_info:
            print(f"  ✅ Header rilevati: {len(header_info.headers)} campi")
            print(f"  📊 Confidence: {header_info.confidence:.2f}")
            print(f"  🔍 Delimiter: '{header_info.delimiter}'")
            print(f"  📋 Header: {header_info.headers}")
            
            # Verifica che gli header corrispondano a quelli attesi
            if header_info.confidence > 0.5:
                print(f"  ✅ Confidence sufficiente")
                passed_tests += 1
            else:
                print(f"  ❌ Confidence troppo bassa: {header_info.confidence:.2f}")
        else:
            print(f"  ❌ Nessun header rilevato")
    
    print(f"\n📊 Risultati: {passed_tests}/{total_tests} test passati")
    return passed_tests == total_tests


def test_adaptive_parser_with_csv():
    """Test del parser adattivo con dati CSV."""
    print("\n🧪 Testando parser adattivo con CSV...")
    
    # Inizializza il parser adattivo
    parser = AdaptiveParser()
    
    # Test case
    csv_content = """session_id,network_packet_size,protocol_type,login_attempts,session_duration,encryption_used,ip_reputation_score,failed_logins,browser_type,unusual_time_access,attack_detected
SID_00001,599,TCP,4,492.9832634426563,DES,0.606818080396889,1,Edge,0,1
SID_00002,472,TCP,3,1557.9964611204384,DES,0.30156896759608937,0,Firefox,0,0"""
    
    # Parsa il contenuto
    records = list(parser.parse(csv_content, "cybersecurity_data.csv"))
    
    print(f"📝 Record parsati: {len(records)}")
    
    if records:
        # Verifica il primo record
        first_record = records[0]
        print(f"  📊 Parser type: {first_record.get('parser_type', 'unknown')}")
        print(f"  📈 Structure confidence: {first_record.get('structure_confidence', 0.0):.2f}")
        
        # Verifica che non ci siano campi field_0, field_1, etc.
        field_fields = [k for k in first_record.keys() if k.startswith('field_')]
        if field_fields:
            print(f"  ❌ Campi generici trovati: {field_fields}")
            return False
        else:
            print(f"  ✅ Nessun campo generico trovato")
            
            # Verifica che ci siano i campi corretti
            expected_fields = [
                'session_id', 'network_packet_size', 'protocol_type', 'login_attempts',
                'session_duration', 'encryption_used', 'ip_reputation_score', 'failed_logins',
                'browser_type', 'unusual_time_access', 'attack_detected'
            ]
            
            found_fields = [k for k in first_record.keys() if k in expected_fields]
            print(f"  📋 Campi trovati: {found_fields}")
            
            if len(found_fields) >= len(expected_fields) * 0.8:  # 80% dei campi
                print(f"  ✅ Campi corretti rilevati")
                return True
            else:
                print(f"  ❌ Campi mancanti")
                return False
    else:
        print(f"  ❌ Nessun record parsato")
        return False


def test_header_cleaning():
    """Test della pulizia dei nomi degli header."""
    print("\n🧪 Testando pulizia nomi header...")
    
    detector = CSVHeaderDetector()
    
    # Test cases per pulizia header
    test_cases = [
        {
            "input": ["Session ID", "Network Packet Size", "Protocol Type"],
            "expected": ["Session_ID", "Network_Packet_Size", "Protocol_Type"]
        },
        {
            "input": ["source_ip", "destination_ip", "user_id"],
            "expected": ["source_ip", "destination_ip", "user_id"]
        },
        {
            "input": ["IP Address", "User ID", "Session ID"],
            "expected": ["IP_Address", "User_ID", "Session_ID"]
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}/{total_tests}")
        
        cleaned_headers = detector.clean_header_names(test_case["input"])
        print(f"  📥 Input: {test_case['input']}")
        print(f"  📤 Output: {cleaned_headers}")
        
        # Verifica che i nomi siano puliti
        if all(' ' not in header for header in cleaned_headers):
            print(f"  ✅ Nomi puliti correttamente")
            passed_tests += 1
        else:
            print(f"  ❌ Nomi non puliti correttamente")
    
    print(f"\n📊 Risultati: {passed_tests}/{total_tests} test passati")
    return passed_tests == total_tests


def main():
    """Esegue tutti i test."""
    print("🚀 Test rilevamento header CSV")
    print("=" * 50)
    
    # Esegui i test
    test1_passed = test_csv_header_detection()
    test2_passed = test_adaptive_parser_with_csv()
    test3_passed = test_header_cleaning()
    
    # Risultati finali
    print("\n" + "="*50)
    print("📊 RISULTATI FINALI")
    print("="*50)
    
    tests = [
        ("Rilevamento header CSV", test1_passed),
        ("Parser adattivo con CSV", test2_passed),
        ("Pulizia nomi header", test3_passed)
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
        print("✅ Il problema dei campi field_0, field_1, etc. è RISOLTO!")
        return True
    else:
        print("⚠️  Alcuni test sono falliti!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 