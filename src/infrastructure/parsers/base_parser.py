"""
Base Parser - Classe base per tutti i parser

Questo modulo fornisce la classe base astratta per tutti i parser del sistema.
Definisce l'interfaccia comune e le funzionalità di base come logging degli errori,
gestione delle modalità strict/lenient, e validazione del contenuto.

DESIGN:
- Pattern Template Method per standardizzare il comportamento dei parser
- Gestione centralizzata degli errori e warning
- Supporto per modalità strict (fail-fast) e lenient (continue-on-error)
- Logging strutturato per debugging e monitoring

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Iterator, Optional
from datetime import datetime


class ParseError(Exception):
    """
    Eccezione personalizzata per errori di parsing.
    
    WHY: Eccezione specifica per distinguere errori di parsing da altri errori
    e fornire informazioni contestuali come numero di riga e contenuto originale.
    
    Attributes:
        message: Messaggio descrittivo dell'errore
        line_number: Numero della riga che ha causato l'errore
        original_line: Contenuto originale della riga problematica
    """
    
    def __init__(self, message: str, line_number: int = None, original_line: str = None):
        self.message = message
        self.line_number = line_number
        self.original_line = original_line
        super().__init__(f"Line {line_number}: {message}" if line_number else message)


class BaseParser(ABC):
    """
    Classe base astratta per tutti i parser del sistema.
    
    Questa classe definisce il contratto comune per tutti i parser e fornisce
    funzionalità di base come logging degli errori, gestione delle modalità
    di parsing, e validazione del contenuto.
    
    Contract:
        - can_parse(): Determina se il parser può gestire il contenuto
        - parse(): Parsa il contenuto e restituisce record strutturati
        - log_error(): Registra errori di parsing
        - log_warning(): Registra warning non critici
    
    WHY: Utilizziamo una classe base per evitare duplicazione di codice
    e garantire comportamento consistente tra tutti i parser.
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Inizializza il parser base.
        
        Args:
            strict_mode: Se True, solleva eccezioni per errori di parsing
                        Se False, continua il parsing e logga gli errori
        """
        self.strict_mode = strict_mode
        self.errors = []
        self.warnings = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def can_parse(self, content: str, filename: str = None) -> bool:
        """
        Determina se questo parser può gestire il contenuto specificato.
        
        WHY: Metodo astratto per forzare ogni parser a implementare
        la propria logica di rilevamento del formato.
        
        Args:
            content: Contenuto da analizzare
            filename: Nome del file (opzionale, per logging)
            
        Returns:
            True se il parser può gestire il contenuto
        """
        pass
    
    @abstractmethod
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        """
        Parsa il contenuto e restituisce record strutturati.
        
        WHY: Metodo astratto per garantire che ogni parser implementi
        la propria logica di parsing specifica.
        
        Args:
            content: Contenuto da parsare
            filename: Nome del file (per logging)
            
        Yields:
            Dizionari con i dati parsati
        """
        pass
    
    def log_error(self, message: str, line_number: int = None, line_content: str = None):
        """
        Registra un errore di parsing.
        
        WHY: Gestione centralizzata degli errori per facilitare debugging
        e monitoring. In modalità strict, solleva un'eccezione.
        
        Args:
            message: Messaggio descrittivo dell'errore
            line_number: Numero della riga problematica
            line_content: Contenuto della riga problematica
        """
        error = {
            'message': message,
            'line_number': line_number,
            'line_content': line_content,
            'timestamp': datetime.now().isoformat(),
            'parser_type': self.__class__.__name__
        }
        self.errors.append(error)
        
        # Log dell'errore
        self.logger.error(f"Parsing error: {message}", extra={
            'line_number': line_number,
            'line_content': line_content
        })
        
        # In modalità strict, solleva eccezione
        if self.strict_mode:
            raise ParseError(message, line_number, line_content)
    
    def log_warning(self, message: str, line_number: int = None):
        """
        Registra un warning non critico.
        
        WHY: Separazione tra errori critici e warning per permettere
        al sistema di continuare il processing quando possibile.
        
        Args:
            message: Messaggio descrittivo del warning
            line_number: Numero della riga (opzionale)
        """
        warning = {
            'message': message,
            'line_number': line_number,
            'timestamp': datetime.now().isoformat(),
            'parser_type': self.__class__.__name__
        }
        self.warnings.append(warning)
        
        # Log del warning
        self.logger.warning(f"Parsing warning: {message}", extra={
            'line_number': line_number
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Restituisce statistiche del parsing.
        
        WHY: Metodo di utilità per monitoring e debugging,
        fornendo visibilità sui problemi di parsing.
        
        Returns:
            Dizionario con statistiche del parser
        """
        return {
            'parser_type': self.__class__.__name__,
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'strict_mode': self.strict_mode,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def clear_statistics(self):
        """
        Pulisce le statistiche accumulate.
        
        WHY: Permette di riutilizzare la stessa istanza del parser
        per multiple operazioni di parsing.
        """
        self.errors.clear()
        self.warnings.clear() 