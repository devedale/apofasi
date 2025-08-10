"""
Parsers Module - Modulo per tutti i parser del sistema

Questo modulo fornisce accesso a tutti i parser disponibili nel sistema,
inclusi i parser specifici per diversi formati di log e il parser universale
che gestisce automaticamente la selezione del parser appropriato.

DESIGN:
- Factory pattern per la creazione di parser
- Supporto per parser specifici e universale
- Configurazione centralizzata dei parser
- Import automatico di tutte le classi parser

Author: Edoardo D'Alesio
Version: 1.0.0
"""

from typing import Dict, List, Any, Optional
from ...domain.interfaces.log_parser import LogParser

# Import dei parser specifici estratti
from .base_parser import BaseParser, ParseError
from .cef_parser import CEFParser
from .multi_strategy_parser import MultiStrategyParser
from .adaptive_parser import AdaptiveParser
from .xml_log_parser import XMLLogParser
from .csv_parser import CSVParser
from .office_parser import OfficeParser
from .binary_parser import BinaryParser
from .smart_excel_parser import SmartExcelParser

# Rimosso ParserOrchestrator - ora usiamo solo MultiStrategyParser


def create_parsers(config: Dict[str, Any], regex_service: Optional["RegexService"] = None) -> List[LogParser]:
    """
    Crea i parser disponibili.
    
    Args:
        config: Configurazione del sistema
        regex_service: Servizio regex condiviso (opzionale)
        
    Returns:
        Lista di parser configurati
    """
    from .multi_strategy_parser import MultiStrategyParser
    
    # Crea solo MultiStrategyParser con RegexService condiviso
    return [MultiStrategyParser(config, regex_service)]


def get_available_parsers() -> List[str]:
    """
    Restituisce la lista dei parser disponibili.
    
    WHY: Metodo di utilità per debugging e monitoring,
    fornendo visibilità sui parser disponibili nel sistema.
    
    Returns:
        Lista dei nomi dei parser disponibili
    """
    return [
        'cef',
        'syslog', 
        'adaptive',
        'csv',
        'xml_log',
        'office_parser',
        'binary_parser',
        'smart_excel_parser'
    ]


def create_specific_parser(parser_type: str, config: Dict[str, Any] = None) -> BaseParser:
    """
    Crea un parser specifico per tipo.
    
    WHY: Permette la creazione di parser specifici per testing
    e debugging, bypassando il parser universale.
    
    Args:
        parser_type: Tipo di parser da creare
        config: Configurazione opzionale
        
    Returns:
        Istanza del parser richiesto
        
    Raises:
        ValueError: Se il tipo di parser non è supportato
    """
    config = config or {}
    
    parser_map = {
        'adaptive': AdaptiveParser,
        'csv': CSVParser,
        'xml_log': XMLLogParser,
        'office_parser': OfficeParser,
        'binary_parser': BinaryParser,
        'smart_excel_parser': SmartExcelParser
    }
    
    if parser_type not in parser_map:
        raise ValueError(f"Parser type '{parser_type}' not supported. Available: {list(parser_map.keys())}")
    
    return parser_map[parser_type](**config) 