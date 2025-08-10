"""Universal File Parser - Tool per convertire diversi formati strutturati in JSON
Supporta: CEF, Syslog, JSON, CSV, TSV, TXT strutturato
"""

import json
import csv
import re
import logging
import gzip
import zipfile
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Iterator, Union
from pathlib import Path
from datetime import datetime
from io import StringIO, BytesIO
import chardet

from ...domain.interfaces.log_parser import LogParser
from ...domain.entities.parsed_record import ParsedRecord
from ...domain.entities.log_entry import LogEntry
from ...core.services.regex_service import RegexService
from .adaptive_parser import AdaptiveParser
from .multi_strategy_parser import MultiStrategyParser
from .json_parser import JSONParser
from .fortinet_parser import FortinetLogParser
from .apache_parser import ApacheLogParser
# from .csv_parser import CSVParser  # Rimosso per evitare conflitti con MultiStrategyParser
# from .robust_csv_parser import RobustCSVParser  # Rimosso per evitare conflitti con MultiStrategyParser


class ParseError(Exception):
    """Eccezione personalizzata per errori di parsing"""
    def __init__(self, message: str, line_number: int = None, original_line: str = None):
        self.message = message
        self.line_number = line_number
        self.original_line = original_line
        super().__init__(f"Line {line_number}: {message}" if line_number else message)


class BaseParser(ABC):
    """Classe base astratta per tutti i parser"""
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.errors = []
        self.warnings = []
        
    @abstractmethod
    def can_parse(self, content: str, filename: str = None) -> bool:
        """Determina se questo parser può gestire il contenuto"""
        pass
    
    @abstractmethod
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        """Parsa il contenuto e restituisce record JSON"""
        pass
    
    def log_error(self, message: str, line_number: int = None, line_content: str = None):
        """Registra un errore"""
        error = {
            'message': message,
            'line_number': line_number,
            'line_content': line_content,
            'timestamp': datetime.now().isoformat()
        }
        self.errors.append(error)
        
        if self.strict_mode:
            raise ParseError(message, line_number, line_content)
    
    def log_warning(self, message: str, line_number: int = None):
        """Registra un warning"""
        warning = {
            'message': message,
            'line_number': line_number,
            'timestamp': datetime.now().isoformat()
        }
        self.warnings.append(warning)




















class ParserOrchestrator(LogParser):
    """Orchestratore che coordina tutti i parser specifici"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.strict_mode = config.get("strict_mode", False)
        
        # Parser multi-strategy universale (priorità massima)
        self.multi_strategy_parser = MultiStrategyParser(config)
        
        # Parser adattivo universale (seconda priorità)
        self.adaptive_parser = UniversalAdaptiveParser(config)
        
        # Parser robusto per file problematici (terza priorità)
        # self.robust_csv_parser = RobustCSVParser(config)  # Rimosso per evitare conflitti con MultiStrategyParser
        
        # Parser specifici come fallback
        self.parsers = [
            JSONParser(self.strict_mode),
            FortinetLogParser(self.strict_mode),
            ApacheLogParser(self.strict_mode),
            # CSVParser(self.strict_mode),  # Rimosso per evitare conflitti con MultiStrategyParser
        ]
        # Passa la configurazione completa ai parser che la supportano
        for parser in self.parsers:
            if hasattr(parser, 'set_config'):
                parser.set_config(config)
        self.encoding_errors = []
    
    @property
    def name(self) -> str:
        """Get the name of this parser."""
        return "UniversalFileParser"
    
    @property
    def supported_formats(self) -> list[str]:
        """Get list of supported formats."""
        return ["json", "csv", "syslog", "cef", "fortinet", "apache", "txt"]
    
    @property
    def priority(self) -> int:
        """Get parser priority (lower = higher priority)."""
        return 1  # High priority since it's universal
    
    def can_parse(self, content: str, filename: Optional[Path] = None) -> bool:
        """Sempre True per il parser universale"""
        return True
    
    def parse(self, log_entry: "LogEntry") -> Iterator[ParsedRecord]:
        """Parsa il contenuto usando il parser multi-strategy universale"""
        content = log_entry.content
        source_file = log_entry.source_file
        line_number = log_entry.line_number
        
        try:
            # Usa prima il parser multi-strategy universale
            try:
                yield from self.multi_strategy_parser.parse(log_entry)
                return
            except Exception as e:
                print(f"⚠️ MULTI-STRATEGY PARSER FAILED [{source_file}:{line_number}]: {str(e)}")
                # Fallback al parser adattivo
            
            # Fallback al parser adattivo universale
            try:
                yield from self.adaptive_parser.parse(log_entry)
                return
            except Exception as e:
                print(f"⚠️ ADAPTIVE PARSER FAILED [{source_file}:{line_number}]: {str(e)}")
                # Fallback al parser robusto per file problematici
            
            # Fallback al parser robusto per file problematici
            # Rimosso per evitare conflitti con MultiStrategyParser
            # try:
            #     if self.robust_csv_parser.can_parse(content, str(source_file) if source_file else None):
            #         yield from self.robust_csv_parser.parse(log_entry)
            #         return
            # except Exception as e:
            #     print(f"⚠️ ROBUST CSV PARSER FAILED [{source_file}:{line_number}]: {str(e)}")
            #     # Fallback ai parser specifici
            
            # Special handling for CSV structured logs (single lines only)
            # Rimosso per evitare conflitti con MultiStrategyParser
            # if (source_file and source_file.suffix.lower() == '.csv' and 
            #     isinstance(content, str) and ',' in content and
            #     '\n' not in content):  # Only for single lines
            #     
            #     # Check if this might be a structured log line
            #     csv_parser = next((p for p in self.parsers if isinstance(p, CSVParser)), None)
            #     if csv_parser:
            #         # Try to parse as single line
            #         record = csv_parser.parse_single_line(content, str(source_file), line_number)
            #         if record:
            #             # Crea la struttura serializzata
            #             serialized_data = {
            #                 'original': record,
            #                 'anonymized': self._anonymize_data(record),
            #                 'extracted_fields': self._extract_common_fields(record),
            #                 'parser_used': 'CSVParser'
            #             }
            #             
            #             yield ParsedRecord(
            #                 original_content=content,
            #                 parsed_data=serialized_data,
            #                 parser_name="csv_structured",
            #                 source_file=source_file,
            #                 line_number=line_number,
            #                 confidence_score=1.0,
            #             )
            #             return
            
            # Trova il parser appropriato
            selected_parser = None
            for parser in self.parsers:
                if parser.can_parse(content, str(source_file)):
                    selected_parser = parser
                    break
            
            if not selected_parser:
                # Fallback: tratta come testo generico
                error_msg = 'Nessun parser appropriato trovato'
                print(f"⚠️ NO PARSER FOUND [{source_file}:{line_number}]: {error_msg}")
                yield ParsedRecord(
                    original_content=content,
                    parsed_data={
                        'content': content,
                        'parse_error': error_msg,
                        'original': content,
                        'anonymized': content,
                        'extracted_fields': {}
                    },
                    parser_name="fallback",
                    source_file=source_file,
                    line_number=line_number,
                )
                return
            
            # Parsa usando il parser selezionato
            try:
                # I parser specifici restituiscono generatori, prendiamo il primo risultato
                parsed_results = list(selected_parser.parse(content, str(source_file)))
                
                if not parsed_results:
                    error_msg = 'Nessun record parsato'
                    print(f"⚠️ NO PARSED RECORDS [{source_file}:{line_number}]: {error_msg}")
                    yield ParsedRecord(
                        original_content=content,
                        parsed_data={
                            'parse_error': error_msg,
                            'original': content,
                            'anonymized': content,
                            'extracted_fields': {}
                        },
                        parser_name="error",
                        source_file=source_file,
                        line_number=line_number,
                    )
                    return
                
                # Prendiamo il primo risultato
                parsed_data = parsed_results[0]
                
                # Se è un dizionario, lo convertiamo in ParsedRecord
                if isinstance(parsed_data, dict):
                    # Crea la struttura serializzata
                    serialized_data = {
                        'original': parsed_data,
                        'anonymized': self._anonymize_data(parsed_data),
                        'extracted_fields': self._extract_common_fields(parsed_data),
                        'parser_used': selected_parser.__class__.__name__
                    }
                    
                    yield ParsedRecord(
                        original_content=content,
                        parsed_data=serialized_data,
                        parser_name=selected_parser.__class__.__name__.lower().replace('parser', ''),
                        source_file=source_file,
                        line_number=line_number,
                        confidence_score=1.0,
                    )
                else:
                    # Se è già un ParsedRecord, lo restituiamo direttamente
                    yield parsed_data
                    
            except Exception as e:
                error_msg = f'Errore durante il parsing: {str(e)}'
                print(f"❌ PARSER ERROR [{source_file}:{line_number}]: {error_msg}")
                yield ParsedRecord(
                    original_content=content,
                    parsed_data={
                        'parse_error': error_msg,
                        'original': content,
                        'anonymized': content,
                        'extracted_fields': {}
                    },
                    parser_name="error",
                    source_file=source_file,
                    line_number=line_number,
                ).add_error(str(e))
            
        except Exception as e:
            yield ParsedRecord(
                original_content=content,
                parsed_data={
                    'parse_error': str(e),
                    'original': content,
                    'anonymized': content,
                    'extracted_fields': {}
                },
                parser_name="error",
                source_file=source_file,
                line_number=line_number,
            ).add_error(str(e))
    
    def _anonymize_data(self, data: Any) -> Any:
        """Anonimizza i dati"""
        # Get anonymization configuration
        drain3_config = self.config.get("drain3", {})
        anonymization_config = drain3_config.get("anonymization", {})
        always_anonymize = anonymization_config.get("always_anonymize", [])
        replace_methods = anonymization_config.get("methods", {}).get("replace", {})
        
        if isinstance(data, dict):
            anonymized = {}
            for key, value in data.items():
                # Check if field should be anonymized
                if key.lower() in [field.lower() for field in always_anonymize]:
                    # Use replacement method if configured
                    replacement = replace_methods.get(key, f"<{key.upper()}>")
                    anonymized[key] = replacement
                else:
                    anonymized[key] = self._anonymize_data(value)
            return anonymized
        elif isinstance(data, list):
            return [self._anonymize_data(item) for item in data]
        else:
            return data
    
    def _extract_common_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estrae campi comuni dal record parsato"""
        extracted = {}
        
        # Cerca campi comuni
        common_fields = ['timestamp', 'level', 'service', 'message', 'ip', 'hostname']
        
        for field in common_fields:
            if field in data:
                extracted[field] = data[field]
        
        return extracted 