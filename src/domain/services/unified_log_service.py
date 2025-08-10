"""
Servizio per la generazione di strutture JSON unificate ed efficienti.

WHY: Crea una struttura standardizzata per tutti i log che sia:
- Ottimizzata per ricerca efficiente
- Preparata per migrazione su Redis
- Efficiente per analisi multiple
- Standardizzata per tutti i tipi di log
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from ..entities.parsed_record import ParsedRecord


@dataclass
class UnifiedLogRecord:
    """
    Record di log unificato ed efficiente.
    
    WHY: Struttura standardizzata per tutti i log che permette
    ricerca efficiente e analisi multiple da un unico database.
    
    Contract:
        - Input: ParsedRecord con dati normalizzati
        - Output: Record unificato con tutti i campi necessari
        - Side effects: Calcoli di indici e hash per ricerca
    """
    
    # Identificatori univoci
    id: str  # Hash univoco del record
    log_id: str  # ID specifico del log (se disponibile)
    
    # Metadati temporali (calcolati una volta sola)
    timestamp: datetime  # Timestamp normalizzato
    timestamp_iso: str  # ISO format per ricerca
    timestamp_unix: int  # Unix timestamp per ordinamento
    timestamp_confidence: float  # Confidenza del timestamp
    timestamp_source: str  # Fonte del timestamp
    
    # Metadati del file
    source_file: str  # File di origine
    line_number: int  # Numero di riga
    file_size: int  # Dimensione del file
    file_modified: datetime  # Data modifica file
    
    # Informazioni di parsing
    parser_type: str  # Tipo di parser utilizzato
    parsing_confidence: float  # Confidenza del parsing
    parsing_success: bool  # Successo del parsing
    
    # Contenuto originale
    original_content: str  # Contenuto originale
    original_length: int  # Lunghezza del contenuto
    
    # Dati parsati strutturati
    parsed_data: Dict[str, Any]  # Dati parsati
    
    # Campi estratti per ricerca efficiente
    extracted_fields: Dict[str, Any]  # Campi estratti per ricerca
    
    # Indicatori di sicurezza
    security_indicators: Dict[str, Any]  # Indicatori di sicurezza
    
    # Metadati di processing
    processed_at: datetime  # Quando è stato processato
    processing_time_ms: int  # Tempo di processing in ms
    
    # Hash per ricerca rapida
    content_hash: str  # Hash del contenuto
    structure_hash: str  # Hash della struttura
    
    # Indici per ricerca
    search_indices: Dict[str, Any]  # Indici per ricerca
    
    def __post_init__(self):
        """Calcola campi derivati dopo l'inizializzazione."""
        if not self.id:
            self.id = self._generate_id()
        
        if not self.timestamp_iso:
            self.timestamp_iso = self.timestamp.isoformat()
        
        if not self.timestamp_unix:
            self.timestamp_unix = int(self.timestamp.timestamp())
        
        if not self.content_hash:
            self.content_hash = self._hash_content()
        
        if not self.structure_hash:
            self.structure_hash = self._hash_structure()
    
    def _generate_id(self) -> str:
        """Genera ID univoco per il record."""
        content = f"{self.source_file}:{self.line_number}:{self.original_content}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _hash_content(self) -> str:
        """Genera hash del contenuto."""
        return hashlib.sha256(self.original_content.encode()).hexdigest()[:16]
    
    def _hash_structure(self) -> str:
        """Genera hash della struttura."""
        structure = f"{self.parser_type}:{len(self.parsed_data)}:{len(self.extracted_fields)}"
        return hashlib.sha256(structure.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte il record in dizionario."""
        return asdict(self)
    
    def to_redis_dict(self) -> Dict[str, Any]:
        """Converte per storage su Redis."""
        return {
            'id': self.id,
            'timestamp': self.timestamp_iso,
            'timestamp_unix': self.timestamp_unix,
            'source_file': self.source_file,
            'line_number': self.line_number,
            'parser_type': self.parser_type,
            'original_content': self.original_content,
            'parsed_data': self.parsed_data,
            'extracted_fields': self.extracted_fields,
            'security_indicators': self.security_indicators,
            'search_indices': self.search_indices
        }


class UnifiedLogService:
    """
    Servizio per la generazione di record di log unificati.
    
    WHY: Centralizza la creazione di strutture JSON efficienti
    per tutti i tipi di log, preparando per Redis e analisi.
    
    Contract:
        - Input: ParsedRecord normalizzato
        - Output: UnifiedLogRecord ottimizzato
        - Side effects: Calcoli di indici e hash
    """
    
    def __init__(self):
        """Inizializza il servizio."""
        self.security_patterns = self._load_security_patterns()
        self.field_extractors = self._load_field_extractors()
    
    def create_unified_record(self, parsed_record: ParsedRecord, 
                            processing_start: datetime = None) -> UnifiedLogRecord:
        """
        Crea un record unificato da un ParsedRecord.
        
        Args:
            parsed_record: Record parsato
            processing_start: Timestamp di inizio processing
            
        Returns:
            Record unificato ottimizzato
        """
        # Calcola timestamp di processing
        if not processing_start:
            processing_start = datetime.now(timezone.utc)
        
        processing_time = datetime.now(timezone.utc) - processing_start
        processing_time_ms = int(processing_time.total_seconds() * 1000)
        
        # Estrai campi per ricerca efficiente
        extracted_fields = self._extract_search_fields(parsed_record)
        
        # Calcola indicatori di sicurezza
        security_indicators = self._calculate_security_indicators(parsed_record)
        
        # Crea indici di ricerca
        search_indices = self._create_search_indices(parsed_record, extracted_fields)
        
        # Ottieni informazioni del file
        file_info = self._get_file_info(parsed_record.source_file)
        
        return UnifiedLogRecord(
            id="",  # Sarà generato automaticamente
            log_id=self._extract_log_id(parsed_record),
            timestamp=parsed_record.timestamp or datetime.now(timezone.utc),
            timestamp_iso="",  # Sarà generato automaticamente
            timestamp_unix=0,  # Sarà generato automaticamente
            timestamp_confidence=getattr(parsed_record, 'timestamp_confidence', 0.0),
            timestamp_source=getattr(parsed_record, 'timestamp_source', 'unknown'),
            source_file=str(parsed_record.source_file),
            line_number=parsed_record.line_number,
            file_size=file_info.get('size', 0),
            file_modified=file_info.get('modified', datetime.now(timezone.utc)),
            parser_type=parsed_record.parser_name,
            parsing_confidence=getattr(parsed_record, 'confidence_score', 0.0),
            parsing_success=True,
            original_content=parsed_record.original_content,
            original_length=len(parsed_record.original_content),
            parsed_data=parsed_record.parsed_data,
            extracted_fields=extracted_fields,
            security_indicators=security_indicators,
            processed_at=datetime.now(timezone.utc),
            processing_time_ms=processing_time_ms,
            content_hash="",  # Sarà generato automaticamente
            structure_hash="",  # Sarà generato automaticamente
            search_indices=search_indices
        )
    
    def _extract_search_fields(self, record: ParsedRecord) -> Dict[str, Any]:
        """Estrae campi per ricerca efficiente."""
        fields = {}
        
        # Estrai campi comuni
        for field_name, extractor in self.field_extractors.items():
            if hasattr(record, field_name):
                value = getattr(record, field_name)
                if value:
                    fields[field_name] = extractor(value)
        
        # Estrai da parsed_data
        if hasattr(record, 'parsed_data') and record.parsed_data:
            for key, value in record.parsed_data.items():
                if key in self.field_extractors:
                    fields[key] = self.field_extractors[key](value)
        
        return fields
    
    def _calculate_security_indicators(self, record: ParsedRecord) -> Dict[str, Any]:
        """Calcola indicatori di sicurezza."""
        indicators = {
            'has_ip': False,
            'has_mac': False,
            'has_credentials': False,
            'has_errors': False,
            'has_warnings': False,
            'severity_level': 'info',
            'threat_indicators': []
        }
        
        content = record.original_content.lower()
        
        # Cerca indicatori di sicurezza
        for pattern_name, pattern_info in self.security_patterns.items():
            if pattern_info['pattern'].search(content):
                indicators['threat_indicators'].append(pattern_name)
        
        # Determina severità
        if any(indicator in indicators['threat_indicators'] 
               for indicator in ['error', 'critical', 'fatal']):
            indicators['severity_level'] = 'error'
        elif any(indicator in indicators['threat_indicators'] 
                for indicator in ['warning', 'alert']):
            indicators['severity_level'] = 'warning'
        
        return indicators
    
    def _create_search_indices(self, record: ParsedRecord, 
                             extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Crea indici per ricerca efficiente."""
        indices = {
            'by_timestamp': {
                'year': record.timestamp.year if record.timestamp else None,
                'month': record.timestamp.month if record.timestamp else None,
                'day': record.timestamp.day if record.timestamp else None,
                'hour': record.timestamp.hour if record.timestamp else None
            },
            'by_parser': record.parser_name,
            'by_source': str(record.source_file),
            'by_severity': 'info',  # Sarà aggiornato da security_indicators
            'by_length': len(record.original_content),
            'by_confidence': getattr(record, 'confidence_score', 0.0)
        }
        
        return indices
    
    def _extract_log_id(self, record: ParsedRecord) -> str:
        """Estrae ID del log se disponibile."""
        if hasattr(record, 'parsed_data') and record.parsed_data:
            # Cerca campi comuni per ID
            for field in ['logid', 'id', 'sequence', 'event_id']:
                if field in record.parsed_data:
                    return str(record.parsed_data[field])
        
        return ""
    
    def _get_file_info(self, source_file: Path) -> Dict[str, Any]:
        """Ottiene informazioni del file."""
        try:
            stat = source_file.stat()
            return {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            }
        except:
            return {'size': 0, 'modified': datetime.now(timezone.utc)}
    
    def _load_security_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Carica pattern di sicurezza centralizzati dal RegexService."""
        from ...core.services.regex_service import RegexService
        regex_service = RegexService()
        security_patterns: Dict[str, Dict[str, Any]] = {}
        # Converte i pattern di categoria 'security' in compiled regex
        for name, cfg in regex_service.get_patterns_by_category('security').items():
            compiled = regex_service.get_compiled_pattern(name)
            if compiled is None:
                continue
            # Normalizza chiave senza prefisso categoria
            key = name.replace('security_', '')
            security_patterns[key] = {
                'pattern': compiled,
                'severity': cfg.get('severity', 'info')
            }
        return security_patterns
    
    def _load_field_extractors(self) -> Dict[str, callable]:
        """Carica estrattori di campi."""
        return {
            'ip_address': lambda x: str(x) if x else None,
            'mac_address': lambda x: str(x) if x else None,
            'user_id': lambda x: str(x) if x else None,
            'session_id': lambda x: str(x) if x else None,
            'device_id': lambda x: str(x) if x else None,
            'hostname': lambda x: str(x) if x else None,
            'port': lambda x: int(x) if x and str(x).isdigit() else None,
            'status_code': lambda x: int(x) if x and str(x).isdigit() else None
        }
    
    def create_unified_collection(self, records: List[ParsedRecord]) -> List[UnifiedLogRecord]:
        """
        Crea una collezione di record unificati.
        
        Args:
            records: Lista di record parsati
            
        Returns:
            Lista di record unificati
        """
        processing_start = datetime.now(timezone.utc)
        unified_records = []
        
        for record in records:
            unified_record = self.create_unified_record(record, processing_start)
            unified_records.append(unified_record)
        
        return unified_records 