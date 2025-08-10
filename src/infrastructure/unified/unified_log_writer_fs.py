"""Filesystem Unified Log Writer implementation.

Scrive file JSON unificati, indici, statistiche e dataset di training.
"""

from __future__ import annotations

import json
import gzip
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

from ...domain.interfaces.unified_log_writer import UnifiedLogWriter
from ...domain.entities.parsed_record import ParsedRecord
from ...domain.services.unified_log_service import UnifiedLogService, UnifiedLogRecord
from ...domain.services.timestamp_normalization_service import TimestampNormalizationService


class UnifiedLogWriterFs(UnifiedLogWriter):
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.unified_service = UnifiedLogService()
        self.timestamp_service = TimestampNormalizationService()

    def write_unified_files(self, records: List[ParsedRecord], output_dir: Path | None = None) -> Dict[str, Path]:
        out_dir = output_dir or self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        normalized = [self.timestamp_service.normalize_parsed_record(r) for r in records]
        unified = self.unified_service.create_unified_collection(normalized)

        generated: Dict[str, Path] = {}
        generated['main'] = self._write_main(unified, out_dir)
        generated['redis'] = self._write_redis(unified, out_dir)
        generated['compressed'] = self._write_compressed(unified, out_dir)
        generated['indices'] = self._write_indices(unified, out_dir)
        generated['statistics'] = self._write_statistics(unified, out_dir)
        return generated

    def write_training_logppt(self, records: List[ParsedRecord], output_path: Path) -> Path:
        """Esporta dataset di training (id,message,event,eventtemplate)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('id\tmessage\tevent\teventtemplate\n')
            for rec in records:
                rid = f"{rec.source_file}:{rec.line_number}"
                message = (rec.original_content or '').replace('\t', ' ').replace('\n', ' ')
                event = str(getattr(rec, 'drain3_cluster_id', ''))
                eventtemplate = getattr(rec, 'drain3_template', '') or ''
                f.write(f"{rid}\t{message}\t{event}\t{eventtemplate}\n")
        return output_path

    # --- private writers ---
    def _write_main(self, records: List[UnifiedLogRecord], out_dir: Path) -> Path:
        path = out_dir / 'unified_logs.json'
        data = {
            'metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'total_records': len(records),
                'version': '1.0',
                'format': 'unified_log'
            },
            'records': [r.to_dict() for r in records]
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def _write_redis(self, records: List[UnifiedLogRecord], out_dir: Path) -> Path:
        path = out_dir / 'unified_logs_redis.json'
        data = {
            'metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'total_records': len(records),
                'version': '1.0',
                'format': 'redis_optimized'
            },
            'records': [r.to_redis_dict() for r in records]
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def _write_compressed(self, records: List[UnifiedLogRecord], out_dir: Path) -> Path:
        path = out_dir / 'unified_logs_compressed.json.gz'
        data = {
            'metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'total_records': len(records),
                'version': '1.0',
                'format': 'compressed'
            },
            'records': [r.to_dict() for r in records]
        }
        with gzip.open(path, 'wt', encoding='utf-8') as f:
            json.dump(data, f, default=str)
        return path

    def _write_indices(self, records: List[UnifiedLogRecord], out_dir: Path) -> Path:
        path = out_dir / 'unified_logs_indices.json'
        indices: Dict[str, Any] = {
            'by_parser': {},
            'by_source': {},
            'by_severity': {},
        }
        for r in records:
            indices['by_parser'].setdefault(r.parser_type, []).append(r.id)
            indices['by_source'].setdefault(r.source_file, []).append(r.id)
            sev = r.security_indicators.get('severity_level', 'info')
            indices['by_severity'].setdefault(sev, []).append(r.id)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'indices': indices}, f, indent=2)
        return path

    def _write_statistics(self, records: List[UnifiedLogRecord], out_dir: Path) -> Path:
        path = out_dir / 'unified_logs_statistics.json'
        lengths = [r.original_length for r in records]
        stats = {
            'total_records': len(records),
            'average_content_length': (sum(lengths) / len(lengths)) if lengths else 0,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'statistics': stats}, f, indent=2)
        return path


