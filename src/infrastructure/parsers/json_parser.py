"""Parser for JSON and JSONL"""

import json
from typing import Dict, Any, Iterator

from .base_parser import BaseParser, ParseError

class JSONParser(BaseParser):
    """Parser per JSON e JSONL"""
    
    def __init__(self, strict_mode: bool = False):
        super().__init__(strict_mode)
        self._config = {}
    
    def set_config(self, config: Dict[str, Any]):
        """Set configuration for this parser."""
        self._config = config
    
    def can_parse(self, content: str, filename: str = None) -> bool:
        content = content.strip()
        
        # Controlla se è JSON valido
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            pass
        
        # Controlla se è JSONL (JSON Lines)
        lines = content.split('\n')
        json_lines = 0
        non_empty_lines = 0
        
        for line in lines[:100]:
            line = line.strip()
            if line:
                non_empty_lines += 1
                try:
                    json.loads(line)
                    json_lines += 1
                except json.JSONDecodeError:
                    pass
        
        return non_empty_lines > 0 and (json_lines / non_empty_lines) >= 0.8
    
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        content = content.strip()
        
        # Prova prima come JSON singolo
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for i, record in enumerate(data):
                    if isinstance(record, dict):
                        record['_metadata'] = {
                            'source_file': filename,
                            'array_index': i,
                            'parser': 'JSON'
                        }
                        yield record
                    else:
                        yield {
                            'value': record,
                            '_metadata': {
                                'source_file': filename,
                                'array_index': i,
                                'parser': 'JSON'
                            }
                        }
            elif isinstance(data, dict):
                data['_metadata'] = {
                    'source_file': filename,
                    'parser': 'JSON'
                }
                yield data
            else:
                yield {
                    'value': data,
                    '_metadata': {
                        'source_file': filename,
                        'parser': 'JSON'
                    }
                }
            return
        except json.JSONDecodeError:
            pass
        
        # Prova come JSONL
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    record['_metadata'] = {
                        'source_file': filename,
                        'line_number': line_num,
                        'parser': 'JSONL'
                    }
                    yield record
                else:
                    yield {
                        'value': record,
                        '_metadata': {
                            'source_file': filename,
                            'line_number': line_num,
                            'parser': 'JSONL'
                        }
                    }
            except json.JSONDecodeError as e:
                self.log_error(f"JSON non valido: {str(e)}", line_num, line)
                if not self.strict_mode:
                    yield {
                        'raw_content': line,
                        'parse_error': str(e),
                        '_metadata': {
                            'source_file': filename,
                            'line_number': line_num,
                            'parser': 'JSONL',
                            'status': 'parse_error'
                        }
                    }
    
    def _anonymize_data(self, data: Any) -> Any:
        """
        Anonymize JSON data using configuration.
        
        Args:
            data: Data to anonymize
            
        Returns:
            Anonymized data
        """
        # Get anonymization configuration
        drain3_config = self._config.get("drain3", {})
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

