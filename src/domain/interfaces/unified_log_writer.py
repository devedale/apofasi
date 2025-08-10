"""Unified Log Writer Interface.

Contratto per writer di log unificati e dataset di training.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Protocol


class UnifiedLogWriter(Protocol):
    """Interfaccia per scrivere log unificati e dataset correlati.

    Methods:
        write_unified_files: Scrive i file JSON unificati e derivati, ritorna mappa nome->path
        write_training_logppt: Esporta dataset training compatibile con LogParser/LogPPT
    """

    def write_unified_files(self, records: List[Any], output_dir: Path) -> Dict[str, Path]:
        ...

    def write_training_logppt(self, records: List[Any], output_path: Path) -> Path:
        ...


