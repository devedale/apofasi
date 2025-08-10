"""
Data Schema Management - Soluzione architetturale universale per parsing adattivo
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Set
from enum import Enum
import re
from datetime import datetime

from ..services.config_manager import ConfigManager


class FieldType(Enum):
    """Tipi di campo riconosciuti automaticamente"""
    TIMESTAMP = "timestamp"
    IP_ADDRESS = "ip_address"
    USER_ID = "user_id"
    MESSAGE = "message"
    LEVEL = "level"
    COMPONENT = "component"
    PROCESS_ID = "process_id"
    HOSTNAME = "hostname"
    PORT = "port"
    URL = "url"
    PATH = "path"
    EMAIL = "email"
    HASH = "hash"
    UNKNOWN = "unknown"


@dataclass
class FieldMapping:
    """Mappatura di un campo con il suo tipo e validazione"""
    name: str
    detected_type: FieldType
    confidence: float
    validation_pattern: Optional[str] = None
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


@dataclass
class DataSchema:
    """Schema dinamico per un dataset"""
    name: str
    fields: Dict[str, FieldMapping]
    total_records: int
    confidence_score: float
    format_type: str  # csv, json, syslog, etc.
    
    def get_field_names(self) -> List[str]:
        """Restituisce i nomi dei campi ordinati per confidenza"""
        return sorted(self.fields.keys(), 
                     key=lambda x: self.fields[x].confidence, 
                     reverse=True)
    
    def get_high_confidence_fields(self, threshold: float = 0.7) -> List[str]:
        """Restituisce i campi con alta confidenza"""
        return [name for name, field in self.fields.items() 
                if field.confidence >= threshold]


class SchemaDetector:
    """Rilevatore automatico di schemi di dati usando configurazione dinamica"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def detect_schema(self, data_samples: List[Dict[str, Any]], format_type: str) -> DataSchema:
        """Rileva automaticamente lo schema dai dati di esempio"""
        if not data_samples:
            return DataSchema(
                name="empty_schema",
                fields={},
                total_records=0,
                confidence_score=0.0,
                format_type=format_type
            )
        
        # Analizza ogni campo
        field_mappings = {}
        all_field_names = set()
        
        # Raccogli tutti i nomi dei campi
        for sample in data_samples:
            all_field_names.update(sample.keys())
        
        # Analizza ogni campo
        for field_name in all_field_names:
            field_mapping = self._analyze_field(field_name, data_samples)
            if field_mapping:
                field_mappings[field_name] = field_mapping
        
        # Calcola confidenza globale
        confidence_score = self._calculate_global_confidence(field_mappings)
        
        return DataSchema(
            name=f"auto_detected_{format_type}",
            fields=field_mappings,
            total_records=len(data_samples),
            confidence_score=confidence_score,
            format_type=format_type
        )
    
    def _analyze_field(self, field_name: str, samples: List[Dict[str, Any]]) -> Optional[FieldMapping]:
        """Analizza un campo specifico"""
        # Estrai valori per questo campo
        values = []
        for sample in samples:
            if field_name in sample:
                values.append(str(sample[field_name]))
        
        if not values:
            return None
        
        # Analizza nome del campo
        name_confidence, name_type = self.config_manager.get_field_type_by_name(field_name)
        
        # Analizza valori del campo
        value_confidence, value_type = self.config_manager.get_field_type_by_value(values)
        
        # Combina le analisi
        if name_confidence > value_confidence:
            detected_type = self._get_field_type_enum(name_type)
            confidence = name_confidence
        else:
            detected_type = self._get_field_type_enum(value_type)
            confidence = value_confidence
        
        return FieldMapping(
            name=field_name,
            detected_type=detected_type,
            confidence=confidence,
            examples=values[:3]  # Primi 3 esempi
        )
    
    def _get_field_type_enum(self, field_type_str: str) -> FieldType:
        """Converte stringa in enum FieldType"""
        try:
            return FieldType(field_type_str)
        except ValueError:
            return FieldType.UNKNOWN
    
    def _calculate_global_confidence(self, field_mappings: Dict[str, FieldMapping]) -> float:
        """Calcola la confidenza globale dello schema"""
        if not field_mappings:
            return 0.0
        
        total_confidence = sum(field.confidence for field in field_mappings.values())
        return total_confidence / len(field_mappings)


class AdaptiveParser:
    """Parser adattivo che si basa su schemi dinamici"""
    
    def __init__(self, schema_detector: SchemaDetector):
        self.schema_detector = schema_detector
        self.detected_schemas: Dict[str, DataSchema] = {}
    
    def parse_with_schema(self, data: Dict[str, Any], schema: DataSchema) -> Dict[str, Any]:
        """Parsa i dati usando uno schema specifico"""
        parsed_data = {}
        
        for field_name, field_mapping in schema.fields.items():
            if field_name in data:
                value = data[field_name]
                
                # Applica validazione e conversione basata sul tipo
                parsed_value = self._process_field_value(value, field_mapping)
                parsed_data[field_name] = parsed_value
        
        return parsed_data
    
    def _process_field_value(self, value: Any, field_mapping: FieldMapping) -> Any:
        """Processa un valore di campo basandosi sul suo tipo rilevato"""
        if value is None or value == '':
            return None
        
        value_str = str(value)
        
        # Applica conversione basata sul tipo
        if field_mapping.detected_type == FieldType.TIMESTAMP:
            return self._parse_timestamp(value_str)
        elif field_mapping.detected_type == FieldType.IP_ADDRESS:
            return value_str  # Mantieni IP per anonimizzazione
        elif field_mapping.detected_type == FieldType.PROCESS_ID:
            return self._parse_integer(value_str)
        elif field_mapping.detected_type == FieldType.PORT:
            return self._parse_integer(value_str)
        elif field_mapping.detected_type == FieldType.USER_ID:
            return value_str  # Mantieni per anonimizzazione
        else:
            return value_str
    
    def _parse_timestamp(self, value: str) -> Optional[str]:
        """Parsa timestamp in formato standard"""
        try:
            # Prova diversi formati
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%H:%M:%S',
                '%Y%m%d-%H:%M:%S:%f'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            return value  # Se non riesce a parsare, mantieni originale
        except:
            return value
    
    def _parse_integer(self, value: str) -> Optional[int]:
        """Parsa intero"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return None 