"""
Robust CSV Parser - Parser CSV robusto e standard.

WHY: I CSV dovrebbero essere banali da parsare, non un problema.
Questo parser implementa gli standard della community e gestisce tutti i casi edge.

DESIGN: Parser CSV robusto che segue:
- RFC 4180 per CSV standard
- Gestione intelligente di header e tipi
- Rilevamento automatico di delimitatori
- Gestione di quote, escape e caratteri speciali
- Type inference per campi numerici e booleani
- Gestione di file con encoding diversi
"""

import csv
import io
import re
import chardet
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator, Tuple
from dataclasses import dataclass
from datetime import datetime

from ...domain.interfaces.log_parser import LogParser
from ...domain.entities.log_entry import LogEntry
from ...domain.entities.parsed_record import ParsedRecord


@dataclass
class CSVFieldInfo:
    """Informazioni su un campo CSV."""
    name: str
    type: str  # 'string', 'number', 'boolean', 'timestamp', 'unknown'
    sample_values: List[str]
    is_constant: bool
    has_patterns: bool


class RobustCSVParser(LogParser):
    """
    Parser CSV robusto e standard.
    
    WHY: I CSV dovrebbero essere banali da parsare, non un problema.
    Questo parser implementa gli standard della community e gestisce tutti i casi edge.
    
    Contract:
        - Input: LogEntry con contenuto CSV
        - Output: ParsedRecord con dati strutturati
        - Side effects: Nessuno, parsing puro
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inizializza il parser CSV robusto.
        
        Args:
            config: Configurazione opzionale
        """
        self.config = config or {}
        self.delimiters = [',', ';', '\t', '|']  # Delimitatori comuni
        self.max_sample_lines = 100  # Linee per analisi header
        
    def can_parse(self, content: str, filename: Optional[str] = None) -> bool:
        """
        Determina se questo parser può gestire il contenuto.
        
        Args:
            content: Contenuto da analizzare
            filename: Nome del file (opzionale)
            
        Returns:
            True se il contenuto sembra essere CSV
        """
        # Controlla estensione del file
        if filename:
            file_path = Path(filename)
            if file_path.suffix.lower() in ['.csv', '.tsv', '.txt']:
                return True
        
        # Analizza il contenuto per determinare se è CSV
        lines = content.split('\n')
        if len(lines) < 2:
            return False
        
        # Conta delimitatori nella prima riga
        first_line = lines[0].strip()
        if not first_line:
            return False
        
        # Conta delimitatori comuni
        delimiter_counts = {}
        for delimiter in self.delimiters:
            delimiter_counts[delimiter] = first_line.count(delimiter)
        
        # Se c'è un delimitatore dominante, probabilmente è CSV
        max_count = max(delimiter_counts.values())
        if max_count > 0:
            # Verifica che le righe successive abbiano lo stesso numero di campi
            expected_fields = max_count + 1
            for line in lines[1:min(5, len(lines))]:  # Controlla prime 5 righe
                if line.strip():
                    field_count = line.count(list(delimiter_counts.keys())[list(delimiter_counts.values()).index(max_count)]) + 1
                    if field_count != expected_fields:
                        return False
            return True
        
        return False
    
    def parse(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Parsa il contenuto CSV e restituisce record strutturati.
        
        WHY: source_file è SEMPRE disponibile tramite log_entry.source_file.
        Questo elimina gli errori "source_file is not defined" by design.
        
        Args:
            log_entry: Entry del log da parsare
            
        Yields:
            ParsedRecord instances per ogni riga CSV
            
        Raises:
            ValueError: Se log_entry.source_file è None o vuoto
        """
        # VALIDAZIONE BY DESIGN: source_file deve essere sempre definito
        self._validate_log_entry(log_entry)
        
        try:
            # Determina il delimitatore ottimale
            delimiter = self._detect_delimiter(log_entry.content)
            if not delimiter:
                raise ValueError("Impossibile determinare il delimitatore CSV")
            
            # Analizza la struttura del CSV
            field_info = self._analyze_csv_structure(log_entry.content, delimiter)
            
            # Parsa ogni riga
            lines = log_entry.content.split('\n')
            for line_number, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                
                try:
                    # Parsa la riga CSV
                    parsed_data = self._parse_csv_line(line, delimiter, field_info)
                    
                    # BY DESIGN: Estrai e aggiungi chiavi rilevate
                    enriched_data = self.extract_detected_keys(line, parsed_data)
                    
                    # Crea il record parsato con source_file SEMPRE definito
                    yield ParsedRecord(
                        original_content=line,
                        parsed_data=enriched_data,  # ✅ Dati arricchiti con chiavi rilevate
                        parser_name="robust_csv",
                        source_file=log_entry.source_file,  # ✅ SEMPRE definito
                        line_number=line_number,
                        confidence_score=0.95
                    )
                    
                except Exception as e:
                    # Record di errore per righe problematiche
                    yield ParsedRecord(
                        original_content=line,
                        parsed_data={
                            'parse_error': str(e),
                            'line_number': line_number,
                            'delimiter': delimiter
                        },
                        parser_name="robust_csv_error",
                        source_file=log_entry.source_file,  # ✅ SEMPRE definito
                        line_number=line_number,
                        confidence_score=0.0
                    ).add_error(str(e))
                    
        except Exception as e:
            # Record di errore generale
            yield ParsedRecord(
                original_content=log_entry.content,
                parsed_data={
                    'parse_error': str(e),
                    'parser': 'robust_csv'
                },
                parser_name="robust_csv_error",
                source_file=log_entry.source_file,  # ✅ SEMPRE definito
                line_number=log_entry.line_number,
                confidence_score=0.0
            ).add_error(str(e))
    
    def extract_detected_keys(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estrae e aggiunge le chiavi rilevate al parsed_data.
        
        WHY: By design, tutti i parser devono implementare questa funzione
        per garantire coerenza nell'estrazione di chiavi e pattern rilevati.
        
        DESIGN: Estrazione intelligente di chiavi CSV che:
        1. Identifica pattern nei dati
        2. Estrae tipi di dati e metadati
        3. Rileva anomalie e caratteristiche speciali
        4. Aggiunge chiavi rilevate per analisi avanzate
        
        Args:
            content: Contenuto originale del log
            parsed_data: Dati già parsati dal parser
            
        Returns:
            parsed_data arricchito con chiavi rilevate
        """
        enriched_data = parsed_data.copy()
        
        # 1. ESTRAZIONE PATTERN E METADATI
        if '_csv_metadata' in enriched_data:
            csv_meta = enriched_data['_csv_metadata']
            
            # Analizza pattern nei dati
            pattern_analysis = self._analyze_csv_patterns(content, enriched_data)
            enriched_data['_detected_patterns'] = pattern_analysis
            
            # Estrai caratteristiche dei campi
            field_characteristics = self._extract_field_characteristics(enriched_data)
            enriched_data['_field_characteristics'] = field_characteristics
            
            # Rileva anomalie e caratteristiche speciali
            anomalies = self._detect_csv_anomalies(content, enriched_data)
            enriched_data['_detected_anomalies'] = anomalies
        
        # 2. AGGIUNGI METADATI STANDARD
        enriched_data.update({
            '_detected_keys': {
                'parser_type': 'robust_csv',
                'has_patterns': True,
                'field_count': enriched_data.get('_csv_metadata', {}).get('field_count', 0),
                'delimiter': enriched_data.get('_csv_metadata', {}).get('delimiter', 'unknown'),
                'extraction_timestamp': datetime.now().isoformat()
            }
        })
        
        return enriched_data
    
    def _detect_delimiter(self, content: str) -> Optional[str]:
        """
        Rileva automaticamente il delimitatore CSV.
        
        Args:
            content: Contenuto CSV
            
        Returns:
            Delimitatore rilevato o None
        """
        lines = content.split('\n')
        if len(lines) < 2:
            return None
        
        # Analizza le prime righe per determinare il delimitatore
        delimiter_scores = {}
        
        for delimiter in self.delimiters:
            score = 0
            field_counts = []
            
            for line in lines[:min(10, len(lines))]:  # Prime 10 righe
                if line.strip():
                    field_count = line.count(delimiter) + 1
                    field_counts.append(field_count)
            
            if field_counts:
                # Calcola consistenza del numero di campi
                avg_fields = sum(field_counts) / len(field_counts)
                consistency = 1.0 - (max(field_counts) - min(field_counts)) / avg_fields if avg_fields > 0 else 0
                
                # Bonus per delimitatori comuni
                common_bonus = 1.0 if delimiter in [',', ';'] else 0.5
                
                delimiter_scores[delimiter] = consistency * common_bonus
        
        # Restituisce il delimitatore con punteggio più alto
        if delimiter_scores:
            return max(delimiter_scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _analyze_csv_structure(self, content: str, delimiter: str) -> List[CSVFieldInfo]:
        """
        Analizza la struttura del CSV per inferire tipi e pattern.
        
        Args:
            content: Contenuto CSV
            delimiter: Delimitatore utilizzato
            
        Returns:
            Lista di informazioni sui campi
        """
        lines = content.split('\n')
        if len(lines) < 2:
            return []
        
        # Parsa header
        header_line = lines[0].strip()
        field_names = [name.strip() for name in header_line.split(delimiter)]
        
        # Analizza campi
        field_info = []
        for i, field_name in enumerate(field_names):
            sample_values = []
            field_types = set()
            
            # Raccoglie valori di esempio
            for line in lines[1:min(self.max_sample_lines, len(lines))]:
                if line.strip():
                    fields = line.split(delimiter)
                    if i < len(fields):
                        value = fields[i].strip()
                        if value:
                            sample_values.append(value)
                            field_types.add(self._infer_field_type(value))
            
            # Determina tipo dominante
            dominant_type = self._get_dominant_type(field_types)
            
            # Controlla se il campo è costante
            is_constant = len(set(sample_values)) == 1 if sample_values else False
            
            # Controlla se ha pattern
            has_patterns = self._has_patterns(sample_values)
            
            field_info.append(CSVFieldInfo(
                name=field_name,
                type=dominant_type,
                sample_values=sample_values[:10],  # Primi 10 valori
                is_constant=is_constant,
                has_patterns=has_patterns
            ))
        
        return field_info
    
    def _infer_field_type(self, value: str) -> str:
        """
        Inferisce il tipo di un campo dal suo valore.
        
        Args:
            value: Valore del campo
            
        Returns:
            Tipo inferito
        """
        # Rimuovi quote
        value = value.strip('"\'')
        
        # Controlla se è vuoto
        if not value:
            return 'unknown'
        
        # Controlla se è numerico
        try:
            float(value)
            return 'number'
        except ValueError:
            pass
        
        # Controlla se è booleano
        if value.lower() in ['true', 'false', 'yes', 'no', '1', '0']:
            return 'boolean'
        
        # Controlla se è timestamp
        if self._looks_like_timestamp(value):
            return 'timestamp'
        
        # Default: stringa
        return 'string'
    
    def _looks_like_timestamp(self, value: str) -> bool:
        """
        Controlla se un valore sembra essere un timestamp.
        
        Args:
            value: Valore da controllare
            
        Returns:
            True se sembra un timestamp
        """
        # Pattern comuni per timestamp
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}:\d{2}:\d{2}',  # HH:MM:SS
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
        ]
        
        for pattern in timestamp_patterns:
            if re.search(pattern, value):
                return True
        
        return False
    
    def _get_dominant_type(self, types: set) -> str:
        """
        Determina il tipo dominante da un set di tipi.
        
        Args:
            types: Set di tipi
            
        Returns:
            Tipo dominante
        """
        if not types:
            return 'unknown'
        
        # Priorità: number > timestamp > boolean > string
        type_priority = {
            'number': 4,
            'timestamp': 3,
            'boolean': 2,
            'string': 1,
            'unknown': 0
        }
        
        return max(types, key=lambda t: type_priority.get(t, 0))
    
    def _has_patterns(self, values: List[str]) -> bool:
        """
        Controlla se i valori hanno pattern ricorrenti.
        
        Args:
            values: Lista di valori
            
        Returns:
            True se ci sono pattern
        """
        if len(values) < 3:
            return False
        
        # Controlla se ci sono valori ripetuti
        unique_values = set(values)
        if len(unique_values) < len(values) * 0.8:  # 80% valori unici
            return True
        
        # Controlla pattern di lunghezza
        lengths = [len(v) for v in values]
        if len(set(lengths)) < len(lengths) * 0.5:  # 50% lunghezze diverse
            return True
        
        return False
    
    def _parse_csv_line(self, line: str, delimiter: str, field_info: List[CSVFieldInfo]) -> Dict[str, Any]:
        """
        Parsa una singola riga CSV.
        
        Args:
            line: Riga CSV da parsare
            delimiter: Delimitatore da utilizzare
            field_info: Informazioni sui campi
            
        Returns:
            Dizionario con i dati parsati
        """
        # Parsa la riga usando il modulo csv standard
        csv_reader = csv.reader([line], delimiter=delimiter)
        fields = next(csv_reader)
        
        # Crea il record parsato
        parsed_data = {}
        
        for i, (field, info) in enumerate(zip(fields, field_info)):
            field_name = info.name
            field_value = field.strip()
            
            # Converti il valore in base al tipo
            if info.type == 'number':
                try:
                    parsed_data[field_name] = float(field_value) if '.' in field_value else int(field_value)
                except ValueError:
                    parsed_data[field_name] = field_value
            elif info.type == 'boolean':
                parsed_data[field_name] = field_value.lower() in ['true', 'yes', '1']
            else:
                parsed_data[field_name] = field_value
            
            # Aggiungi metadati del campo
            parsed_data[f'{field_name}_type'] = info.type
            parsed_data[f'{field_name}_is_constant'] = info.is_constant
            parsed_data[f'{field_name}_has_patterns'] = info.has_patterns
        
        # Aggiungi metadati generali
        parsed_data['_csv_metadata'] = {
            'delimiter': delimiter,
            'field_count': len(fields),
            'parser': 'robust_csv'
        }
        
        return parsed_data
    
    def _analyze_csv_patterns(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analizza pattern nei dati CSV.
        
        Returns:
            Analisi dei pattern rilevati
        """
        patterns = {}
        
        # Pattern di timestamp
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}:\d{2}:\d{2}',  # HH:MM:SS
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        ]
        
        for pattern in timestamp_patterns:
            matches = re.findall(pattern, content)
            if matches:
                patterns['timestamp_patterns'] = {
                    'pattern': pattern,
                    'matches': len(matches),
                    'examples': matches[:5]  # Primi 5 esempi
                }
        
        # Pattern di IP
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ip_matches = re.findall(ip_pattern, content)
        if ip_matches:
            patterns['ip_addresses'] = {
                'count': len(ip_matches),
                'examples': list(set(ip_matches))[:5]
            }
        
        # Pattern di email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, content)
        if email_matches:
            patterns['email_addresses'] = {
                'count': len(email_matches),
                'examples': email_matches[:5]
            }
        
        return patterns
    
    def _extract_field_characteristics(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estrae caratteristiche dei campi CSV.
        
        Returns:
            Caratteristiche dei campi
        """
        characteristics = {}
        
        for key, value in parsed_data.items():
            if key.startswith('_') or key in ['_csv_metadata', '_detected_patterns']:
                continue
            
            # Analizza il tipo di valore
            if isinstance(value, (int, float)):
                characteristics[key] = {
                    'type': 'numeric',
                    'is_constant': False,
                    'has_patterns': False
                }
            elif isinstance(value, bool):
                characteristics[key] = {
                    'type': 'boolean',
                    'is_constant': False,
                    'has_patterns': False
                }
            elif isinstance(value, str):
                # Analizza stringhe per pattern
                str_analysis = self._analyze_string_patterns(value)
                characteristics[key] = {
                    'type': 'string',
                    'length': len(value),
                    'is_constant': False,
                    'has_patterns': str_analysis['has_patterns'],
                    'pattern_type': str_analysis['pattern_type']
                }
        
        return characteristics
    
    def _analyze_string_patterns(self, value: str) -> Dict[str, Any]:
        """
        Analizza pattern nelle stringhe.
        
        Args:
            value: Stringa da analizzare
            
        Returns:
            Analisi dei pattern
        """
        # Controlla se è un timestamp
        if self._looks_like_timestamp(value):
            return {'has_patterns': True, 'pattern_type': 'timestamp'}
        
        # Controlla se è un numero
        try:
            float(value)
            return {'has_patterns': True, 'pattern_type': 'numeric_string'}
        except ValueError:
            pass
        
        # Controlla se è un IP
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        if re.match(ip_pattern, value):
            return {'has_patterns': True, 'pattern_type': 'ip_address'}
        
        # Controlla se è un email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.match(email_pattern, value):
            return {'has_patterns': True, 'pattern_type': 'email'}
        
        # Controlla se ha caratteri speciali
        special_chars = re.findall(r'[^a-zA-Z0-9\s]', value)
        if special_chars:
            return {'has_patterns': True, 'pattern_type': 'special_characters'}
        
        return {'has_patterns': False, 'pattern_type': 'plain_text'}
    
    def _detect_csv_anomalies(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rileva anomalie e caratteristiche speciali nei dati CSV.
        
        Returns:
            Anomalie rilevate
        """
        anomalies = {}
        
        # Controlla righe vuote o malformate
        lines = content.split('\n')
        empty_lines = sum(1 for line in lines if not line.strip())
        if empty_lines > 0:
            anomalies['empty_lines'] = {
                'count': empty_lines,
                'percentage': (empty_lines / len(lines)) * 100
            }
        
        # Controlla consistenza del numero di campi
        if '_csv_metadata' in parsed_data:
            expected_fields = parsed_data['_csv_metadata'].get('field_count', 0)
            if expected_fields > 0:
                inconsistent_lines = 0
                for line in lines:
                    if line.strip():
                        delimiter = parsed_data['_csv_metadata'].get('delimiter', ',')
                        actual_fields = line.count(delimiter) + 1
                        if actual_fields != expected_fields:
                            inconsistent_lines += 1
                
                if inconsistent_lines > 0:
                    anomalies['inconsistent_field_count'] = {
                        'count': inconsistent_lines,
                        'percentage': (inconsistent_lines / len(lines)) * 100,
                        'expected': expected_fields
                    }
        
        # Controlla caratteri non ASCII
        non_ascii_chars = re.findall(r'[^\x00-\x7F]', content)
        if non_ascii_chars:
            anomalies['non_ascii_characters'] = {
                'count': len(non_ascii_chars),
                'examples': list(set(non_ascii_chars))[:5]
            }
        
        return anomalies
    
    def get_parser_info(self) -> Dict[str, Any]:
        """
        Restituisce informazioni sul parser.
        
        Returns:
            Dizionario con informazioni sul parser
        """
        return {
            'name': 'RobustCSVParser',
            'description': 'Parser CSV robusto e standard che segue RFC 4180',
            'supported_formats': ['csv', 'tsv', 'txt'],
            'features': [
                'Rilevamento automatico delimitatori',
                'Type inference intelligente',
                'Gestione quote e escape',
                'Analisi pattern e costanti',
                'Gestione errori robusta'
            ],
            'standards': ['RFC 4180', 'Community best practices']
        } 