"""
Analizzatore per problemi e warning nei risultati di parsing.

Questo modulo identifica e categorizza problemi, warning e
anomalie nei risultati di parsing per migliorare la qualità
e l'affidabilità del sistema.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.core import LoggerService


@dataclass
class IssueAnalysis:
    """Analisi di problemi e warning."""
    total_issues: int
    critical_issues: int
    warnings: int
    error_distribution: Dict[str, int]
    warning_distribution: Dict[str, int]
    parser_issues: Dict[str, List[str]]
    common_problems: List[str]
    recommendations: List[str]


class IssuesAnalyzer:
    """
    Analizzatore per problemi e warning nei risultati di parsing.
    
    WHY: Identifica sistematicamente problemi per migliorare
    la qualità del parsing e l'affidabilità del sistema.
    """
    
    def __init__(self, logger: Optional[LoggerService] = None):
        """
        Inizializza l'analizzatore di problemi.
        
        Args:
            logger: Servizio di logging opzionale
        """
        self.logger = logger or LoggerService()
    
    def analyze(self, results: List[Dict[str, Any]]) -> IssueAnalysis:
        """
        Analizza i risultati per identificare problemi e warning.
        
        WHY: Fornisce visibilità sui problemi per migliorare
        la qualità del parsing e prevenire errori futuri.
        
        Args:
            results: Lista dei risultati parsati
            
        Returns:
            Analisi dei problemi e warning
        """
        if not results:
            self.logger.warning("Nessun risultato da analizzare per problemi")
            return self._create_empty_analysis()
        
        self.logger.info(f"Analizzando problemi per {len(results)} record")
        
        # Contatori base
        total_issues = 0
        critical_issues = 0
        warnings = 0
        
        # Distribuzioni
        error_distribution = self._analyze_error_distribution(results)
        warning_distribution = self._analyze_warning_distribution(results)
        
        # Problemi per parser
        parser_issues = self._analyze_parser_issues(results)
        
        # Problemi comuni
        common_problems = self._identify_common_problems(results)
        
        # Raccomandazioni
        recommendations = self._generate_recommendations(results, error_distribution, warning_distribution)
        
        # Calcola totali
        total_issues = sum(error_distribution.values()) + sum(warning_distribution.values())
        critical_issues = sum(count for error, count in error_distribution.items() 
                           if self._is_critical_error(error))
        warnings = sum(warning_distribution.values())
        
        analysis = IssueAnalysis(
            total_issues=total_issues,
            critical_issues=critical_issues,
            warnings=warnings,
            error_distribution=error_distribution,
            warning_distribution=warning_distribution,
            parser_issues=parser_issues,
            common_problems=common_problems,
            recommendations=recommendations
        )
        
        self.logger.info(f"Problemi identificati: {total_issues} totali, {critical_issues} critici, {warnings} warning")
        
        return analysis
    
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
                error_message = result.get('error', 'Unknown error')
                error_type = self._categorize_error(error_message)
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
                    warning_message = warning.get('message', '')
                else:
                    warning_type = 'general'
                    warning_message = str(warning)
                
                # Categorizza il warning
                categorized_type = self._categorize_warning(warning_message)
                warning_counter[categorized_type] += 1
        
        return dict(warning_counter)
    
    def _analyze_parser_issues(self, results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Analizza i problemi specifici per ogni parser.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Problemi per parser
        """
        parser_issues = defaultdict(list)
        
        for result in results:
            parser_name = result.get('parser_type', 'unknown')
            
            if not result.get('success', False):
                error_message = result.get('error', 'Unknown error')
                parser_issues[parser_name].append(error_message)
            else:
                warnings = result.get('warnings', [])
                for warning in warnings:
                    if isinstance(warning, dict):
                        warning_message = warning.get('message', '')
                    else:
                        warning_message = str(warning)
                    parser_issues[parser_name].append(warning_message)
        
        return dict(parser_issues)
    
    def _identify_common_problems(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Identifica problemi comuni nei risultati.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Lista di problemi comuni
        """
        problem_patterns = {
            'parsing_failure': ['parse', 'parsing', 'format'],
            'validation_error': ['validate', 'validation', 'invalid'],
            'encoding_issue': ['encoding', 'utf', 'ascii'],
            'timeout_error': ['timeout', 'time out'],
            'memory_error': ['memory', 'out of memory'],
            'permission_error': ['permission', 'access denied'],
            'file_not_found': ['not found', 'file not found'],
            'data_quality': ['quality', 'incomplete', 'missing'],
            'performance': ['slow', 'performance', 'timeout']
        }
        
        problem_counter = Counter()
        
        for result in results:
            if not result.get('success', False):
                error_message = result.get('error', '').lower()
                
                for problem_type, keywords in problem_patterns.items():
                    if any(keyword in error_message for keyword in keywords):
                        problem_counter[problem_type] += 1
        
        # Restituisci i problemi più comuni
        return [problem for problem, count in problem_counter.most_common(5)]
    
    def _generate_recommendations(self, results: List[Dict[str, Any]], 
                                error_distribution: Dict[str, int],
                                warning_distribution: Dict[str, int]) -> List[str]:
        """
        Genera raccomandazioni basate sui problemi identificati.
        
        Args:
            results: Lista dei risultati
            error_distribution: Distribuzione degli errori
            warning_distribution: Distribuzione dei warning
            
        Returns:
            Lista di raccomandazioni
        """
        recommendations = []
        
        # Analizza errori di parsing
        parsing_errors = error_distribution.get('parsing', 0)
        if parsing_errors > 0:
            recommendations.append(f"Considerare miglioramenti ai parser per ridurre {parsing_errors} errori di parsing")
        
        # Analizza errori di validazione
        validation_errors = error_distribution.get('validation', 0)
        if validation_errors > 0:
            recommendations.append(f"Rivedere le regole di validazione per risolvere {validation_errors} errori di validazione")
        
        # Analizza problemi di encoding
        encoding_errors = error_distribution.get('encoding', 0)
        if encoding_errors > 0:
            recommendations.append(f"Implementare gestione encoding più robusta per {encoding_errors} errori di encoding")
        
        # Analizza warning di qualità dati
        quality_warnings = warning_distribution.get('data_quality', 0)
        if quality_warnings > 0:
            recommendations.append(f"Migliorare la qualità dei dati per ridurre {quality_warnings} warning di qualità")
        
        # Analizza problemi di performance
        performance_issues = error_distribution.get('performance', 0)
        if performance_issues > 0:
            recommendations.append("Ottimizzare le performance del parsing per ridurre timeout")
        
        # Raccomandazioni generali
        total_errors = sum(error_distribution.values())
        total_warnings = sum(warning_distribution.values())
        
        if total_errors > len(results) * 0.1:  # Più del 10% di errori
            recommendations.append("Considerare una revisione completa dei parser")
        
        if total_warnings > len(results) * 0.2:  # Più del 20% di warning
            recommendations.append("Migliorare la qualità dei dati di input")
        
        return recommendations
    
    def _categorize_error(self, error_message: str) -> str:
        """
        Categorizza un errore basato sul messaggio.
        
        Args:
            error_message: Messaggio di errore
            
        Returns:
            Categoria dell'errore
        """
        error_message_lower = error_message.lower()
        
        # Mappatura errori
        error_categories = {
            'parsing': ['parse', 'parsing', 'format', 'syntax'],
            'validation': ['validate', 'validation', 'invalid', 'required'],
            'encoding': ['encoding', 'utf', 'ascii', 'unicode'],
            'timeout': ['timeout', 'time out', 'timed out'],
            'memory': ['memory', 'out of memory', 'insufficient'],
            'permission': ['permission', 'access denied', 'forbidden'],
            'not_found': ['not found', 'file not found', 'missing'],
            'network': ['network', 'connection', 'timeout'],
            'performance': ['slow', 'performance', 'timeout'],
            'data_quality': ['quality', 'incomplete', 'missing', 'corrupt']
        }
        
        for category, keywords in error_categories.items():
            if any(keyword in error_message_lower for keyword in keywords):
                return category
        
        return 'unknown'
    
    def _categorize_warning(self, warning_message: str) -> str:
        """
        Categorizza un warning basato sul messaggio.
        
        Args:
            warning_message: Messaggio di warning
            
        Returns:
            Categoria del warning
        """
        warning_message_lower = warning_message.lower()
        
        # Mappatura warning
        warning_categories = {
            'data_quality': ['quality', 'incomplete', 'missing', 'corrupt'],
            'performance': ['slow', 'performance', 'timeout'],
            'validation': ['validate', 'validation', 'warning'],
            'encoding': ['encoding', 'utf', 'ascii'],
            'format': ['format', 'structure', 'pattern'],
            'security': ['security', 'sensitive', 'privacy']
        }
        
        for category, keywords in warning_categories.items():
            if any(keyword in warning_message_lower for keyword in keywords):
                return category
        
        return 'general'
    
    def _is_critical_error(self, error_type: str) -> bool:
        """
        Determina se un errore è critico.
        
        Args:
            error_type: Tipo di errore
            
        Returns:
            True se l'errore è critico
        """
        critical_errors = ['memory', 'permission', 'not_found', 'network']
        return error_type in critical_errors
    
    def _create_empty_analysis(self) -> IssueAnalysis:
        """
        Crea analisi vuota quando non ci sono risultati.
        
        Returns:
            Analisi vuota
        """
        return IssueAnalysis(
            total_issues=0,
            critical_issues=0,
            warnings=0,
            error_distribution={},
            warning_distribution={},
            parser_issues={},
            common_problems=[],
            recommendations=[]
        ) 