"""
Generatore di file JSON unificati ed efficienti.

WHY: Crea file JSON ottimizzati per ricerca e analisi,
preparati per migrazione su Redis e con tutti i calcoli
fatti una volta sola.
"""

import json
import gzip
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from ...domain.services.unified_log_service import UnifiedLogService, UnifiedLogRecord
from ...domain.entities.parsed_record import ParsedRecord
from ...domain.services.timestamp_normalization_service import TimestampNormalizationService


class UnifiedLogGenerator:
    """
    Generatore di file JSON unificati.
    
    WHY: Centralizza la generazione di file JSON efficienti
    per tutti i tipi di log, con struttura ottimizzata per
    ricerca e analisi.
    
    Contract:
        - Input: Lista di ParsedRecord normalizzati
        - Output: File JSON unificati ottimizzati
        - Side effects: Calcoli di indici e statistiche
    """
    
    def __init__(self, output_dir: Path):
        """
        Inizializza il generatore.
        
        Args:
            output_dir: Directory di output
        """
        self.output_dir = output_dir
        self.unified_service = UnifiedLogService()
        self.timestamp_service = TimestampNormalizationService()
        
        # Assicurati che la directory esista
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_unified_files(self, parsed_records: List[ParsedRecord]) -> Dict[str, Path]:
        """
        Genera file JSON unificati.
        
        Args:
            parsed_records: Lista di record parsati
            
        Returns:
            Dizionario con percorsi dei file generati
        """
        print("🔄 Generando file JSON unificati...")
        
        # Normalizza timestamp
        normalized_records = []
        for record in parsed_records:
            normalized_record = self.timestamp_service.normalize_parsed_record(record)
            normalized_records.append(normalized_record)
        
        # Crea record unificati
        unified_records = self.unified_service.create_unified_collection(normalized_records)
        
        # Genera file
        generated_files = {}
        
        # File principale unificato
        main_file = self._generate_main_file(unified_records)
        generated_files['main'] = main_file
        
        # File per Redis
        redis_file = self._generate_redis_file(unified_records)
        generated_files['redis'] = redis_file
        
        # File compresso
        compressed_file = self._generate_compressed_file(unified_records)
        generated_files['compressed'] = compressed_file
        
        # File di indici
        indices_file = self._generate_indices_file(unified_records)
        generated_files['indices'] = indices_file
        
        # File di statistiche
        stats_file = self._generate_statistics_file(unified_records)
        generated_files['statistics'] = stats_file
        
        print(f"✅ File JSON unificati generati: {len(generated_files)} file")
        return generated_files
    
    def _generate_main_file(self, records: List[UnifiedLogRecord]) -> Path:
        """Genera file principale unificato."""
        file_path = self.output_dir / "unified_logs.json"
        
        data = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_records": len(records),
                "version": "1.0",
                "format": "unified_log"
            },
            "records": [record.to_dict() for record in records]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"  📄 File principale: {file_path}")
        return file_path
    
    def _generate_redis_file(self, records: List[UnifiedLogRecord]) -> Path:
        """Genera file ottimizzato per Redis."""
        file_path = self.output_dir / "unified_logs_redis.json"
        
        redis_data = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_records": len(records),
                "version": "1.0",
                "format": "redis_optimized"
            },
            "records": [record.to_redis_dict() for record in records]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(redis_data, f, indent=2, default=str)
        
        print(f"  🔄 File Redis: {file_path}")
        return file_path
    
    def _generate_compressed_file(self, records: List[UnifiedLogRecord]) -> Path:
        """Genera file compresso."""
        file_path = self.output_dir / "unified_logs_compressed.json.gz"
        
        data = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_records": len(records),
                "version": "1.0",
                "format": "compressed"
            },
            "records": [record.to_dict() for record in records]
        }
        
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump(data, f, default=str)
        
        print(f"  📦 File compresso: {file_path}")
        return file_path
    
    def _generate_indices_file(self, records: List[UnifiedLogRecord]) -> Path:
        """Genera file di indici per ricerca rapida."""
        file_path = self.output_dir / "unified_logs_indices.json"
        
        # Crea indici
        indices = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_records": len(records),
                "version": "1.0",
                "format": "search_indices"
            },
            "indices": {
                "by_timestamp": self._create_timestamp_index(records),
                "by_parser": self._create_parser_index(records),
                "by_source": self._create_source_index(records),
                "by_severity": self._create_severity_index(records),
                "by_confidence": self._create_confidence_index(records),
                "by_security": self._create_security_index(records)
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(indices, f, indent=2, default=str)
        
        print(f"  🔍 File indici: {file_path}")
        return file_path
    
    def _generate_statistics_file(self, records: List[UnifiedLogRecord]) -> Path:
        """Genera file di statistiche."""
        file_path = self.output_dir / "unified_logs_statistics.json"
        
        stats = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_records": len(records),
                "version": "1.0",
                "format": "statistics"
            },
            "statistics": {
                "temporal": self._calculate_temporal_stats(records),
                "parser": self._calculate_parser_stats(records),
                "security": self._calculate_security_stats(records),
                "performance": self._calculate_performance_stats(records),
                "content": self._calculate_content_stats(records)
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, default=str)
        
        print(f"  📊 File statistiche: {file_path}")
        return file_path
    
    def _create_timestamp_index(self, records: List[UnifiedLogRecord]) -> Dict[str, Any]:
        """Crea indice temporale."""
        index = {}
        
        for record in records:
            year = record.timestamp.year
            month = record.timestamp.month
            day = record.timestamp.day
            hour = record.timestamp.hour
            
            if year not in index:
                index[year] = {}
            if month not in index[year]:
                index[year][month] = {}
            if day not in index[year][month]:
                index[year][month][day] = {}
            if hour not in index[year][month][day]:
                index[year][month][day][hour] = []
            
            index[year][month][day][hour].append(record.id)
        
        return index
    
    def _create_parser_index(self, records: List[UnifiedLogRecord]) -> Dict[str, List[str]]:
        """Crea indice per parser."""
        index = {}
        
        for record in records:
            parser = record.parser_type
            if parser not in index:
                index[parser] = []
            index[parser].append(record.id)
        
        return index
    
    def _create_source_index(self, records: List[UnifiedLogRecord]) -> Dict[str, List[str]]:
        """Crea indice per file sorgente."""
        index = {}
        
        for record in records:
            source = record.source_file
            if source not in index:
                index[source] = []
            index[source].append(record.id)
        
        return index
    
    def _create_severity_index(self, records: List[UnifiedLogRecord]) -> Dict[str, List[str]]:
        """Crea indice per severità."""
        index = {}
        
        for record in records:
            severity = record.security_indicators.get('severity_level', 'info')
            if severity not in index:
                index[severity] = []
            index[severity].append(record.id)
        
        return index
    
    def _create_confidence_index(self, records: List[UnifiedLogRecord]) -> Dict[str, List[str]]:
        """Crea indice per confidenza."""
        index = {
            'high': [],    # > 0.8
            'medium': [],  # 0.5-0.8
            'low': []      # < 0.5
        }
        
        for record in records:
            confidence = record.parsing_confidence
            if confidence > 0.8:
                index['high'].append(record.id)
            elif confidence > 0.5:
                index['medium'].append(record.id)
            else:
                index['low'].append(record.id)
        
        return index
    
    def _create_security_index(self, records: List[UnifiedLogRecord]) -> Dict[str, List[str]]:
        """Crea indice per indicatori di sicurezza."""
        index = {}
        
        for record in records:
            for indicator in record.security_indicators.get('threat_indicators', []):
                if indicator not in index:
                    index[indicator] = []
                index[indicator].append(record.id)
        
        return index
    
    def _calculate_temporal_stats(self, records: List[UnifiedLogRecord]) -> Dict[str, Any]:
        """Calcola statistiche temporali."""
        if not records:
            return {}
        
        timestamps = [r.timestamp for r in records if r.timestamp]
        
        if not timestamps:
            return {}
        
        min_time = min(timestamps)
        max_time = max(timestamps)
        duration = max_time - min_time
        
        return {
            "total_records": len(records),
            "records_with_timestamp": len(timestamps),
            "timestamp_coverage": len(timestamps) / len(records),
            "time_span": {
                "start": min_time.isoformat(),
                "end": max_time.isoformat(),
                "duration_seconds": duration.total_seconds()
            },
            "average_confidence": sum(r.timestamp_confidence for r in records) / len(records)
        }
    
    def _calculate_parser_stats(self, records: List[UnifiedLogRecord]) -> Dict[str, Any]:
        """Calcola statistiche per parser."""
        parser_counts = {}
        parser_confidence = {}
        
        for record in records:
            parser = record.parser_type
            parser_counts[parser] = parser_counts.get(parser, 0) + 1
            
            if parser not in parser_confidence:
                parser_confidence[parser] = []
            parser_confidence[parser].append(record.parsing_confidence)
        
        return {
            "parser_distribution": parser_counts,
            "parser_confidence": {
                parser: sum(confidences) / len(confidences)
                for parser, confidences in parser_confidence.items()
            }
        }
    
    def _calculate_security_stats(self, records: List[UnifiedLogRecord]) -> Dict[str, Any]:
        """Calcola statistiche di sicurezza."""
        severity_counts = {}
        threat_counts = {}
        
        for record in records:
            severity = record.security_indicators.get('severity_level', 'info')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            for threat in record.security_indicators.get('threat_indicators', []):
                threat_counts[threat] = threat_counts.get(threat, 0) + 1
        
        return {
            "severity_distribution": severity_counts,
            "threat_indicators": threat_counts
        }
    
    def _calculate_performance_stats(self, records: List[UnifiedLogRecord]) -> Dict[str, Any]:
        """Calcola statistiche di performance."""
        processing_times = [r.processing_time_ms for r in records]
        
        return {
            "total_processing_time_ms": sum(processing_times),
            "average_processing_time_ms": sum(processing_times) / len(processing_times) if processing_times else 0,
            "max_processing_time_ms": max(processing_times) if processing_times else 0,
            "min_processing_time_ms": min(processing_times) if processing_times else 0
        }
    
    def _calculate_content_stats(self, records: List[UnifiedLogRecord]) -> Dict[str, Any]:
        """Calcola statistiche del contenuto."""
        lengths = [r.original_length for r in records]
        
        return {
            "total_content_length": sum(lengths),
            "average_content_length": sum(lengths) / len(lengths) if lengths else 0,
            "max_content_length": max(lengths) if lengths else 0,
            "min_content_length": min(lengths) if lengths else 0
        } 