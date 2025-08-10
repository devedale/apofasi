"""
Test Completo su Tutta la Cartella Examples

Questo script testa l'intera pipeline di parsing su tutti i file
nella cartella examples, tentando di identificare automaticamente
il formato corretto per ogni file.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

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
    """Configura i servizi core per il test."""
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
        max_size=100 * 1024 * 1024,  # 100MB
        max_entries=2000,
        default_ttl=600  # 10 minuti
    )
    
    # Validator Service
    validator = ValidatorService(
        validation_level=ValidationLevel.BASIC,
        enable_logging=True,
        enable_metrics=True
    )
    
    logger.info("Servizi Core Layer configurati con successo")
    return logger, metrics, cache, validator


def detect_file_format(file_path: Path, logger: LoggerService) -> Optional[str]:
    """
    Tenta di rilevare automaticamente il formato del file.
    
    WHY: Rilevamento automatico per processare file senza
    conoscere a priori il loro formato.
    
    Args:
        file_path: Percorso del file da analizzare
        logger: Servizio di logging
        
    Returns:
        Nome del parser da utilizzare o None se non rilevato
    """
    try:
        # Leggi le prime righe del file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample_lines = []
            for i, line in enumerate(f):
                if i >= 5:  # Leggi solo le prime 5 righe
                    break
                sample_lines.append(line.strip())
        
        if not sample_lines:
            return None
        
        sample_content = '\n'.join(sample_lines)
        
        # Testa ogni parser disponibile
        available_parsers = get_available_parsers()
        
        for parser_name in available_parsers:
            try:
                parser = create_specific_parser(parser_name)
                if parser and parser.can_parse(sample_content, str(file_path)):
                    logger.info(f"Formato rilevato per {file_path.name}: {parser_name}")
                    return parser_name
            except Exception as e:
                logger.debug(f"Parser {parser_name} fallito per {file_path.name}: {e}")
                continue
        
        # Fallback basato sull'estensione del file
        extension = file_path.suffix.lower()
        if extension == '.csv':
            logger.info(f"Fallback per {file_path.name}: formato CSV (non ancora implementato)")
            return None
        elif extension == '.json':
            logger.info(f"Fallback per {file_path.name}: formato JSON (non ancora implementato)")
            return None
        elif extension == '.txt':
            # Per file .txt, non fare fallback automatico
            logger.info(f"Fallback per {file_path.name}: formato non rilevato")
            return None
        
        logger.warning(f"Formato non rilevato per {file_path.name}")
        return None
        
    except Exception as e:
        logger.error(f"Errore rilevamento formato per {file_path.name}: {e}")
        return None


def test_file_with_core_services(file_path: Path, parser_type: str, 
                               logger: LoggerService, metrics: MetricsService,
                               cache: CacheService, validator: ValidatorService) -> Dict[str, Any]:
    """
    Testa un singolo file con i servizi core.
    
    Args:
        file_path: Percorso del file da parsare
        parser_type: Tipo di parser da utilizzare
        logger: Servizio di logging
        metrics: Servizio di metriche
        cache: Servizio di cache
        validator: Servizio di validazione
        
    Returns:
        Dizionario con risultati del test
    """
    start_time = time.time()
    
    try:
        # Validazione file
        logger.info(f"Validando file: {file_path}")
        file_validation = validator.validate_file(file_path)
        
        if not file_validation['valid']:
            logger.error(f"File non valido: {file_validation['errors']}")
            return {
                'success': False,
                'error': 'File validation failed',
                'file_size': file_path.stat().st_size,
                'duration': time.time() - start_time
            }
        
        # Creazione parser
        logger.info(f"Creando parser {parser_type}")
        parser = create_specific_parser(parser_type)
        
        if not parser:
            logger.error(f"Parser {parser_type} non disponibile")
            return {
                'success': False,
                'error': f'Parser {parser_type} not available',
                'file_size': file_path.stat().st_size,
                'duration': time.time() - start_time
            }
        
        # Parsing con cache
        cache_key = f"parsed_{file_path.name}_{parser_type}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.info("Risultato trovato in cache")
            parsed_records = cached_result
        else:
            logger.info("Parsing file...")
            
            # Leggi il file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
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
        
        return {
            'success': True,
            'parser_type': parser_type,
            'records_parsed': len(parsed_records),
            'file_size': file_path.stat().st_size,
            'duration': duration,
            'validation_warnings': len(validation_result.get('warnings', [])),
            'validation_errors': len(validation_result.get('errors', []))
        }
        
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
        
        return {
            'success': False,
            'error': str(e),
            'file_size': file_path.stat().st_size,
            'duration': duration
        }


def test_all_examples():
    """
    Testa tutti i file nella cartella examples.
    
    WHY: Test completo per verificare la capacità del sistema
    di processare diversi tipi di file automaticamente.
    """
    print("🚀 Iniziando test completo su tutta la cartella examples...")
    print("=" * 70)
    
    # Setup servizi core
    logger, metrics, cache, validator = setup_core_services()
    
    # Trova tutti i file da testare
    examples_dir = Path("examples")
    test_files = []
    
    # File nella root di examples
    for file_path in examples_dir.iterdir():
        if file_path.is_file() and file_path.suffix in ['.txt', '.csv', '.json', '.log']:
            test_files.append(file_path)
    
    # File nelle sottocartelle (escludendo .git)
    for subdir in examples_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.'):
            for file_path in subdir.rglob('*.log'):
                test_files.append(file_path)
            for file_path in subdir.rglob('*.txt'):
                test_files.append(file_path)
    
    logger.info(f"Trovati {len(test_files)} file da testare")
    
    results = {}
    total_start_time = time.time()
    
    # Test ogni file
    for i, file_path in enumerate(test_files, 1):
        print(f"\n[{i}/{len(test_files)}] 🧪 Testando {file_path}")
        
        # Rilevamento automatico formato
        detected_format = detect_file_format(file_path, logger)
        
        if detected_format:
            result = test_file_with_core_services(
                file_path, detected_format, logger, metrics, cache, validator
            )
            result['detected_format'] = detected_format
        else:
            result = {
                'success': False,
                'error': 'Format not detected',
                'file_size': file_path.stat().st_size,
                'duration': 0.0,
                'detected_format': None
            }
        
        results[str(file_path)] = result
    
    # Statistiche finali
    total_duration = time.time() - total_start_time
    
    print("\n" + "=" * 70)
    print("📊 RISULTATI TEST COMPLETO SU TUTTA LA CARTELLA EXAMPLES")
    print("=" * 70)
    
    # Risultati parsing
    successful_tests = sum(1 for r in results.values() if r['success'])
    total_tests = len(results)
    total_records = sum(r.get('records_parsed', 0) for r in results.values() if r['success'])
    
    print(f"✅ Test completati: {successful_tests}/{total_tests}")
    print(f"📄 Record parsati: {total_records}")
    print(f"⏱️  Tempo totale: {total_duration:.3f}s")
    
    # Dettaglio per file
    print(f"\n📋 DETTAGLIO PER FILE:")
    for file_path, result in results.items():
        status = "✅" if result['success'] else "❌"
        file_name = Path(file_path).name
        format_detected = result.get('detected_format', 'N/A')
        records = result.get('records_parsed', 0)
        duration = result.get('duration', 0)
        size = result.get('file_size', 0)
        
        print(f"{status} {file_name}")
        print(f"   📁 Formato: {format_detected}")
        print(f"   📊 Record: {records}")
        print(f"   ⏱️  Tempo: {duration:.3f}s")
        print(f"   📦 Size: {size} bytes")
        
        if not result['success'] and 'error' in result:
            print(f"   ❌ Errore: {result['error']}")
        print()
    
    # Statistiche Core Layer
    print("📈 STATISTICHE CORE LAYER")
    print("-" * 40)
    
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
    output_file = Path("outputs/test_all_examples_results.json")
    output_file.parent.mkdir(exist_ok=True)
    
    final_results = {
        'timestamp': datetime.now().isoformat(),
        'test_duration': total_duration,
        'successful_tests': successful_tests,
        'total_tests': total_tests,
        'total_records_parsed': total_records,
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
    """Esegue il test completo su tutti gli esempi."""
    try:
        success = test_all_examples()
        
        if success:
            print("\n🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
            print("✅ Sistema in grado di processare tutti i file examples")
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