"""
Rilevatore di tipo di file basato su magic numbers e contenuto.

WHY: Identifica il tipo di file basandosi sul contenuto binario invece
che sull'estensione, permettendo di riconoscere file Office, ZIP,
PDF e altri formati binari anche con estensioni diverse.
"""

import struct
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class FileTypeDetector:
    """
    Rilevatore di tipo di file basato su magic numbers.
    
    WHY: Risolve il problema di file con estensioni errate o mancanti,
    identificando il tipo reale basandosi sui primi byte del file.
    
    Contract:
        - Input: Percorso file o primi byte
        - Output: Tipo di file rilevato con confidenza
        - Side effects: Nessuno, analisi pura
    """
    
    def __init__(self):
        """Inizializza il rilevatore di tipo di file."""
        self.magic_numbers = self._load_magic_numbers()
    
    def _load_magic_numbers(self) -> Dict[bytes, Dict[str, any]]:
        """
        Carica i magic numbers per i formati più comuni.
        
        Returns:
            Dizionario con magic numbers e informazioni sui formati
        """
        return {
            # Office Open XML (XLSX, DOCX, PPTX)
            b'PK\x03\x04': {
                'type': 'office_open_xml',
                'extensions': ['.xlsx', '.docx', '.pptx', '.zip'],
                'description': 'Office Open XML / ZIP Archive',
                'confidence': 0.95
            },
            
            # ZIP Archive
            b'PK\x05\x06': {
                'type': 'zip',
                'extensions': ['.zip'],
                'description': 'ZIP Archive',
                'confidence': 0.95
            },
            
            # PDF
            b'%PDF': {
                'type': 'pdf',
                'extensions': ['.pdf'],
                'description': 'PDF Document',
                'confidence': 0.95
            },
            
            # PNG Image
            b'\x89PNG\r\n\x1a\n': {
                'type': 'png',
                'extensions': ['.png'],
                'description': 'PNG Image',
                'confidence': 0.95
            },
            
            # JPEG Image
            b'\xff\xd8\xff': {
                'type': 'jpeg',
                'extensions': ['.jpg', '.jpeg'],
                'description': 'JPEG Image',
                'confidence': 0.95
            },
            
            # GIF Image
            b'GIF87a': {
                'type': 'gif',
                'extensions': ['.gif'],
                'description': 'GIF Image',
                'confidence': 0.95
            },
            b'GIF89a': {
                'type': 'gif',
                'extensions': ['.gif'],
                'description': 'GIF Image',
                'confidence': 0.95
            },
            
            # Microsoft Office Legacy
            b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': {
                'type': 'office_legacy',
                'extensions': ['.doc', '.xls', '.ppt'],
                'description': 'Microsoft Office Legacy',
                'confidence': 0.95
            },
            
            # Executable (PE)
            b'MZ': {
                'type': 'executable',
                'extensions': ['.exe', '.dll', '.sys'],
                'description': 'Windows Executable',
                'confidence': 0.90
            },
            
            # ELF Executable
            b'\x7fELF': {
                'type': 'elf',
                'extensions': ['.elf', '.so', '.bin'],
                'description': 'ELF Executable',
                'confidence': 0.95
            },
            
            # Mach-O Executable
            b'\xfe\xed\xfa\xce': {
                'type': 'macho',
                'extensions': ['.app', '.dylib'],
                'description': 'Mach-O Executable',
                'confidence': 0.95
            },
            b'\xce\xfa\xed\xfe': {
                'type': 'macho',
                'extensions': ['.app', '.dylib'],
                'description': 'Mach-O Executable (Little Endian)',
                'confidence': 0.95
            },
            
            # Archive formats
            b'\x1f\x8b\x08': {
                'type': 'gzip',
                'extensions': ['.gz', '.tgz'],
                'description': 'GZIP Archive',
                'confidence': 0.95
            },
            
            b'BZh': {
                'type': 'bzip2',
                'extensions': ['.bz2', '.tbz2'],
                'description': 'BZIP2 Archive',
                'confidence': 0.95
            },
            
            # Text-based formats (check for UTF-8 BOM)
            b'\xef\xbb\xbf': {
                'type': 'text_utf8',
                'extensions': ['.txt', '.log', '.csv', '.json'],
                'description': 'UTF-8 Text with BOM',
                'confidence': 0.80
            }
        }
    
    def detect_file_type(self, file_path: Path) -> Dict[str, any]:
        """
        Rileva il tipo di file basandosi sui magic numbers.
        
        Args:
            file_path: Percorso del file da analizzare
            
        Returns:
            Dizionario con informazioni sul tipo di file rilevato
        """
        try:
            with open(file_path, 'rb') as f:
                # Leggi i primi 16 byte per il rilevamento
                header = f.read(16)
                
                if not header:
                    return self._create_unknown_result()
                
                # Prova a rilevare magic numbers
                for magic, info in self.magic_numbers.items():
                    if header.startswith(magic):
                        return {
                            'detected_type': info['type'],
                            'description': info['description'],
                            'confidence': info['confidence'],
                            'extensions': info['extensions'],
                            'magic_number': magic.hex(),
                            'file_path': str(file_path),
                            'file_size': file_path.stat().st_size
                        }
                
                # Se non trova magic numbers, prova a rilevare come testo
                return self._detect_text_format(header, file_path)
                
        except Exception as e:
            return {
                'detected_type': 'unknown',
                'description': f'Error detecting file type: {e}',
                'confidence': 0.0,
                'extensions': [],
                'magic_number': '',
                'file_path': str(file_path),
                'file_size': 0
            }
    
    def _detect_text_format(self, header: bytes, file_path: Path) -> Dict[str, any]:
        """
        Rileva se il file è in formato testo.
        
        Args:
            header: Primi byte del file
            file_path: Percorso del file
            
        Returns:
            Informazioni sul formato testo rilevato
        """
        # Controlla se è testo UTF-8 valido
        try:
            header.decode('utf-8')
            return {
                'detected_type': 'text_utf8',
                'description': 'UTF-8 Text File',
                'confidence': 0.70,
                'extensions': ['.txt', '.log', '.csv', '.json', '.xml'],
                'magic_number': '',
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size
            }
        except UnicodeDecodeError:
            # Prova a rilevare come binario generico
            return {
                'detected_type': 'binary',
                'description': 'Binary File',
                'confidence': 0.60,
                'extensions': ['.bin', '.dat'],
                'magic_number': '',
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size
            }
    
    def _create_unknown_result(self) -> Dict[str, any]:
        """Crea risultato per file sconosciuto."""
        return {
            'detected_type': 'unknown',
            'description': 'Unknown File Type',
            'confidence': 0.0,
            'extensions': [],
            'magic_number': '',
            'file_path': '',
            'file_size': 0
        }
    
    def is_office_file(self, file_path: Path) -> bool:
        """
        Controlla se il file è un documento Office.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            True se è un file Office
        """
        result = self.detect_file_type(file_path)
        return result['detected_type'] in ['office_open_xml', 'office_legacy']
    
    def is_archive_file(self, file_path: Path) -> bool:
        """
        Controlla se il file è un archivio.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            True se è un file di archivio
        """
        result = self.detect_file_type(file_path)
        return result['detected_type'] in ['zip', 'gzip', 'bzip2']
    
    def is_text_file(self, file_path: Path) -> bool:
        """
        Controlla se il file è in formato testo.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            True se è un file di testo
        """
        result = self.detect_file_type(file_path)
        return result['detected_type'] in ['text_utf8']
    
    def get_recommended_parser(self, file_path: Path) -> str:
        """
        Suggerisce il parser più appropriato per il file.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            Nome del parser raccomandato
        """
        result = self.detect_file_type(file_path)
        
        if result['detected_type'] == 'office_open_xml':
            return 'office_parser'
        elif result['detected_type'] == 'text_utf8':
            # Controlla l'estensione per suggerire parser specifici
            ext = file_path.suffix.lower()
            if ext == '.csv':
                return 'csv_parser'
            elif ext == '.json':
                return 'json_parser'
            elif ext == '.xml':
                return 'xml_parser'
            elif ext in ['.gz']:
                # File compressi - determina dal nome completo
                if '.csv.gz' in file_path.name.lower():
                    return 'csv_parser'
                elif '.json.gz' in file_path.name.lower():
                    return 'json_parser'
                elif '.xml.gz' in file_path.name.lower():
                    return 'xml_parser'
                else:
                    return 'adaptive_parser'
            elif ext in ['.txt', '.log', '.syslog', '.conf', '']:
                return 'adaptive_parser'
            else:
                return 'adaptive_parser'
        elif result['detected_type'] == 'binary':
            return 'binary_parser'
        else:
            return 'adaptive_parser' 