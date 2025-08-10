"""
Core Validators - Validatori centralizzati per l'applicazione

Questo modulo fornisce validatori per diversi aspetti dell'applicazione,
inclusi configurazione, dati, file e schemi. I validatori garantiscono
l'integrità dei dati e la conformità ai requisiti del sistema.

DESIGN:
- Validatori modulari e riutilizzabili
- Supporto per validazione asincrona
- Integrazione con il sistema di errori
- Validazione progressiva per performance

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import re
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime

from .exceptions import ValidationError, ConfigurationError
from .constants import (
    MAX_FILE_SIZE, MAX_LINE_LENGTH, SUPPORTED_FORMATS,
    SENSITIVE_FIELDS, SENSITIVE_PATTERNS
)
from .enums import LogFormat, ValidationLevel


class ConfigValidator:
    """
    Validatore per configurazioni dell'applicazione.
    
    WHY: Validatore dedicato per garantire che le configurazioni
    siano corrette e complete prima dell'utilizzo.
    """
    
    def __init__(self, strict_mode: bool = True):
        """
        Inizializza il validatore di configurazione.
        
        Args:
            strict_mode: Se True, solleva eccezioni per errori
                        Se False, restituisce warning
        """
        self.strict_mode = strict_mode
        self.errors = []
        self.warnings = []
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Valida una configurazione completa.
        
        WHY: Validazione completa per garantire che tutte le
        sezioni della configurazione siano corrette.
        
        Args:
            config: Dizionario di configurazione
            
        Returns:
            True se la configurazione è valida
            
        Raises:
            ConfigurationError: Se la configurazione non è valida
        """
        self.errors.clear()
        self.warnings.clear()
        
        # Validazione sezioni obbligatorie
        required_sections = ['parsing', 'output', 'anonymization']
        for section in required_sections:
            if section not in config:
                self._add_error(f"Sezione obbligatoria '{section}' mancante")
        
        # Validazione sezioni specifiche
        if 'parsing' in config:
            self._validate_parsing_config(config['parsing'])
        
        if 'output' in config:
            self._validate_output_config(config['output'])
        
        if 'anonymization' in config:
            self._validate_anonymization_config(config['anonymization'])
        
        # Controlla se ci sono errori critici
        if self.errors and self.strict_mode:
            raise ConfigurationError(
                f"Configurazione non valida: {len(self.errors)} errori trovati",
                context={'errors': self.errors, 'warnings': self.warnings}
            )
        
        return len(self.errors) == 0
    
    def _validate_parsing_config(self, parsing_config: Dict[str, Any]):
        """Valida la sezione parsing della configurazione."""
        if not isinstance(parsing_config, dict):
            self._add_error("Sezione 'parsing' deve essere un dizionario")
            return
        
        # Validazione formati supportati
        if 'supported_formats' in parsing_config:
            formats = parsing_config['supported_formats']
            if not isinstance(formats, list):
                self._add_error("'supported_formats' deve essere una lista")
            else:
                for fmt in formats:
                    if fmt not in SUPPORTED_FORMATS:
                        self._add_warning(f"Formato '{fmt}' non supportato ufficialmente")
        
        # Validazione timeout
        if 'timeout' in parsing_config:
            timeout = parsing_config['timeout']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                self._add_error("'timeout' deve essere un numero positivo")
        
        # Validazione encoding
        if 'encoding' in parsing_config:
            encoding = parsing_config['encoding']
            if not isinstance(encoding, str):
                self._add_error("'encoding' deve essere una stringa")
    
    def _validate_output_config(self, output_config: Dict[str, Any]):
        """Valida la sezione output della configurazione."""
        if not isinstance(output_config, dict):
            self._add_error("Sezione 'output' deve essere un dizionario")
            return
        
        # Validazione formato output
        if 'format' in output_config:
            format_type = output_config['format']
            if format_type not in ['json', 'csv', 'xml', 'yaml']:
                self._add_error(f"Formato output '{format_type}' non supportato")
        
        # Validazione compressione
        if 'compression' in output_config:
            compression = output_config['compression']
            if compression not in ['none', 'gzip', 'bzip2']:
                self._add_error(f"Compressione '{compression}' non supportata")
    
    def _validate_anonymization_config(self, anonymization_config: Dict[str, Any]):
        """Valida la sezione anonimizzazione della configurazione."""
        if not isinstance(anonymization_config, dict):
            self._add_error("Sezione 'anonymization' deve essere un dizionario")
            return
        
        # Validazione metodi
        if 'methods' in anonymization_config:
            methods = anonymization_config['methods']
            if not isinstance(methods, list):
                self._add_error("'methods' deve essere una lista")
            else:
                for method in methods:
                    if method not in ['hash', 'mask', 'replace', 'delete']:
                        self._add_error(f"Metodo anonimizzazione '{method}' non supportato")
    
    def _add_error(self, message: str):
        """Aggiunge un errore di validazione."""
        self.errors.append(message)
    
    def _add_warning(self, message: str):
        """Aggiunge un warning di validazione."""
        self.warnings.append(message)


