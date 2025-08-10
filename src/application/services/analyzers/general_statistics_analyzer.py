"""
Analizzatore per statistiche generali dei risultati di parsing.

Questo modulo fornisce analisi statistiche generali sui risultati
di parsing, inclusi conteggi, medie, distribuzioni e metriche
di performance.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import statistics
from collections import Counter
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.core import LoggerService


@dataclass
class GeneralStatistics:
    """Statistiche generali sui risultati di parsing."""
    total_records: int
    successful_parses: int
    failed_parses: int
    success_rate: float
    avg_confidence: float
    avg_processing_time: float
    total_processing_time: float
    unique_parsers: int
    parser_distribution: Dict[str, int]
    error_distribution: Dict[str, int]
    warning_distribution: Dict[str, int]


class GeneralStatisticsAnalyzer:
    """
    Analizzatore per statistiche generali dei risultati di parsing.
    
    WHY: Separazione delle responsabilità per mantenere il codice
    modulare e testabile. Ogni analizzatore ha una responsabilità
    specifica e ben definita.
    """
    
    def __init__(self, logger: Optional[LoggerService] = None):
        """
        Inizializza l'analizzatore di statistiche generali.
        
        Args:
            logger: Servizio di logging opzionale
        """
        self.logger = logger or LoggerService()
    
    def analyze(self, results: List[Dict[str, Any]]) -> GeneralStatistics:
        """
        Analizza i risultati e genera statistiche generali.
        
        WHY: Fornisce una visione d'insieme dei risultati di parsing
        per identificare pattern, problemi e performance.
        
        Args:
            results: Lista dei risultati parsati
            
        Returns:
            Statistiche generali calcolate
        """
        if not results:
            self.logger.warning("Nessun risultato da analizzare")
            return self._create_empty_statistics()
        
        self.logger.info(f"Analizzando {len(results)} record per statistiche generali")
        
        # Contatori base
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
        
        # Distribuzione parser
        parser_distribution = Counter(r.get('parser_type', 'unknown') for r in results)
        
        # Distribuzione errori
        error_distribution = self._analyze_error_distribution(results)
        
        # Distribuzione warning
        warning_distribution = self._analyze_warning_distribution(results)
        
        # Numero parser unici
        unique_parsers = len(set(r.get('parser_type', 'unknown') for r in results))
        
        statistics_data = GeneralStatistics(
            total_records=total_records,
            successful_parses=successful_parses,
            failed_parses=failed_parses,
            success_rate=success_rate,
            avg_confidence=avg_confidence,
            avg_processing_time=avg_processing_time,
            total_processing_time=total_processing_time,
            unique_parsers=unique_parsers,
            parser_distribution=dict(parser_distribution),
            error_distribution=error_distribution,
            warning_distribution=warning_distribution
        )
        
        self.logger.info(f"Statistiche generali calcolate: {successful_parses}/{total_records} successi ({success_rate:.1f}%)")
        
        return statistics_data
    
    def _analyze_error_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analizza la distribuzione degli errori.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Distribuzione degli errori per tipo
        """
        error_counter = Counter()
        
        for result in results:
            if not result.get('success', False):
                error_type = result.get('error_type', 'unknown')
                error_counter[error_type] += 1
        
        return dict(error_counter)
    
    def _analyze_warning_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analizza la distribuzione dei warning.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Distribuzione dei warning per tipo
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
    
    def _create_empty_statistics(self) -> GeneralStatistics:
        """
        Crea statistiche vuote quando non ci sono risultati.
        
        Returns:
            Statistiche vuote
        """
        return GeneralStatistics(
            total_records=0,
            successful_parses=0,
            failed_parses=0,
            success_rate=0.0,
            avg_confidence=0.0,
            avg_processing_time=0.0,
            total_processing_time=0.0,
            unique_parsers=0,
            parser_distribution={},
            error_distribution={},
            warning_distribution={}
        ) 