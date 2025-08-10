"""Parser for CSV and TSV files"""

import csv
from pathlib import Path
from typing import Dict, Any, Iterator, List

from .base_parser import BaseParser, ParseError

class CSVParser(BaseParser):
    """Parser per CSV e TSV"""
    
    def __init__(self, strict_mode: bool = False, delimiter: str = None):
        super().__init__(strict_mode)
        self.delimiter = delimiter
        self.detected_delimiter = None
        self.headers = None
        self._config = {}
    
    def set_config(self, config: Dict[str, Any]):
        """Set configuration for this parser."""
        self._config = config
    
    def _is_structured_log_data(self, headers: List[str]) -> bool:
        """Controlla se è un file di dati log già strutturati."""
        structured_indicators = [
            'LineId', 'EventId', 'EventTemplate', 'Content',
            'Component', 'Pid', 'Time', 'Timestamp'
        ]
        
        # Se ha almeno 3 indicatori di dati strutturati
        matches = sum(1 for header in headers if header in structured_indicators)
        return matches >= 3
    
    def can_parse(self, content: str, filename: str = None) -> bool:
        # Controlla estensione file
        if filename:
            ext = Path(filename).suffix.lower()
            if ext in ['.csv', '.tsv']:
                return True
        
        # Prova a rilevare delimitatori comuni
        lines = content.strip().split('\n')[:10]
        if not lines:
            return False
        
        delimiters = [',', '\t', ';', '|']
        for delimiter in delimiters:
            if self._test_delimiter(lines, delimiter):
                return True
        
        # Se non rileva delimitatori ma il file ha estensione CSV, prova comunque
        if filename and Path(filename).suffix.lower() == '.csv':
            return True
        
        return False
    
    def _test_delimiter(self, lines: List[str], delimiter: str) -> bool:
        """Testa se un delimitatore è consistente attraverso le righe"""
        if len(lines) < 2:
            return False
        
        try:
            reader = csv.reader(lines, delimiter=delimiter)
            rows = list(reader)
            if len(rows) < 2:
                return False
            
            # Controlla che il numero di colonne sia consistente
            first_row_cols = len(rows[0])
            if first_row_cols < 2:  # Almeno 2 colonne
                return False
            
            consistent_rows = sum(1 for row in rows if len(row) == first_row_cols)
            return (consistent_rows / len(rows)) >= 0.8
        except:
            return False
    
    def _detect_delimiter(self, content: str) -> str:
        """Auto-rileva il delimitatore"""
        if self.delimiter:
            return self.delimiter
        
        lines = content.strip().split('\n')[:10]
        delimiters = [',', '\t', ';', '|']
        
        for delimiter in delimiters:
            if self._test_delimiter(lines, delimiter):
                return delimiter
        
        return ','  # Default
    
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        self.detected_delimiter = self._detect_delimiter(content)
        
        lines = content.strip().split('\n')
        if not lines:
            return
        
        try:
            # Configura CSV reader con gestione errori robusta
            csv_reader = csv.reader(
                lines,
                delimiter=self.detected_delimiter,
                quotechar='"',
                skipinitialspace=True,
                strict=False  # Permette righe con numero diverso di colonne
            )
            
            # Leggi header
            try:
                headers = next(csv_reader)
                self.headers = [h.strip() for h in headers]
            except StopIteration:
                self.log_error("File CSV vuoto")
                return
            
            # Controlla se è un file di dati log già strutturati
            is_structured_log = self._is_structured_log_data(self.headers)
            
            # Processa le righe
            for line_num, row in enumerate(csv_reader, 2):  # Start from 2 (after header)
                try:
                    if is_structured_log:
                        record = self._process_structured_log_row(row, line_num, filename)
                    else:
                        record = self._process_csv_row(row, line_num, filename)
                    
                    if record:
                        yield record
                except Exception as e:
                    error_msg = f"Errore processing riga CSV: {str(e)}"
                    self.log_error(error_msg, line_num, str(row))
                    if not self.strict_mode:
                        yield {
                            'raw_content': self.detected_delimiter.join(row),
                            'parse_error': str(e),
                            '_metadata': {
                                'source_file': filename,
                                'line_number': line_num,
                                'parser': 'CSV',
                                'status': 'parse_error'
                            }
                        }
        
        except Exception as e:
            error_msg = f"Errore generale CSV parsing: {str(e)}"
            self.log_error(error_msg)
    
    def parse_single_line(self, line: str, filename: str = None, line_number: int = None) -> Dict[str, Any]:
        """Parse a single CSV line (for structured logs)."""
        if not self.headers:
            # Try to detect headers from the line itself
            self.detected_delimiter = self._detect_delimiter(line)
            csv_reader = csv.reader([line], delimiter=self.detected_delimiter)
            try:
                headers = next(csv_reader)
                self.headers = [h.strip() for h in headers]
                return None  # This was a header line
            except StopIteration:
                return None
        
        # Parse the data line
        csv_reader = csv.reader([line], delimiter=self.detected_delimiter)
        try:
            row = next(csv_reader)
            return self._process_structured_log_row(row, line_number or 1, filename)
        except Exception as e:
            error_msg = f"Errore parsing riga singola CSV: {str(e)}"
            self.log_error(error_msg, line_number, line)
            return None
    
    def _process_csv_row(self, row: List[str], line_num: int, filename: str) -> Dict[str, Any]:
        """Processa una singola riga CSV"""
        if len(row) != len(self.headers):
            self.log_warning(f"Numero colonne inconsistente: attese {len(self.headers)}, trovate {len(row)}", line_num)
            
            # Riempi colonne mancanti o tronca eccedenti
            if len(row) < len(self.headers):
                row.extend([''] * (len(self.headers) - len(row)))
            else:
                row = row[:len(self.headers)]
        
        record = {}
        for header, value in zip(self.headers, row):
            # Pulisci e converti valori
            value = value.strip()
            
            # Prova conversioni automatiche
            if value == '':
                record[header] = None
            elif value.lower() in ['true', 'false']:
                record[header] = value.lower() == 'true'
            elif value.isdigit():
                record[header] = int(value)
            elif self._is_float(value):
                record[header] = float(value)
            else:
                record[header] = value
        
        record['_metadata'] = {
            'source_file': filename,
            'line_number': line_num,
            'parser': 'CSV',
            'delimiter': self.detected_delimiter
        }
        
        return record
    
    def _process_structured_log_row(self, row: List[str], line_num: int, filename: str) -> Dict[str, Any]:
        """Processa una riga di dati log già strutturati"""
        if len(row) != len(self.headers):
            self.log_warning(f"Numero colonne inconsistente: attese {len(self.headers)}, trovate {len(row)}", line_num)
            
            # Riempi colonne mancanti o tronca eccedenti
            if len(row) < len(self.headers):
                row.extend([''] * (len(self.headers) - len(row)))
            else:
                row = row[:len(self.headers)]
        
        record = {}
        for header, value in zip(self.headers, row):
            # Pulisci e converti valori
            value = value.strip()
            
            # Prova conversioni automatiche
            if value == '':
                record[header] = None
            elif value.lower() in ['true', 'false']:
                record[header] = value.lower() == 'true'
            elif value.isdigit():
                record[header] = int(value)
            elif self._is_float(value):
                record[header] = float(value)
            else:
                record[header] = value
        
        # Aggiungi metadati specifici per dati strutturati
        record['_metadata'] = {
            'source_file': filename,
            'line_number': line_num,
            'parser': 'CSV_STRUCTURED',
            'delimiter': self.detected_delimiter,
            'data_type': 'structured_log'
        }
        
        return record
    
    def _is_float(self, value: str) -> bool:
        """Controlla se una stringa può essere convertita in float"""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def _anonymize_data(self, data: Any) -> Any:
        """
        Anonymize CSV data using configuration.
        
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
                    anonymized[key] = value
            return anonymized
        elif isinstance(data, list):
            return [self._anonymize_data(item) for item in data]
        else:
            return data

