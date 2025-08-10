"""
Analizzatore per statistiche specifiche dei parser.

Questo modulo fornisce analisi dettagliate sui performance
e problemi di ogni parser individuale, inclusi tassi di successo,
errori comuni e metriche di performance.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import statistics
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.core import LoggerService


@dataclass
class ParserStatistics:
    """Statistiche dettagliate per un singolo parser."""
    parser_name: str
    total_records: int
    successful_parses: int
    failed_parses: int
    success_rate: float
    avg_confidence: float
    avg_processing_time: float
    total_processing_time: float
    common_errors: List[str]
    error_frequency: Dict[str, int]
    warning_frequency: Dict[str, int]
    performance_metrics: Dict[str, float]


class ParserStatisticsAnalyzer:
    """
    Analizzatore per statistiche specifiche dei parser.
    
    WHY: Fornisce analisi dettagliate per ogni parser per
    identificare problemi specifici e ottimizzazioni.
    """
    
    def __init__(self, logger: Optional[LoggerService] = None):
        """
        Inizializza l'analizzatore di statistiche dei parser.
        
        Args:
            logger: Servizio di logging opzionale
        """
        self.logger = logger or LoggerService()
    
    def analyze(self, results: List[Dict[str, Any]]) -> List[ParserStatistics]:
        """
        Analizza i risultati e genera statistiche per ogni parser.
        
        WHY: Identifica problemi specifici di ogni parser per
        migliorare la qualità del parsing e le performance.
        
        Args:
            results: Lista dei risultati parsati
            
        Returns:
            Lista di statistiche per ogni parser
        """
        if not results:
            self.logger.warning("Nessun risultato da analizzare per statistiche parser")
            return []
        
        self.logger.info(f"Analizzando statistiche per {len(results)} record")
        
        # Raggruppa risultati per parser
        parser_groups = defaultdict(list)
        for result in results:
            parser_name = result.get('parser_type', 'unknown')
            parser_groups[parser_name].append(result)
        
        # Analizza ogni parser
        parser_statistics = []
        for parser_name, parser_results in parser_groups.items():
            stats = self._analyze_single_parser(parser_name, parser_results)
            parser_statistics.append(stats)
        
        # Ordina per success rate decrescente
        parser_statistics.sort(key=lambda x: x.success_rate, reverse=True)
        
        self.logger.info(f"Statistiche calcolate per {len(parser_statistics)} parser")
        
        return parser_statistics
    
    def _analyze_single_parser(self, parser_name: str, results: List[Dict[str, Any]]) -> ParserStatistics:
        """
        Analizza statistiche per un singolo parser.
        
        Args:
            parser_name: Nome del parser
            results: Risultati per questo parser
            
        Returns:
            Statistiche del parser
        """
        total_records = len(results)
        successful_parses = sum(1 for r in results if r.get('success', False))
        failed_parses = total_records - successful_parses
        success_rate = (successful_parses / total_records) * 100 if total_records > 0 else 0
        
        # Metriche di confidence
        confidence_values = [r.get('confidence', 0.0) for r in results if r.get('confidence') is not None]
        avg_confidence = statistics.mean(confidence_values) if confidence_values else 0.0
        
        # Metriche di tempo
        processing_times = [r.get('processing_time', 0.0) for r in results if r.get('processing_time') is not None]
        avg_processing_time = statistics.mean(processing_times) if processing_times else 0.0
        total_processing_time = sum(processing_times)
        
        # Errori comuni
        common_errors = self._analyze_common_errors(results)
        error_frequency = self._analyze_error_frequency(results)
        
        # Warning frequency
        warning_frequency = self._analyze_warning_frequency(results)
        
        # Performance metrics
        performance_metrics = self._calculate_performance_metrics(results)
        
        stats = ParserStatistics(
            parser_name=parser_name,
            total_records=total_records,
            successful_parses=successful_parses,
            failed_parses=failed_parses,
            success_rate=success_rate,
            avg_confidence=avg_confidence,
            avg_processing_time=avg_processing_time,
            total_processing_time=total_processing_time,
            common_errors=common_errors,
            error_frequency=error_frequency,
            warning_frequency=warning_frequency,
            performance_metrics=performance_metrics
        )
        
        self.logger.debug(f"Parser {parser_name}: {successful_parses}/{total_records} successi ({success_rate:.1f}%)")
        
        return stats
    
    def _analyze_common_errors(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Analizza gli errori più comuni per questo parser.
        
        Args:
            results: Risultati del parser
            
        Returns:
            Lista degli errori più comuni
        """
        error_counter = Counter()
        
        for result in results:
            if not result.get('success', False):
                error_message = result.get('error', 'Unknown error')
                # Estrai il tipo di errore dal messaggio
                error_type = self._extract_error_type(error_message)
                error_counter[error_type] += 1
        
        # Restituisci i top 5 errori
        return [error for error, count in error_counter.most_common(5)]
    
    def _extract_error_type(self, error_message: str) -> str:
        """
        Estrae il tipo di errore dal messaggio di errore.
        
        Args:
            error_message: Messaggio di errore completo
            
        Returns:
            Tipo di errore estratto
        """
        # Mappatura di errori comuni
        error_mappings = {
            'parsing': ['parse', 'parsing', 'format'],
            'validation': ['validate', 'validation', 'invalid'],
            'encoding': ['encoding', 'utf', 'ascii'],
            'timeout': ['timeout', 'time out'],
            'memory': ['memory', 'out of memory'],
            'permission': ['permission', 'access denied'],
            'not found': ['not found', 'file not found'],
            'unknown': ['unknown', 'unexpected']
        }
        
        error_message_lower = error_message.lower()
        
        for error_type, keywords in error_mappings.items():
            if any(keyword in error_message_lower for keyword in keywords):
                return error_type
        
        return 'other'
    
    def _analyze_error_frequency(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analizza la frequenza degli errori per tipo.
        
        Args:
            results: Risultati del parser
            
        Returns:
            Frequenza degli errori per tipo
        """
        error_counter = Counter()
        
        for result in results:
            if not result.get('success', False):
                error_message = result.get('error', 'Unknown error')
                error_type = self._extract_error_type(error_message)
                error_counter[error_type] += 1
        
        return dict(error_counter)
    
    def _analyze_warning_frequency(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analizza la frequenza dei warning per tipo.
        
        Args:
            results: Risultati del parser
            
        Returns:
            Frequenza dei warning per tipo
        """
        warning_counter = Counter()
        
        for result in results:
            warnings = result.get('warnings', [])
            for warning in warnings:
                if isinstance(warning, dict):
                    warning_type = warning.get('type', 'unknown')
                else:
                    warning_type = str(warning)
                warning_counter[warning_type] += 1
        
        return dict(warning_counter)
    
    def _calculate_performance_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calcola metriche di performance per il parser.
        
        Args:
            results: Risultati del parser
            
        Returns:
            Metriche di performance
        """
        processing_times = [r.get('processing_time', 0.0) for r in results if r.get('processing_time') is not None]
        
        if not processing_times:
            return {
                'min_time': 0.0,
                'max_time': 0.0,
                'median_time': 0.0,
                'std_dev_time': 0.0,
                'throughput': 0.0
            }
        
        metrics = {
            'min_time': min(processing_times),
            'max_time': max(processing_times),
            'median_time': statistics.median(processing_times),
            'std_dev_time': statistics.stdev(processing_times) if len(processing_times) > 1 else 0.0
        }
        
        # Calcola throughput (record per secondo)
        total_time = sum(processing_times)
        metrics['throughput'] = len(results) / total_time if total_time > 0 else 0.0
        
        return metrics 