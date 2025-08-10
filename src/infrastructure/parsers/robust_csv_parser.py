"""
Parser robusto per file CSV problematici.

WHY: Alcuni file CSV complessi causano loop infiniti nel parser adattivo.
Questo parser implementa una strategia semplificata ma robusta per gestire
file problematici senza analisi complessa.
"""

import csv
import io
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

from .base_parser_abc import BaseParserABC as BaseParser
from ...domain.entities.parsed_record import ParsedRecord


@dataclass
class CSVHeaderInfo:
    """Informazioni sugli header CSV rilevati."""
    headers: List[str]
    delimiter: str
    confidence: float
    has_headers: bool


class RobustCSVParser(BaseParser):
    """
    Parser CSV robusto per file problematici.
    
    WHY: Bypassa l'analisi adattiva complessa e usa una strategia
    semplificata ma affidabile per file che causano loop infiniti.
    
    Contract:
        - Input: Contenuto CSV
        - Output: Iterator di record parsati
        - Side effects: Logging di errori
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inizializza il parser CSV robusto.
        
        Args:
            config: Configurazione opzionale
        """
        super().__init__(config)
        self.max_lines_analyzed = 10  # Limite per analisi header
        self.common_delimiters = [',', ';', '|', '\t']
    
    def can_parse(self, content: str, filename: str = None) -> bool:
        """
        Determina se il contenuto può essere parsato come CSV robusto.
        
        Args:
            content: Contenuto da analizzare
            filename: Nome del file
            
        Returns:
            True se il contenuto sembra essere CSV
        """
        lines = content.strip().split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        # Richiede almeno 2 righe non vuote
        if len(non_empty_lines) < 2:
            return False
        
        # Verifica se contiene delimitatori comuni
        for delimiter in self.common_delimiters:
            if delimiter in non_empty_lines[0]:
                return True
        
        return False
    
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        """
        Parsa il contenuto CSV usando una strategia robusta.
        
        Args:
            content: Contenuto CSV da parsare
            filename: Nome del file
            
        Yields:
            Record parsati
        """
        lines = content.strip().split('\n')
        
        # Identifica header e delimitatori
        header_info = self._detect_csv_structure(lines)
        
        if not header_info:
            self.logger.warning(f"Impossibile identificare struttura CSV per {filename}")
            return
        
        self.logger.info(f"Struttura CSV rilevata per {filename}: "
                        f"{len(header_info.headers)} campi, "
                        f"delimiter '{header_info.delimiter}', "
                        f"confidence {header_info.confidence:.2f}")
        
        # Parsa ogni riga
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                parsed_record = self._parse_csv_line(line, header_info, i)
                if parsed_record:
                    # Assicurati che il record abbia il contenuto originale
                    if 'raw_line' in parsed_record:
                        parsed_record['original_content'] = parsed_record['raw_line']
                    else:
                        parsed_record['original_content'] = line
                    yield parsed_record
            except Exception as e:
                self.logger.warning(f"Errore parsing riga {i} in {filename}: {e}")
                continue
    
    def _detect_csv_structure(self, lines: List[str]) -> Optional[CSVHeaderInfo]:
        """
        Rileva la struttura CSV in modo robusto.
        
        Args:
            lines: Righe del file
            
        Returns:
            Informazioni sulla struttura CSV
        """
        # Analizza solo le prime righe per performance
        sample_lines = lines[:self.max_lines_analyzed]
        
        # Prova ogni delimitatore
        for delimiter in self.common_delimiters:
            try:
                header_info = self._test_delimiter(sample_lines, delimiter)
                if header_info and header_info.confidence > 0.5:
                    return header_info
            except Exception as e:
                self.logger.debug(f"Errore test delimiter '{delimiter}': {e}")
                continue
        
        # Fallback: usa virgola come default
        return CSVHeaderInfo(
            headers=[f"field_{i}" for i in range(10)],
            delimiter=',',
            confidence=0.3,
            has_headers=False
        )
    
    def _test_delimiter(self, lines: List[str], delimiter: str) -> Optional[CSVHeaderInfo]:
        """
        Testa un delimitatore specifico.
        
        Args:
            lines: Righe da testare
            delimiter: Delimitatore da testare
            
        Returns:
            Informazioni sulla struttura o None
        """
        if not lines:
            return None
        
        # Conta il numero di campi per riga
        field_counts = []
        for line in lines:
            if delimiter in line:
                field_counts.append(len(line.split(delimiter)))
        
        if not field_counts:
            return None
        
        # Calcola consistenza
        avg_fields = sum(field_counts) / len(field_counts)
        consistency = 1.0 - (max(field_counts) - min(field_counts)) / avg_fields if avg_fields > 0 else 0.0
        
        # Se la consistenza è alta, probabilmente è CSV
        if consistency > 0.7:
            # Prova a identificare header
            first_line = lines[0]
            if delimiter in first_line:
                headers = [h.strip() for h in first_line.split(delimiter)]
                has_headers = self._looks_like_header(headers)
                
                return CSVHeaderInfo(
                    headers=headers if has_headers else [f"field_{i}" for i in range(len(headers))],
                    delimiter=delimiter,
                    confidence=consistency,
                    has_headers=has_headers
                )
        
        return None
    
    def _looks_like_header(self, headers: List[str]) -> bool:
        """
        Determina se una riga sembra essere un header.
        
        Args:
            headers: Campi della riga
            
        Returns:
            True se sembra essere un header
        """
        if not headers:
            return False
        
        # Conta campi che sembrano nomi di colonna
        header_indicators = 0
        for header in headers:
            header_lower = header.lower()
            
            # Indicatori di header
            if any(word in header_lower for word in ['id', 'name', 'type', 'status', 'time', 'date', 'ip', 'user']):
                header_indicators += 1
            elif header_lower.isalpha() or header_lower.replace('_', '').isalpha():
                header_indicators += 1
            elif len(header) > 0 and header[0].isalpha():
                header_indicators += 1
        
        # Se più della metà sembra essere header
        return header_indicators > len(headers) * 0.5
    
    def _parse_csv_line(self, line: str, header_info: CSVHeaderInfo, line_number: int) -> Optional[Dict[str, Any]]:
        """
        Parsa una singola riga CSV.
        
        Args:
            line: Riga CSV da parsare
            header_info: Informazioni sulla struttura CSV
            line_number: Numero di riga
            
        Returns:
            Record parsato o None
        """
        try:
            if not line.strip():
                return None
            
            # Dividi la riga usando il delimitatore
            parts = line.split(header_info.delimiter)
            
            # Crea record base
            record = {
                'line_number': line_number,
                'raw_line': line,
                'parser_type': 'robust_csv',
                'parsed_at': datetime.now().isoformat(),
                'structure_confidence': header_info.confidence,
                'csv_headers': header_info.headers,
                'has_headers': header_info.has_headers
            }
            
            # Mappa i valori agli header
            for i, header in enumerate(header_info.headers):
                if i < len(parts):
                    value = parts[i].strip()
                    record[header] = value
                else:
                    record[header] = ""
            
            # Aggiungi campi extra se ci sono più valori che header
            for i in range(len(header_info.headers), len(parts)):
                record[f'extra_field_{i}'] = parts[i].strip()
            
            return record
            
        except Exception as e:
            self.logger.warning(f"Errore parsing riga CSV {line_number}: {e}")
            return None 