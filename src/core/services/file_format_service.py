"""
Servizio per la gestione dei formati di file supportati e priorità dei parser.

DESIGN: Centralizza la configurazione dei formati supportati e fornisce
metodi per determinare il parser più appropriato per ogni tipo di file.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FileFormatService:
    """
    Servizio per la gestione dei formati di file supportati.
    
    Fornisce metodi per:
    - Identificare il formato di un file
    - Determinare la priorità del parser
    - Loggare informazioni sui formati supportati
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza il servizio con la configurazione.
        
        Args:
            config: Configurazione dell'applicazione
        """
        self._config = config
        self._file_formats_config = config.get("file_formats", {})
        self._verbose_logging = self._file_formats_config.get("verbose_parser_logging", True)
        
        # Configurazione dei formati supportati (struttura INI semplificata)
        self._supported_formats = self._build_supported_formats_dict()
        self._parser_priorities = self._build_priorities_dict()
        self._parser_mapping = self._build_parser_mapping_dict()
        
        # Log dei formati supportati all'inizializzazione
        self._log_supported_formats()
    
    def _build_supported_formats_dict(self) -> Dict[str, str]:
        """Costruisce il dizionario dei formati supportati dalla configurazione INI."""
        formats = {}
        for key, value in self._file_formats_config.items():
            if key.startswith('supported_'):
                format_name = key.replace('supported_', '')
                formats[format_name] = value
        return formats
    
    def _build_priorities_dict(self) -> Dict[str, int]:
        """Costruisce il dizionario delle priorità dalla configurazione INI."""
        priorities = {}
        for key, value in self._file_formats_config.items():
            if key.startswith('priority_'):
                format_name = key.replace('priority_', '')
                try:
                    priorities[format_name] = int(value)
                except (ValueError, TypeError):
                    priorities[format_name] = 999  # Priorità bassa per valori non validi
        return priorities
    
    def _build_parser_mapping_dict(self) -> Dict[str, str]:
        """Costruisce il dizionario del mapping dei parser dalla configurazione INI."""
        mapping = {}
        for key, value in self._file_formats_config.items():
            if key.startswith('parser_'):
                format_name = key.replace('parser_', '')
                mapping[format_name] = value
        return mapping
    
    def _log_supported_formats(self):
        """Logga i formati di file supportati in modo chiaro."""
        if not self._verbose_logging:
            return
            
        logger.info("📋 FORMATI DI FILE SUPPORTATI:")
        logger.info("=" * 50)
        
        for format_name, description in self._supported_formats.items():
            priority = self._parser_priorities.get(format_name, "N/A")
            parser = self._parser_mapping.get(format_name, "Default")
            logger.info(f"  • {format_name.upper():<10} | Priorità: {priority:<2} | Parser: {parser:<20} | {description}")
        
        logger.info("=" * 50)
        logger.info(f"✅ Totale formati supportati: {len(self._supported_formats)}")
    
    def get_file_format(self, file_path: Path) -> str:
        """
        Determina il formato di un file basandosi sull'estensione.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            Nome del formato identificato
        """
        extension = file_path.suffix.lower().lstrip('.')
        
        # Mappatura diretta delle estensioni
        if extension in self._supported_formats:
            if self._verbose_logging:
                logger.debug(f"🔍 File {file_path.name}: formato identificato '{extension}'")
            return extension
        
        # Fallback per estensioni comuni
        fallback_mapping = {
            'csv': 'csv',
            'json': 'json',
            'log': 'log',
            'txt': 'txt',
            'elog': 'elog'
        }
        
        if extension in fallback_mapping:
            fallback_format = fallback_mapping[extension]
            if self._verbose_logging:
                logger.debug(f"🔍 File {file_path.name}: formato fallback '{fallback_format}' (estensione: {extension})")
            return fallback_format
        
        # Formato generico per estensioni non riconosciute
        if self._verbose_logging:
            logger.debug(f"🔍 File {file_path.name}: formato generico 'log' (estensione non riconosciuta: {extension})")
        return 'log'
    
    def get_parser_priority(self, format_name: str) -> int:
        """
        Ottiene la priorità del parser per un formato specifico.
        
        Args:
            format_name: Nome del formato
            
        Returns:
            Priorità del parser (numeri più bassi = priorità più alta)
        """
        return self._parser_priorities.get(format_name, 999)  # Priorità bassa per formati non configurati
    
    def get_parser_for_format(self, format_name: str) -> str:
        """
        Ottiene il nome del parser raccomandato per un formato.
        
        Args:
            format_name: Nome del formato
            
        Returns:
            Nome del parser raccomandato
        """
        return self._parser_mapping.get(format_name, "MultiStrategyParser")
    
    def is_format_supported(self, format_name: str) -> bool:
        """
        Verifica se un formato è supportato.
        
        Args:
            format_name: Nome del formato
            
        Returns:
            True se il formato è supportato
        """
        return format_name in self._supported_formats
    
    def get_all_supported_formats(self) -> List[str]:
        """
        Ottiene la lista di tutti i formati supportati.
        
        Returns:
            Lista dei formati supportati
        """
        return list(self._supported_formats.keys())
    
    def get_format_description(self, format_name: str) -> str:
        """
        Ottiene la descrizione di un formato.
        
        Args:
            format_name: Nome del formato
            
        Returns:
            Descrizione del formato
        """
        return self._supported_formats.get(format_name, "Formato non riconosciuto")
    
    def log_file_processing_info(self, file_path: Path, parser_used: str, format_detected: str):
        """
        Logga informazioni dettagliate sul processing di un file.
        
        Args:
            file_path: Percorso del file processato
            parser_used: Nome del parser utilizzato
            format_detected: Formato rilevato
        """
        if not self._verbose_logging:
            return
            
        priority = self.get_parser_priority(format_detected)
        description = self.get_format_description(format_detected)
        
        logger.info(f"📄 PROCESSING FILE: {file_path.name}")
        logger.info(f"   ├─ Formato rilevato: {format_detected.upper()}")
        logger.info(f"   ├─ Descrizione: {description}")
        logger.info(f"   ├─ Priorità parser: {priority}")
        logger.info(f"   ├─ Parser utilizzato: {parser_used}")
        logger.info(f"   └─ Estensione: {file_path.suffix}")
    
    def get_formats_summary(self) -> Dict[str, Any]:
        """
        Ottiene un riepilogo completo dei formati supportati.
        
        Returns:
            Dizionario con informazioni sui formati
        """
        return {
            "total_formats": len(self._supported_formats),
            "supported_formats": self._supported_formats,
            "parser_priorities": self._parser_priorities,
            "parser_mapping": self._parser_mapping,
            "verbose_logging": self._verbose_logging
        }