class DataValidator:
    """
    Validatore per dati e record dell'applicazione.
    
    WHY: Validatore per garantire l'integrità dei dati
    durante il processing e l'output.
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.BASIC):
        """
        Inizializza il validatore di dati.
        
        Args:
            validation_level: Livello di validazione da applicare
        """
        self.validation_level = validation_level
        self.errors = []
        self.warnings = []
    
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """
        Valida un singolo record di dati.
        
        WHY: Validazione per garantire che ogni record
        sia strutturalmente corretto e completo.
        
        Args:
            record: Record da validare
            
        Returns:
            True se il record è valido
        """
        self.errors.clear()
        self.warnings.clear()
        
        if not isinstance(record, dict):
            self._add_error("Record deve essere un dizionario")
            return False
        
        # Validazione campi obbligatori
        required_fields = ['parser_type', 'parsed_at']
        for field in required_fields:
            if field not in record:
                self._add_error(f"Campo obbligatorio '{field}' mancante")
        
        # Validazione tipi di dati
        for key, value in record.items():
            self._validate_field(key, value)
        
        # Validazione aggiuntiva per livelli superiori
        if self.validation_level in [ValidationLevel.STRICT, ValidationLevel.COMPLIANCE]:
            self._validate_strict(record)
        
        return len(self.errors) == 0
    
    def validate_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Valida un batch di record.
        
        WHY: Validazione efficiente per grandi volumi di dati
        con reporting aggregato dei problemi.
        
        Args:
            records: Lista di record da validare
            
        Returns:
            Dizionario con statistiche di validazione
        """
        total_records = len(records)
        valid_records = 0
        invalid_records = 0
        all_errors = []
        all_warnings = []
        
        for i, record in enumerate(records):
            if self.validate_record(record):
                valid_records += 1
            else:
                invalid_records += 1
                all_errors.extend(self.errors)
                all_warnings.extend(self.warnings)
        
        return {
            'total_records': total_records,
            'valid_records': valid_records,
            'invalid_records': invalid_records,
            'error_rate': invalid_records / total_records if total_records > 0 else 0,
            'errors': all_errors,
            'warnings': all_warnings
        }
    
    def _validate_field(self, key: str, value: Any):
        """Valida un singolo campo."""
        # Validazione lunghezza stringhe
        if isinstance(value, str):
            if len(value) > MAX_LINE_LENGTH:
                self._add_error(f"Campo '{key}' troppo lungo ({len(value)} caratteri)")
        
        # Validazione campi sensibili
        if key.lower() in SENSITIVE_FIELDS:
            self._add_warning(f"Campo '{key}' contiene potenziali dati sensibili")
        
        # Validazione pattern sensibili
        if isinstance(value, str):
            for pattern_name, pattern in SENSITIVE_PATTERNS.items():
                if re.search(pattern, value):
                    self._add_warning(f"Campo '{key}' contiene pattern '{pattern_name}'")
    
    def _validate_strict(self, record: Dict[str, Any]):
        """Validazione rigorosa per livelli superiori."""
        # Validazione timestamp
        if 'parsed_at' in record:
            try:
                datetime.fromisoformat(record['parsed_at'].replace('Z', '+00:00'))
            except ValueError:
                self._add_error("Campo 'parsed_at' non è un timestamp ISO valido")
        
        # Validazione parser_type
        if 'parser_type' in record:
            parser_type = record['parser_type']
            if not isinstance(parser_type, str) or parser_type not in ['CEF', 'Syslog', 'JSON', 'CSV', 'Apache', 'Fortinet']:
                self._add_error(f"Parser type '{parser_type}' non valido")
    
    def _add_error(self, message: str):
        """Aggiunge un errore di validazione."""
        self.errors.append(message)
    
    def _add_warning(self, message: str):
        """Aggiunge un warning di validazione."""
        self.warnings.append(message)


