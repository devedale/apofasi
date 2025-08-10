"""
Test per il ReportingService Refactorizzato

Questo script testa il nuovo ReportingService che utilizza
analizzatori specializzati per generare report dettagliati.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.core import LoggerService
from src.application.services.reporting_service_refactored import ReportingService


def create_test_data():
    """
    Crea dati di test per il ReportingService.
    
    Returns:
        Lista di risultati di parsing simulati
    """
    return [
        # Record di successo - Syslog
        {
            'success': True,
            'parser_type': 'syslog',
            'message': '2025-08-06 19:30:00 server sshd[1234]: Accepted password for user admin',
            'parsed_data': {
                'timestamp': '2025-08-06 19:30:00',
                'host': 'server',
                'process': 'sshd',
                'pid': 1234,
                'message': 'Accepted password for user admin'
            },
            'confidence': 0.95,
            'processing_time': 0.001,
            'anonymized': False,
            'warnings': []
        },
        {
            'success': True,
            'parser_type': 'syslog',
            'message': '2025-08-06 19:31:00 server sshd[1235]: Failed password for user admin',
            'parsed_data': {
                'timestamp': '2025-08-06 19:31:00',
                'host': 'server',
                'process': 'sshd',
                'pid': 1235,
                'message': 'Failed password for user admin'
            },
            'confidence': 0.92,
            'processing_time': 0.002,
            'anonymized': True,
            'anonymized_fields': ['user'],
            'anonymization_info': {
                'methods': ['hash'],
                'field_methods': {'user': 'hash'}
            },
            'warnings': []
        },
        # Record di successo - Fortinet
        {
            'success': True,
            'parser_type': 'fortinet',
            'message': 'logver=0702111740 type=traffic srcip=192.168.1.100 dstip=10.0.0.1 action=accept',
            'parsed_data': {
                'logver': '0702111740',
                'type': 'traffic',
                'srcip': '192.168.1.100',
                'dstip': '10.0.0.1',
                'action': 'accept'
            },
            'confidence': 0.88,
            'processing_time': 0.003,
            'anonymized': True,
            'anonymized_fields': ['srcip', 'dstip'],
            'anonymization_info': {
                'methods': ['masking'],
                'field_methods': {'srcip': 'masking', 'dstip': 'masking'}
            },
            'warnings': []
        },
        # Record di fallimento
        {
            'success': False,
            'parser_type': 'syslog',
            'message': 'Invalid log format',
            'error': 'Parsing error: Invalid format',
            'error_type': 'parsing',
            'processing_time': 0.001,
            'anonymized': False,
            'warnings': []
        },
        {
            'success': False,
            'parser_type': 'fortinet',
            'message': 'Invalid fortinet log',
            'error': 'Validation error: Missing required fields',
            'error_type': 'validation',
            'processing_time': 0.002,
            'anonymized': False,
            'warnings': []
        },
        # Record con warning
        {
            'success': True,
            'parser_type': 'syslog',
            'message': '2025-08-06 19:32:00 server unknown[1236]: Unknown process message',
            'parsed_data': {
                'timestamp': '2025-08-06 19:32:00',
                'host': 'server',
                'process': 'unknown',
                'pid': 1236,
                'message': 'Unknown process message'
            },
            'confidence': 0.75,
            'processing_time': 0.005,
            'anonymized': False,
            'warnings': [
                {'type': 'data_quality', 'message': 'Unknown process type'},
                {'type': 'performance', 'message': 'Slow parsing detected'}
            ]
        }
    ]


def test_refactored_reporting_service():
    """
    Testa il ReportingService refactorizzato.
    """
    print("🧪 Testando ReportingService Refactorizzato...")
    print("=" * 60)
    
    # Setup
    output_dir = Path("outputs/test_refactored_reporting")
    logger = LoggerService(log_level="INFO", console_output=True)
    
    # Crea dati di test
    test_data = create_test_data()
    print(f"📊 Dati di test creati: {len(test_data)} record")
    
    # Inizializza ReportingService
    reporting_service = ReportingService(output_dir, logger)
    
    # Test 1: Generazione report completo
    print("\n🔍 Test 1: Generazione report completo")
    comprehensive_report = reporting_service.generate_comprehensive_report(test_data)
    
    # Verifica struttura del report
    required_keys = [
        'report_generated_at',
        'total_records_processed',
        'general_statistics',
        'parser_statistics',
        'template_analysis',
        'anonymization_statistics',
        'issues_analysis',
        'recommendations'
    ]
    
    for key in required_keys:
        if key in comprehensive_report:
            print(f"✅ {key}: Presente")
        else:
            print(f"❌ {key}: Mancante")
    
    # Test 2: Generazione file di dati puri
    print("\n📊 Test 2: Generazione file di dati puri")
    reporting_service.generate_pure_data_files(test_data)
    
    # Verifica file generati
    expected_files = [
        'comprehensive_report.json',
        'parsed_data.json',
        'parsed_data.csv',
        'statistics_summary.json'
    ]
    
    for filename in expected_files:
        file_path = output_dir / filename
        if file_path.exists():
            print(f"✅ {filename}: Generato")
        else:
            print(f"❌ {filename}: Mancante")
    
    # Test 3: Verifica contenuto report
    print("\n📋 Test 3: Verifica contenuto report")
    
    # Statistiche generali
    general_stats = comprehensive_report['general_statistics']
    print(f"📄 Record totali: {general_stats['total_records']}")
    print(f"✅ Successi: {general_stats['successful_parses']}")
    print(f"❌ Fallimenti: {general_stats['failed_parses']}")
    print(f"📈 Success Rate: {general_stats['success_rate']:.1f}%")
    
    # Statistiche parser
    parser_stats = comprehensive_report['parser_statistics']
    print(f"🔧 Parser analizzati: {len(parser_stats)}")
    for stat in parser_stats:
        print(f"   - {stat['parser_name']}: {stat['success_rate']:.1f}% success rate")
    
    # Analisi template
    template_analysis = comprehensive_report['template_analysis']
    print(f"📋 Template identificati: {len(template_analysis)}")
    
    # Statistiche anonimizzazione
    anonymization_stats = comprehensive_report['anonymization_statistics']
    print(f"🔒 Record anonimizzati: {anonymization_stats['total_anonymized']}")
    print(f"📊 Tasso anonimizzazione: {anonymization_stats['anonymization_rate']:.1f}%")
    
    # Analisi problemi
    issues_analysis = comprehensive_report['issues_analysis']
    print(f"⚠️  Problemi totali: {issues_analysis['total_issues']}")
    print(f"🚨 Problemi critici: {issues_analysis['critical_issues']}")
    print(f"⚠️  Warning: {issues_analysis['warnings']}")
    
    # Raccomandazioni
    recommendations = comprehensive_report['recommendations']
    print(f"💡 Raccomandazioni generate: {len(recommendations)}")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    print("\n" + "=" * 60)
    print("✅ TEST REPORTING SERVICE REFACTORIZZATO COMPLETATO")
    print("=" * 60)
    
    return True


def main():
    """Esegue il test del ReportingService refactorizzato."""
    try:
        success = test_refactored_reporting_service()
        
        if success:
            print("\n🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
            print("✅ ReportingService refactorizzato funziona correttamente")
        else:
            print("\n⚠️  ALCUNI TEST FALLITI")
            print("❌ Controllare i log per dettagli")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main()) 