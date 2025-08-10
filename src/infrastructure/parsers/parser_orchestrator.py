"""
ParserOrchestrator - Punto di ingresso unificato per il parsing dei log.
Delega tutta la logica al MultiStrategyParser per un'architettura pulita e centralizzata.
"""
from typing import Dict, Any, Iterator, Optional
from pathlib import Path

from ...domain.interfaces.log_parser import LogParser
from ...domain.entities.parsed_record import ParsedRecord
from ...domain.entities.log_entry import LogEntry
from .multi_strategy_parser import MultiStrategyParser

class ParserOrchestrator(LogParser):
    """
    Orchestratore semplificato che agisce come punto di ingresso unico
    per il sistema di parsing, delegando tutto al MultiStrategyParser.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # L'unica responsabilità dell'orchestratore è istanziare il parser principale.
        self.parser = MultiStrategyParser(config)

    @property
    def name(self) -> str:
        return "ParserOrchestrator"

    @property
    def priority(self) -> int:
        return 1

    @property
    def supported_formats(self) -> list[str]:
        # I formati supportati sono quelli del parser sottostante.
        return self.parser.supported_formats

    def can_parse(self, content: str, filename: Optional[Path] = None) -> bool:
        # Delega la decisione al MultiStrategyParser.
        return self.parser.can_parse(content, filename)

    def parse(self, log_entry: "LogEntry") -> Iterator[ParsedRecord]:
        """
        Delega il parsing direttamente al MultiStrategyParser.
        """
        yield from self.parser.parse(log_entry)

    def parse_with_fallback(self, log_entry: "LogEntry") -> Iterator[ParsedRecord]:
        """
        Metodo richiesto dal LogProcessingService per compatibilità.
        Delega al MultiStrategyParser.
        """
        yield from self.parser.parse(log_entry)