class FileValidator:
    """
    Validatore per file e percorsi dell'applicazione.
    
    WHY: Validatore per garantire che i file siano accessibili
    e conformi ai requisiti del sistema.
    """
    
    def __init__(self, max_file_size: int = MAX_FILE_SIZE):
        """
        Inizializza il validatore di file.
        
        Args:
            max_file_size: Dimensione massima file in bytes
        """
        self.max_file_size = max_file_size
    
    def validate_file(self, file_path: Union[str, Path]) -> bool:
        """
        Valida un singolo file.
        
        WHY: Validazione per garantire che il file sia
        accessibile e processabile dal sistema.
        
        Args:
            file_path: Percorso del file da validare
            
        Returns:
            True se il file è valido
        """
        try:
            path = Path(file_path)
            
            # Controlla esistenza
            if not path.exists():
                raise ValidationError(f"File non trovato: {file_path}")
            
            # Controlla se è un file
            if not path.is_file():
                raise ValidationError(f"Percorso non è un file: {file_path}")
            
            # Controlla dimensione
            file_size = path.stat().st_size
            if file_size > self.max_file_size:
                raise ValidationError(
                    f"File troppo grande: {file_size} bytes (max: {self.max_file_size})",
                    context={'file_size': file_size, 'max_size': self.max_file_size}
                )
            
            # Controlla permessi di lettura
            if not path.stat().st_mode & 0o400:
                raise ValidationError(f"File non leggibile: {file_path}")
            
            return True
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Errore validazione file: {str(e)}")
    
    def validate_directory(self, dir_path: Union[str, Path]) -> List[Path]:
        """
        Valida una directory e restituisce i file validi.
        
        WHY: Validazione per processare directory intere
        e filtrare automaticamente file non validi.
        
        Args:
            dir_path: Percorso della directory da validare
            
        Returns:
            Lista di file validi nella directory
        """
        try:
            path = Path(dir_path)
            
            if not path.exists():
                raise ValidationError(f"Directory non trovata: {dir_path}")
            
            if not path.is_dir():
                raise ValidationError(f"Percorso non è una directory: {dir_path}")
            
            valid_files = []
            for file_path in path.iterdir():
                if file_path.is_file():
                    try:
                        if self.validate_file(file_path):
                            valid_files.append(file_path)
                    except ValidationError:
                        # Salta file non validi
                        continue
            
            return valid_files
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Errore validazione directory: {str(e)}")


class SchemaValidator:
    """
    Validatore per schemi di dati.
    
    WHY: Validatore per garantire che i dati conformino
    agli schemi definiti per diversi formati.
    """
    
    def __init__(self):
        """Inizializza il validatore di schemi."""
        self.schemas = {}
        self._load_default_schemas()
    
    def _load_default_schemas(self):
        """Carica gli schemi di default per i formati supportati."""
        # Schema CEF
        self.schemas['cef'] = {
            'type': 'object',
            'required': ['cef_version', 'device_vendor', 'device_product', 'name', 'severity'],
            'properties': {
                'cef_version': {'type': 'string'},
                'device_vendor': {'type': 'string'},
                'device_product': {'type': 'string'},
                'device_version': {'type': 'string'},
                'device_event_class_id': {'type': 'string'},
                'name': {'type': 'string'},
                'severity': {'type': 'string'}
            }
        }
        
        # Schema Syslog
        self.schemas['syslog'] = {
            'type': 'object',
            'required': ['timestamp', 'hostname', 'message'],
            'properties': {
                'priority': {'type': 'string'},
                'timestamp': {'type': 'string'},
                'hostname': {'type': 'string'},
                'tag': {'type': 'string'},
                'message': {'type': 'string'},
                'format': {'type': 'string'}
            }
        }
        
        # Schema JSON generico
        self.schemas['json'] = {
            'type': 'object',
            'properties': {
                'parser_type': {'type': 'string'},
                'parsed_at': {'type': 'string'},
                'line_number': {'type': 'integer'}
            }
        }
    
    def validate_against_schema(self, data: Dict[str, Any], schema_name: str) -> bool:
        """
        Valida dati contro uno schema specifico.
        
        WHY: Validazione per garantire che i dati conformino
        agli schemi definiti per diversi formati.
        
        Args:
            data: Dati da validare
            schema_name: Nome dello schema da utilizzare
            
        Returns:
            True se i dati sono validi secondo lo schema
        """
        if schema_name not in self.schemas:
            raise ValidationError(f"Schema '{schema_name}' non trovato")
        
        schema = self.schemas[schema_name]
        return self._validate_object(data, schema)
    
    def _validate_object(self, data: Any, schema: Dict[str, Any]) -> bool:
        """Valida un oggetto contro uno schema."""
        if not isinstance(data, dict):
            return False
        
        # Validazione campi obbligatori
        if 'required' in schema:
            for field in schema['required']:
                if field not in data:
                    return False
        
        # Validazione proprietà
        if 'properties' in schema:
            for field, field_schema in schema['properties'].items():
                if field in data:
                    if not self._validate_field(data[field], field_schema):
                        return False
        
        return True
    
    def _validate_field(self, value: Any, field_schema: Dict[str, Any]) -> bool:
        """Valida un singolo campo contro il suo schema."""
        expected_type = field_schema.get('type')
        
        if expected_type == 'string':
            return isinstance(value, str)
        elif expected_type == 'integer':
            return isinstance(value, int)
        elif expected_type == 'number':
            return isinstance(value, (int, float))
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        elif expected_type == 'object':
            return isinstance(value, dict)
        elif expected_type == 'array':
            return isinstance(value, list)
        
        return True 