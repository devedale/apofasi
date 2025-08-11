"""
Timestamp normalization service domain service.

Questo servizio si occupa di normalizzare i timestamp estratti dai log
seguendo una gerarchia di attendibilità e formati standard.

WHY: Servizio specializzato per garantire che ogni record abbia un timestamp
normalizzato per correlazione temporale, seguendo i pattern architetturali
del dominio.
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ..entities.parsed_record import ParsedRecord
from ..entities.log_entry import LogEntry
from ..interfaces.centralized_regex_service import CentralizedRegexService


@dataclass
class TimestampInfo:
    """Informazioni su un timestamp normalizzato."""
    
    timestamp: datetime
    confidence: float  # 0.0 - 1.0
    source: str  # 'explicit', 'pattern_inference', 'file_modified', 'processing_time'
    normalized: bool
    timezone: str = "UTC"
    original_value: Optional[str] = None
    
    def to_isoformat(self) -> str:
        """Converte il timestamp in formato ISO."""
        if self.timestamp is None:
            return None
        return self.timestamp.isoformat()


class TimestampNormalizationService:
    """
    Servizio di dominio per normalizzazione temporale.
    
    WHY: Centralizza la logica di normalizzazione temporale
    seguendo i pattern architetturali del dominio.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, 
                 centralized_regex_service: Optional[CentralizedRegexService] = None):
        """Inizializza il servizio di normalizzazione temporale.

        Args:
            config: configurazione globale. Usa `timestamp_normalization.allow_content_scan` (default: False).
            centralized_regex_service: servizio regex centralizzato per configurazione
        """
        self._config = config or {}
        self._centralized_regex_service = centralized_regex_service
        
        # WHY: Usa il servizio centralizzato se disponibile, altrimenti fallback alla configurazione locale
        if self._centralized_regex_service:
            timestamp_config = self._centralized_regex_service.get_timestamp_normalization_config()
            tn_cfg = timestamp_config
        else:
            tn_cfg = self._config.get('timestamp_normalization', {})
        
        # Policy M7: content scan disabilitato di default; permesso solo se esplicitamente abilitato
        self.allow_content_scan: bool = bool(tn_cfg.get('allow_content_scan', False))
        
        # WHY: Carica i pattern dalla configurazione centralizzata se disponibili
        if self._centralized_regex_service:
            # Usa i pattern dalla configurazione centralizzata
            self.timestamp_patterns = self._load_timestamp_patterns_from_config()
        else:
            # Pattern per riconoscimento timestamp (ordinati per specificità) - fallback
            self.timestamp_patterns = [
                # ISO 8601 completo
                (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', 0.95),
                # ISO 8601 senza timezone
                (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?', 0.9),
                # Formato standard con spazio
                (r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?', 0.85),
                # Formato syslog RFC3164
                (r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?', 0.8),
                # Formato loghub
                (r'\d{8}-\d{2}:\d{2}:\d{2}:\d{3}', 0.75),
                # Solo data
                (r'\d{4}-\d{2}-\d{2}', 0.6),
                # Solo ora
                (r'\d{2}:\d{2}:\d{2}(?:\.\d+)?', 0.5),
            ]
        
        # Formati di parsing supportati
        self.datetime_formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%b %d %H:%M:%S',
            '%b %d %H:%M:%S.%f',
            '%Y%m%d-%H:%M:%S:%f',
            '%Y-%m-%d',
            '%H:%M:%S',
            '%H:%M:%S.%f',
        ]
    
    def _load_timestamp_patterns_from_config(self) -> List[Tuple[str, float]]:
        """Carica i pattern timestamp dalla configurazione centralizzata."""
        try:
            timestamp_config = self._centralized_regex_service.get_timestamp_normalization_config()
            patterns = timestamp_config.get('patterns', [])
            
            # Converte i pattern dalla configurazione nel formato atteso
            timestamp_patterns = []
            for pattern_info in patterns:
                if isinstance(pattern_info, dict):
                    pattern = pattern_info.get('pattern', '')
                    replacement = pattern_info.get('replacement', '')
                    # Usa una confidence di default per i pattern configurati
                    confidence = 0.8
                    if pattern:
                        timestamp_patterns.append((pattern, confidence))
            
            # Aggiunge pattern di fallback se nessuno è configurato
            if not timestamp_patterns:
                timestamp_patterns = [
                    (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', 0.95),
                    (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?', 0.9),
                    (r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?', 0.85),
                ]
            
            return timestamp_patterns
            
        except Exception as e:
            print(f"⚠️ Errore nel caricamento pattern timestamp: {e}")
            # Fallback ai pattern di default
            return [
                (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', 0.95),
                (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?', 0.9),
                (r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?', 0.85),
            ]
    
    def normalize_parsed_record(self, record) -> ParsedRecord:
        """
        Normalizza il timestamp di un ParsedRecord.
        
        WHY: Implementa la gerarchia di attendibilità per l'estrazione
        del timestamp più accurato disponibile.
        
        Args:
            record: Il record da normalizzare (ParsedRecord o dict)
            
        Returns:
            Record con timestamp normalizzato
        """
        timestamp_info = self._extract_timestamp_from_record(record)
        
        # Aggiorna il record con il timestamp normalizzato
        record.timestamp = timestamp_info.timestamp
        
        # NON aggiungere timestamp_info ai parsed_data per evitare confusione
        # Il timestamp del log dovrebbe essere estratto separatamente
        
        return record
    
    def normalize_dict_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizza il timestamp di un record dict.
        
        WHY: Gestisce record in formato dict mantenendo la tipizzazione.
        
        Args:
            record: Il record dict da normalizzare
            
        Returns:
            Record dict con timestamp normalizzato
        """
        timestamp_info = self._extract_timestamp_from_record(record)
        
        # Aggiungi informazioni di normalizzazione
        record["timestamp"] = timestamp_info.timestamp
        record["normalized_timestamp"] = timestamp_info.to_isoformat()
        record["timestamp_confidence"] = timestamp_info.confidence
        record["timestamp_source"] = timestamp_info.source
        record["timestamp_timezone"] = timestamp_info.timezone
        record["timestamp_original_value"] = timestamp_info.original_value
        
        return record
    
    def normalize_log_entry(self, log_entry: LogEntry) -> LogEntry:
        """
        Normalizza il timestamp di un LogEntry.
        
        Args:
            log_entry: Il log entry da normalizzare
            
        Returns:
            LogEntry con timestamp normalizzato
        """
        timestamp_info = self._extract_timestamp_from_content(log_entry.content)
        
        # Crea nuovo LogEntry con timestamp normalizzato
        return LogEntry(
            content=log_entry.content,
            source_file=log_entry.source_file,
            line_number=log_entry.line_number,
            timestamp=timestamp_info.timestamp,
            raw_data=log_entry.raw_data
        )
    
    def _extract_timestamp_from_record(self, record) -> TimestampInfo:
        """
        Estrae e normalizza il timestamp da un ParsedRecord o dict.
        
        WHY: Implementa la gerarchia di attendibilità per l'estrazione
        del timestamp più accurato disponibile.
        """
        # Gestisce sia ParsedRecord che dict
        if hasattr(record, 'timestamp') and record.timestamp:
            return TimestampInfo(
                timestamp=record.timestamp,
                confidence=0.9,
                source="explicit",
                normalized=True,
                original_value=record.timestamp.isoformat()
            )
        
        # 2. Prova estrazione dai dati parsati
        if hasattr(record, 'parsed_data'):
            parsed_data = record.parsed_data
        elif isinstance(record, dict):
            parsed_data = record
        else:
            parsed_data = {}
            
        if isinstance(parsed_data, dict):
            # Cerca campi timestamp comuni (escludendo parsed_at che è il timestamp di processing)
            timestamp_fields = ["timestamp", "time", "date", "datetime", "created_at", "event_time", "log_time", "event_timestamp"]
            excluded_fields = ["parsed_at", "processing_time", "parse_time"]  # Campi da escludere
            
            for field in timestamp_fields:
                if field in parsed_data and field not in excluded_fields:
                    value = parsed_data[field]
                    if value:
                        timestamp_info = self._parse_timestamp_value(str(value))
                        if timestamp_info:
                            return timestamp_info

            # 2.b Heuristica su detected_patterns → unix_timestamp
            detected = parsed_data.get('detected_patterns') if isinstance(parsed_data.get('detected_patterns'), dict) else None
            if detected and 'unix_timestamp' in detected:
                candidates = detected['unix_timestamp']
                if not isinstance(candidates, list):
                    candidates = [candidates]
                best_ts = self._select_best_unix_candidate(candidates, parsed_data)
                if best_ts:
                    return best_ts
        
        # 3. Prova estrazione dal contenuto originale SOLO se:
        #    - non ci sono dati parsati (fallback consentito), oppure
        #    - è abilitato allow_content_scan esplicito
        parsed_data_is_empty = not isinstance(parsed_data, dict) or len(parsed_data) == 0
        if parsed_data_is_empty or self.allow_content_scan:
            if hasattr(record, 'original_content'):
                content = record.original_content
            elif isinstance(record, dict) and 'raw_line' in record:
                content = record['raw_line']
            else:
                content = ""
            
            timestamp_info = self._extract_timestamp_from_content(content)
            if timestamp_info.confidence > 0.5:
                return timestamp_info
        
        # 4. Nessun timestamp trovato - non usare processing_time
        return TimestampInfo(
            timestamp=None,  # Nessun timestamp invece di processing_time
            confidence=0.0,
            source="none",
            normalized=False,
            original_value=None
        )
    
    def _extract_timestamp_from_content(self, content: str) -> TimestampInfo:
        """
        Estrae timestamp dal contenuto usando pattern recognition.
        
        Args:
            content: Contenuto del log
            
        Returns:
            TimestampInfo con il timestamp più accurato trovato
        """
        best_match = None
        best_confidence = 0.0
        
        # Prova tutti i pattern in ordine di specificità
        for pattern, confidence in self.timestamp_patterns:
            match = re.search(pattern, content)
            if match and confidence > best_confidence:
                timestamp_str = match.group(0)
                parsed_timestamp = self._parse_timestamp_string(timestamp_str)
                if parsed_timestamp:
                    best_match = TimestampInfo(
                        timestamp=parsed_timestamp,
                        confidence=confidence,
                        source="pattern_inference",
                        normalized=True,
                        original_value=timestamp_str
                    )
                    best_confidence = confidence
        
        if best_match and best_match.timestamp and self._is_valid_timestamp(best_match.timestamp):
            return best_match
        
        # Nessun timestamp valido trovato
        return TimestampInfo(
            timestamp=None,  # Nessun timestamp invece di processing_time
            confidence=0.0,
            source="none",
            normalized=False,
            original_value=None
        )
    
    def _parse_timestamp_value(self, value: str) -> Optional[TimestampInfo]:
        """
        Parsa un valore di timestamp specifico.
        
        Args:
            value: Valore del timestamp
            
        Returns:
            TimestampInfo se parsato con successo
        """
        parsed_timestamp = self._parse_timestamp_string(value)
        if parsed_timestamp and self._is_valid_timestamp(parsed_timestamp):
            return TimestampInfo(
                timestamp=parsed_timestamp,
                confidence=0.85,
                source="explicit",
                normalized=True,
                original_value=value
            )
        return None

    def _parse_unix_candidate(self, value: Any) -> Optional[TimestampInfo]:
        """Prova a interpretare un candidato come Unix timestamp (sec/ms)."""
        try:
            s = str(value).strip()
            # Filtra valori non numerici
            if not s or not all(ch.isdigit() for ch in s):
                return None
            iv = int(s)
            # ms vs sec: 13+ cifre → ms
            if len(s) >= 13:
                dt = datetime.fromtimestamp(iv / 1000, tz=timezone.utc)
            else:
                dt = datetime.fromtimestamp(iv, tz=timezone.utc)
            if self._is_valid_timestamp(dt):
                return TimestampInfo(
                    timestamp=dt,
                    confidence=0.7,
                    source="detected_patterns",
                    normalized=True,
                    original_value=s
                )
        except Exception:
            return None
        return None

    def _select_best_unix_candidate(self, candidates: List[Any], parsed_data: Dict[str, Any]) -> Optional[TimestampInfo]:
        """Seleziona il miglior Unix timestamp tra i candidati rilevati.
        Criteri:
        - preferisci valori plausibili (>= 2000-01-01, <= now+10y)
        - se ci sono più candidati validi, prendi quello con più cifre (ms > sec)
        - se presenti campi date/time espliciti in parsed_data, scoraggia candidati in conflitto grossolano
        """
        valid: List[Tuple[str, TimestampInfo]] = []
        for raw in candidates:
            ts_info = self._parse_unix_candidate(raw)
            if ts_info and self._is_valid_timestamp(ts_info.timestamp):
                valid.append((str(raw), ts_info))
        if not valid:
            return None
        # euristica: ordina per lunghezza stringa desc (ms preferito), poi per valore
        valid.sort(key=lambda t: (len(t[0]), t[1].timestamp), reverse=True)
        best = valid[0][1]
        best.source = 'detected_patterns'
        return best
    
    def _parse_timestamp_string(self, timestamp_str: str) -> Optional[datetime]:
        """
        Parsa una stringa timestamp usando i formati supportati.
        
        Args:
            timestamp_str: Stringa del timestamp
            
        Returns:
            datetime se parsato con successo
        """
        # Prova tutti i formati supportati
        for fmt in self.datetime_formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                # Assumi UTC se non specificato
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                
                # Valida che il timestamp sia realistico
                if self._is_valid_timestamp(dt):
                    return dt
            except ValueError:
                continue
        
        return None
    
    def _is_valid_timestamp(self, dt: datetime) -> bool:
        """
        Valida se un timestamp è realistico.
        
        Args:
            dt: Timestamp da validare
            
        Returns:
            True se il timestamp è valido
        """
        # Escludi date troppo vecchie (prima del 1970)
        if dt.year < 1970:
            return False
        
        # Escludi date future (più di 10 anni nel futuro)
        current_year = datetime.now().year
        if dt.year > current_year + 10:
            return False
        
        # Escludi date con valori impossibili
        if dt.month < 1 or dt.month > 12:
            return False
        if dt.day < 1 or dt.day > 31:
            return False
        if dt.hour < 0 or dt.hour > 23:
            return False
        if dt.minute < 0 or dt.minute > 59:
            return False
        if dt.second < 0 or dt.second > 59:
            return False
        
        return True
    
    def sort_records_by_timestamp(self, records: List[ParsedRecord]) -> List[ParsedRecord]:
        """
        Ordina i record per timestamp normalizzato.
        
        WHY: Fornisce ordinamento temporale per analisi cronologica.
        
        Args:
            records: Lista di record da ordinare
            
        Returns:
            Lista ordinata per timestamp
        """
        # Normalizza tutti i record
        normalized_records = []
        for record in records:
            normalized_record = self.normalize_parsed_record(record)
            normalized_records.append(normalized_record)
        
        # Ordina per timestamp (record senza timestamp alla fine)
        return sorted(
            normalized_records,
            key=lambda r: (r.timestamp is None, r.timestamp or datetime.max.replace(tzinfo=timezone.utc))
        )
    
    def get_timeline_statistics(self, records: List[ParsedRecord]) -> Dict[str, any]:
        """
        Calcola statistiche sulla timeline dei record.
        
        Args:
            records: Lista di record
            
        Returns:
            Statistiche sulla timeline
        """
        if not records:
            return {
                "total_records": 0,
                "records_with_timestamp": 0,
                "timestamp_coverage": 0.0,
                "time_span": None,
                "average_confidence": 0.0
            }
        
        records_with_timestamp = 0
        total_confidence = 0.0
        timestamps = []
        
        for record in records:
            normalized_record = self.normalize_parsed_record(record)
            if normalized_record.timestamp:
                records_with_timestamp += 1
                timestamps.append(normalized_record.timestamp)
                
                # Calcola confidence media
                timestamp_info = normalized_record.parsed_data.get("timestamp_info", {})
                confidence = timestamp_info.get("confidence", 0.0)
                total_confidence += confidence
        
        # Calcola statistiche
        total_records = len(records)
        timestamp_coverage = records_with_timestamp / total_records if total_records > 0 else 0.0
        average_confidence = total_confidence / records_with_timestamp if records_with_timestamp > 0 else 0.0
        
        # Calcola time span
        time_span = None
        if timestamps:
            min_timestamp = min(timestamps)
            max_timestamp = max(timestamps)
            time_span = {
                "start": min_timestamp.isoformat(),
                "end": max_timestamp.isoformat(),
                "duration_seconds": (max_timestamp - min_timestamp).total_seconds()
            }
        
        return {
            "total_records": total_records,
            "records_with_timestamp": records_with_timestamp,
            "timestamp_coverage": timestamp_coverage,
            "time_span": time_span,
            "average_confidence": average_confidence
        } 