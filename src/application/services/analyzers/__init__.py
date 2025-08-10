"""
Package per analizzatori di statistiche e reportistica.

Questo package contiene tutti gli analizzatori specializzati per
generare statistiche dettagliate sui risultati di parsing.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

from .general_statistics_analyzer import GeneralStatisticsAnalyzer, GeneralStatistics
from .parser_statistics_analyzer import ParserStatisticsAnalyzer, ParserStatistics
from .template_analyzer import TemplateAnalyzer, TemplateAnalysis
from .anonymization_analyzer import AnonymizationAnalyzer, AnonymizationStats
from .issues_analyzer import IssuesAnalyzer, IssueAnalysis

__all__ = [
    # Analizzatori
    'GeneralStatisticsAnalyzer',
    'ParserStatisticsAnalyzer', 
    'TemplateAnalyzer',
    'AnonymizationAnalyzer',
    'IssuesAnalyzer',
    
    # Data classes
    'GeneralStatistics',
    'ParserStatistics',
    'TemplateAnalysis', 
    'AnonymizationStats',
    'IssueAnalysis'
] 