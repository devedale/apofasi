"""
Parser per file binari generici.

WHY: Gestisce file binari che non possono essere parsati come testo,
fornendo informazioni sui metadati del file e analisi base.
"""

import hashlib
import struct
from typing import Iterator, Dict, Any
from pathlib import Path
import logging
from datetime import datetime

from ...domain.interfaces.log_parser import LogParser
from ...domain.entities.log_entry import LogEntry
from ...domain.entities.parsed_record import ParsedRecord


class BinaryParser(LogParser):
    """
    Parser per file binari generici.
    
    WHY: Fornisce analisi base di file binari quando non è possibile
    fare parsing del contenuto come testo, estraendo metadati e informazioni
    sulla struttura del file.
    
    Contract:
        - Input: File binario qualsiasi
        - Output: Metadati e analisi del file binario
        - Side effects: Analisi dei primi byte per magic numbers
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Inizializza il parser binario.
        
        Args:
            strict_mode: Modalità strict per parsing rigoroso
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)
    
    @property
    def name(self) -> str:
        """Get the name of this parser."""
        return "binary_parser"
    
    @property
    def supported_formats(self) -> list[str]:
        """Get list of supported formats."""
        return ["binary", "executable", "archive", "image", "unknown"]
    
    @property
    def priority(self) -> int:
        """Get parser priority (lower = higher priority)."""
        return 10  # Low priority for binary files
    
    def can_parse(self, content: str, filename: str = None) -> bool:
        """
        Determina se il contenuto è un file binario.
        
        Args:
            content: Contenuto da analizzare
            filename: Nome del file (opzionale)
            
        Returns:
            True se il contenuto è riconosciuto come binario
        """
        # Per file binari, controlla se il contenuto contiene caratteri non stampabili
        if content:
            # Conta caratteri non stampabili
            non_printable = sum(1 for c in content[:100] if not c.isprintable() and not c.isspace())
            if non_printable > len(content[:100]) * 0.3:  # Più del 30% non stampabile
                return True
        
        return False
    
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        """
        Parsa un file binario.
        
        Args:
            content: Contenuto del file (non usato per file binari)
            filename: Nome del file da parsare
            
        Yields:
            Dizionari con i dati parsati
        """
        try:
            if not filename:
                self.logger.error("Nome file richiesto per parsing binario")
                return
            
            file_path = Path(filename)
            
            # Analizza il file binario
            binary_info = self._analyze_binary_file(file_path)
            
            # Aggiungi metadati del parsing
            binary_info.update({
                'parser_type': 'Binary',
                'filename': str(file_path),
                'parsed_at': datetime.now().isoformat()
            })
            
            yield binary_info
            
        except Exception as e:
            self.logger.error(f"Errore parsing file binario {filename}: {e}")
            yield {
                'error': str(e),
                'parser_type': 'Binary',
                'filename': filename,
                'parsed_at': datetime.now().isoformat()
            }
    
    def _analyze_binary_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analizza un file binario.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            Informazioni sul file binario
        """
        try:
            with open(file_path, 'rb') as f:
                # Leggi i primi 64 byte per l'analisi
                header = f.read(64)
                
                if not header:
                    return {"error": "File vuoto"}
                
                # Calcola hash del file
                f.seek(0)
                file_hash = hashlib.sha256(f.read()).hexdigest()
                
                # Analizza magic numbers
                magic_info = self._analyze_magic_numbers(header)
                
                # Analizza statistiche del file
                stats = self._analyze_file_statistics(file_path, header)
                
                return {
                    'file_type': 'binary',
                    'file_path': str(file_path),
                    'file_size': file_path.stat().st_size,
                    'file_hash': file_hash,
                    'magic_numbers': magic_info,
                    'statistics': stats,
                    'analysis': {
                        'is_executable': self._is_executable(header),
                        'is_archive': self._is_archive(header),
                        'is_image': self._is_image(header),
                        'entropy': self._calculate_entropy(header)
                    }
                }
                
        except Exception as e:
            return {"error": f"Errore analisi file binario: {e}"}
    
    def _analyze_magic_numbers(self, header: bytes) -> Dict[str, Any]:
        """
        Analizza i magic numbers del file.
        
        Args:
            header: Primi byte del file
            
        Returns:
            Informazioni sui magic numbers
        """
        magic_numbers = {
            b'PK\x03\x04': 'ZIP/Office Open XML',
            b'PK\x05\x06': 'ZIP Archive',
            b'%PDF': 'PDF Document',
            b'\x89PNG\r\n\x1a\n': 'PNG Image',
            b'\xff\xd8\xff': 'JPEG Image',
            b'GIF87a': 'GIF Image',
            b'GIF89a': 'GIF Image',
            b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': 'Microsoft Office Legacy',
            b'MZ': 'Windows Executable',
            b'\x7fELF': 'ELF Executable',
            b'\xfe\xed\xfa\xce': 'Mach-O Executable',
            b'\x1f\x8b\x08': 'GZIP Archive',
            b'BZh': 'BZIP2 Archive'
        }
        
        detected_types = []
        for magic, description in magic_numbers.items():
            if header.startswith(magic):
                detected_types.append({
                    'magic': magic.hex(),
                    'description': description,
                    'confidence': 0.95
                })
        
        return {
            'detected_types': detected_types,
            'header_hex': header[:16].hex(),
            'header_ascii': ''.join(chr(b) if 32 <= b <= 126 else '.' for b in header[:16])
        }
    
    def _analyze_file_statistics(self, file_path: Path, header: bytes) -> Dict[str, Any]:
        """
        Analizza statistiche del file.
        
        Args:
            file_path: Percorso del file
            header: Primi byte del file
            
        Returns:
            Statistiche del file
        """
        file_size = file_path.stat().st_size
        
        # Calcola distribuzione dei byte
        byte_counts = {}
        for byte in header:
            byte_counts[byte] = byte_counts.get(byte, 0) + 1
        
        # Trova byte più comuni
        most_common_bytes = sorted(byte_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'file_size': file_size,
            'header_size': len(header),
            'unique_bytes': len(byte_counts),
            'most_common_bytes': [{'byte': f'0x{b:02x}', 'count': c} for b, c in most_common_bytes],
            'null_bytes': byte_counts.get(0, 0),
            'printable_ratio': sum(1 for b in header if 32 <= b <= 126) / len(header)
        }
    
    def _is_executable(self, header: bytes) -> bool:
        """Controlla se il file è un eseguibile."""
        return (header.startswith(b'MZ') or 
                header.startswith(b'\x7fELF') or 
                header.startswith(b'\xfe\xed\xfa\xce') or
                header.startswith(b'\xce\xfa\xed\xfe'))
    
    def _is_archive(self, header: bytes) -> bool:
        """Controlla se il file è un archivio."""
        return (header.startswith(b'PK') or 
                header.startswith(b'\x1f\x8b\x08') or 
                header.startswith(b'BZh'))
    
    def _is_image(self, header: bytes) -> bool:
        """Controlla se il file è un'immagine."""
        return (header.startswith(b'\x89PNG\r\n\x1a\n') or 
                header.startswith(b'\xff\xd8\xff') or 
                header.startswith(b'GIF87a') or 
                header.startswith(b'GIF89a'))
    
    def _calculate_entropy(self, data: bytes) -> float:
        """
        Calcola l'entropia dei dati.
        
        Args:
            data: Dati da analizzare
            
        Returns:
            Entropia (0.0 - 8.0)
        """
        if not data:
            return 0.0
        
        # Calcola frequenza dei byte
        byte_counts = {}
        for byte in data:
            byte_counts[byte] = byte_counts.get(byte, 0) + 1
        
        # Calcola entropia
        entropy = 0.0
        data_len = len(data)
        
        for count in byte_counts.values():
            if count > 0:
                probability = count / data_len
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy 