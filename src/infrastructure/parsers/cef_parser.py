"""Parser for Common Event Format (CEF)"""

import re
from typing import Dict, Any, Iterator

from .base_parser import BaseParser, ParseError
from ...core.services.regex_service import RegexService

class CEFParser(BaseParser):
    """Parser for Common Event Format (CEF)"""
    
    def __init__(self, strict_mode: bool = False):
        super().__init__(strict_mode)
        self.regex_service = RegexService()
        self.cef_pattern = self.regex_service.get_compiled_pattern('parsing_cef')
    
    def can_parse(self, content: str, filename: str = None) -> bool:
        lines = content.strip().split('\n')
        # Controlla se almeno il 70% delle righe non vuote sono CEF
        cef_lines = 0
        non_empty_lines = 0
        
        for line in lines[:100]:  # Controlla solo le prime 100 righe per performance
            line = line.strip()
            if line:
                non_empty_lines += 1
                if line.startswith('CEF:'):
                    cef_lines += 1
        
        return non_empty_lines > 0 and (cef_lines / non_empty_lines) >= 0.7
    
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            try:
                record = self._parse_cef_line(line)
                record['_metadata'] = {
                    'source_file': filename,
                    'line_number': line_num,
                    'parser': 'CEF'
                }
                yield record
            except Exception as e:
                error_msg = f"Errore parsing CEF: {str(e)}"
                self.log_error(error_msg, line_num, line)
                if not self.strict_mode:
                    # Restituisci almeno il contenuto grezzo
                    yield {
                        'raw_content': line,
                        'parse_error': str(e),
                        '_metadata': {
                            'source_file': filename,
                            'line_number': line_num,
                            'parser': 'CEF',
                            'status': 'parse_error'
                        }
                    }
    
    def _parse_cef_line(self, line: str) -> Dict[str, Any]:
        if not self.cef_pattern:
            raise ValueError("Pattern CEF non disponibile")
        
        match = self.cef_pattern.match(line)
        if not match:
            raise ValueError("Formato CEF non valido")
        
        record = match.groupdict()
        
        # Parsa l'extension (key=value pairs)
        extension = record.pop('extension', '')
        record['extensions'] = self._parse_cef_extensions(extension)
        
        # Converti severity in numero
        try:
            record['severity'] = int(record['severity'])
        except ValueError:
            self.log_warning(f"Severity non numerica: {record['severity']}")
        
        return record
    
    def _parse_cef_extensions(self, extension: str) -> Dict[str, Any]:
        """Parsa le estensioni CEF (key=value pairs)"""
        extensions = {}
        
        # Usa il pattern centralizzato per key-value pairs
        key_value_pattern = self.regex_service.get_compiled_pattern('parsing_key_value')
        if key_value_pattern:
            matches = key_value_pattern.findall(extension)
        else:
            # Fallback se il pattern non è disponibile
            pattern = r'(\w+)=([^=]*?)(?=\s+\w+=|$)'
            matches = re.findall(pattern, extension)
        
        for key, value in matches:
            value = value.strip()
            # Gestisci escape sequences
            value = value.replace('\\=', '=').replace('\\|', '|').replace('\\\\', '\\')
            
            # Prova a convertire in numero se possibile
            if value.isdigit():
                extensions[key] = int(value)
            elif value.replace('.', '').isdigit():
                extensions[key] = float(value)
            else:
                extensions[key] = value
        
        return extensions

