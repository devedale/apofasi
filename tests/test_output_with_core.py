"""
Test di Output Completo con Core Layer

Questo script testa l'intera pipeline di parsing utilizzando
il Core Layer appena implementato, inclusi logging, metriche,
cache e validazione.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.core import (
    # Core Layer
    LoggerService, MetricsService, CacheService, ValidatorService,
    LogFormat, ParserType, ProcessingStatus, ErrorSeverity,
    ValidationLevel, CacheStrategy
)

from src.infrastructure.parsers import (
    # Parser estratti
    get_available_parsers, create_specific_parser
)


def setup_core_services():
    """
    Configura i servizi core per il test.
    
    WHY: Setup centralizzato per garantire configurazione
    consistente di tutti i servizi core.
    
    Returns:
        Tuple con tutti i servizi configurati
    """
    print("🔧 Configurando servizi Core Layer...")
    
    # Logger Service
    logger = LoggerService(
        log_level="INFO",
        console_output=True,
        structured_logging=False
    )
    
    # Metrics Service
    metrics = MetricsService(
        auto_collect=True,
        update_interval=2.0
    )
    
    # Cache Service
    cache = CacheService(
        strategy=CacheStrategy.MEMORY,
        max_size=50 * 1024 * 1024,  # 50MB
        max_entries=1000,
        default_ttl=300  # 5 minuti
    )
    
    # Validator Service
    validator = ValidatorService(
        validation_level=ValidationLevel.BASIC,
        enable_logging=True,
        enable_metrics=True
    )
    
    logger.info("Servizi Core Layer configurati con successo")
    return logger, metrics, cache, validator


def test_parser_with_core_services(file_path: Path, parser_type: str, 
                                 logger: LoggerService, metrics: MetricsService,
                                 cache: CacheService, validator: ValidatorService):
    """
    Testa un parser specifico con i servizi core.
    
    WHY: Test integrato per verificare che i parser funzionino
    correttamente con logging, metriche, cache e validazione.
    
    Args:
        file_path: Percorso del file da parsare
        parser_type: Tipo di parser da utilizzare
        logger: Servizio di logging
        metrics: Servizio di metriche
        cache: Servizio di cache
        validator: Servizio di validazione
    """
    print(f"\n🧪 Testando parser {parser_type} su {file_path.name}")
    
    start_time = time.time()
    
    try:
        # Validazione file
        logger.info(f"Iniziando validazione file: {file_path}")
        file_validation = validator.validate_file(file_path)
        
        if not file_validation['valid']:
            logger.error(f"File non valido: {file_validation['errors']}")
            return False
        
        # Creazione parser
        logger.info(f"Creando parser {parser_type}")
        parser = create_specific_parser(parser_type)
        
        if not parser:
            logger.error(f"Parser {parser_type} non disponibile")
            return False
        
        # Parsing con cache
        cache_key = f"parsed_{file_path.name}_{parser_type}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.info("Risultato trovato in cache")
            parsed_records = cached_result
        else:
            logger.info("Parsing file...")
            
            # Leggi il file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parsed_records = list(parser.parse(content, str(file_path)))
            
            # Cache del risultato
            cache.set(cache_key, parsed_records, ttl=600)  # 10 minuti
        
        # Validazione risultati
        logger.info(f"Validando {len(parsed_records)} record")
        validation_result = validator.validate_data(parsed_records)
        
        # Metriche
        duration = time.time() - start_time
        metrics.record_operation(
            operation=f"parse_{parser_type}",
            duration=duration,
            success=True,
            files_processed=1,
            records_processed=len(parsed_records),
            warnings=len(validation_result.get('warnings', []))
        )
        
        # Logging risultati
        logger.info(f"Parsing completato: {len(parsed_records)} record in {duration:.3f}s")
        
        if validation_result['valid']:
            logger.info("Validazione record completata con successo")
        else:
            logger.warning(f"Validazione con warning: {validation_result['warnings']}")
        
        return True
        
    except Exception as e:
        duration = time.time() - start_time
        logger.log_exception(e, context={
            'file_path': str(file_path),
            'parser_type': parser_type,
            'duration': duration
        })
        
        metrics.record_operation(
            operation=f"parse_{parser_type}",
            duration=duration,
            success=False
        )
        
        return False


def test_all_parsers_with_core():
    """
    Testa tutti i parser disponibili con i servizi core.
    
    WHY: Test completo per verificare l'integrazione
    tra parser estratti e Core Layer.
    """
    print("🚀 Iniziando test completo con Core Layer...")
    print("=" * 60)
    
    # Setup servizi core
    logger, metrics, cache, validator = setup_core_services()
    
    # File di test
    test_files = {
        'examples/example_syslog.txt': 'syslog',
        'examples/FGT80FTK22013405.root.tlog.txt': 'fortinet'
    }
    
    results = {}
    total_start_time = time.time()
    
    # Test ogni parser
    for file_path_str, parser_type in test_files.items():
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            logger.warning(f"File non trovato: {file_path}")
            continue
        
        success = test_parser_with_core_services(
            file_path, parser_type, logger, metrics, cache, validator
        )
        
        results[file_path.name] = {
            'parser_type': parser_type,
            'success': success,
            'file_size': file_path.stat().st_size
        }
    
    # Statistiche finali
    total_duration = time.time() - total_start_time
    
    print("\n" + "=" * 60)
    print("📊 RISULTATI TEST COMPLETO")
    print("=" * 60)
    
    # Risultati parsing
    successful_tests = sum(1 for r in results.values() if r['success'])
    total_tests = len(results)
    
    print(f"✅ Test completati: {successful_tests}/{total_tests}")
    print(f"⏱️  Tempo totale: {total_duration:.3f}s")
    
    for file_name, result in results.items():
        status = "✅" if result['success'] else "❌"
        print(f"{status} {file_name} ({result['parser_type']}) - {result['file_size']} bytes")
    
    # Statistiche Core Layer
    print("\n📈 STATISTICHE CORE LAYER")
    print("-" * 30)
    
    # Logger stats
    logger_stats = logger.get_statistics()
    print(f"📝 Logger: {logger_stats['log_level']} level")
    
    # Metrics stats
    metrics_summary = metrics.get_performance_summary()
    print(f"📊 Metriche: {metrics_summary['total_operations']} operazioni")
    print(f"   ⏱️  Tempo medio: {metrics_summary['average_operation_time']:.3f}s")
    print(f"   ❌ Error rate: {metrics_summary['error_rate_percent']:.1f}%")
    print(f"   💾 CPU: {metrics_summary['current_cpu_percent']:.1f}%")
    print(f"   🧠 Memoria: {metrics_summary['current_memory_percent']:.1f}%")
    
    # Cache stats
    cache_stats = cache.get_stats()
    print(f"💾 Cache: {cache_stats['current_entries']} entries")
    print(f"   🎯 Hit rate: {cache_stats['hit_rate_percent']:.1f}%")
    print(f"   📦 Size: {cache_stats['current_size_bytes'] / 1024:.1f} KB")
    
    # Validator stats
    validator_stats = validator.get_stats()
    print(f"✅ Validazione: {validator_stats['total_validations']} validazioni")
    print(f"   🎯 Success rate: {validator_stats['success_rate_percent']:.1f}%")
    print(f"   ⚠️  Warning: {validator_stats['total_warnings']}")
    
    # Salva risultati
    output_file = Path("outputs/test_results_with_core.json")
    output_file.parent.mkdir(exist_ok=True)
    
    final_results = {
        'timestamp': datetime.now().isoformat(),
        'test_duration': total_duration,
        'successful_tests': successful_tests,
        'total_tests': total_tests,
        'success_rate': (successful_tests / total_tests) * 100 if total_tests > 0 else 0,
        'results': results,
        'core_layer_stats': {
            'logger': logger_stats,
            'metrics': metrics_summary,
            'cache': cache_stats,
            'validator': validator_stats
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"\n💾 Risultati salvati in: {output_file}")
    
    # Cleanup
    metrics.stop_collection()
    
    return successful_tests == total_tests


def main():
    """Esegue il test completo con Core Layer."""
    try:
        success = test_all_parsers_with_core()
        
        if success:
            print("\n🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
            print("✅ Core Layer e parser funzionano correttamente insieme")
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