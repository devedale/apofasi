"""
Parser per file Office (XLSX, DOCX, PPTX).

WHY: Gestisce file Office Open XML che sono essenzialmente
archivi ZIP con contenuto XML strutturato.
"""

import zipfile
import xml.etree.ElementTree as ET
from typing import Iterator, Dict, Any, List
from pathlib import Path
import logging
from datetime import datetime

from ...domain.interfaces.log_parser import LogParser
from ...domain.entities.log_entry import LogEntry
from ...domain.entities.parsed_record import ParsedRecord


class OfficeParser(LogParser):
    """
    Parser per file Office Open XML.
    
    WHY: Gestisce file Office che sono archivi ZIP con contenuto XML,
    estraendo dati strutturati da fogli di calcolo, documenti e presentazioni.
    
    Contract:
        - Input: File Office Open XML (XLSX, DOCX, PPTX)
        - Output: Record parsati con dati strutturati
        - Side effects: Estrazione temporanea di file XML
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Inizializza il parser Office.
        
        Args:
            strict_mode: Modalità strict per parsing rigoroso
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)
        
        # Configurazione per diversi tipi di file Office
        self.office_types = {
            'xlsx': {
                'content_types': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
                'main_file': 'xl/workbook.xml',
                'data_files': ['xl/worksheets/sheet*.xml'],
                'parser': self._parse_excel
            },
            'docx': {
                'content_types': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                'main_file': 'word/document.xml',
                'data_files': ['word/document.xml'],
                'parser': self._parse_word
            },
            'pptx': {
                'content_types': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
                'main_file': 'ppt/presentation.xml',
                'data_files': ['ppt/slides/slide*.xml'],
                'parser': self._parse_powerpoint
            }
        }
    
    @property
    def name(self) -> str:
        """Get the name of this parser."""
        return "office_parser"
    
    @property
    def supported_formats(self) -> List[str]:
        """Get list of supported formats."""
        return ["xlsx", "docx", "pptx", "office_open_xml"]
    
    @property
    def priority(self) -> int:
        """Get parser priority (lower = higher priority)."""
        return 5  # Medium priority for Office files
    
    def can_parse(self, content: str, filename: str = None) -> bool:
        """
        Determina se il contenuto è un file Office valido.
        
        Args:
            content: Contenuto da analizzare
            filename: Nome del file (opzionale)
            
        Returns:
            True se il contenuto è riconosciuto come file Office
        """
        # Per file Office, controlla principalmente il nome del file
        if filename:
            file_path = Path(filename)
            if file_path.suffix.lower() in ['.xlsx', '.docx', '.pptx']:
                return True
        
        # Controlla se il contenuto inizia con magic number ZIP
        if content.startswith('PK'):
            return True
        
        return False
    
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        """
        Parsa un file Office.
        
        Args:
            content: Contenuto del file (non usato per file binari)
            filename: Nome del file da parsare
            
        Yields:
            Dizionari con i dati parsati
        """
        try:
            if not filename:
                self.logger.error("Nome file richiesto per parsing Office")
                return
            
            file_path = Path(filename)
            
            # Determina il tipo di file Office
            office_type = self._detect_office_type(file_path)
            if not office_type:
                self.logger.warning(f"Tipo di file Office non rilevato per {file_path}")
                return
            
            # Parsa il file Office
            parsed_data = self._parse_office_file(file_path, office_type)
            
            # Aggiungi metadati del parsing
            parsed_data.update({
                'parser_type': 'Office',
                'filename': str(file_path),
                'office_type': office_type,
                'parsed_at': datetime.now().isoformat()
            })
            
            yield parsed_data
            
        except Exception as e:
            self.logger.error(f"Errore parsing file Office {filename}: {e}")
            yield {
                'error': str(e),
                'parser_type': 'Office',
                'filename': filename,
                'parsed_at': datetime.now().isoformat()
            }
    
    def _detect_office_type(self, file_path: Path) -> str:
        """
        Rileva il tipo di file Office.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            Tipo di file Office ('xlsx', 'docx', 'pptx') o None
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Controlla il file [Content_Types].xml
                if '[Content_Types].xml' in zip_file.namelist():
                    content_types_content = zip_file.read('[Content_Types].xml').decode('utf-8')
                    
                    # Cerca il tipo di contenuto principale
                    for office_type, config in self.office_types.items():
                        for content_type in config['content_types']:
                            if content_type in content_types_content:
                                return office_type
                
                # Fallback basato sull'estensione
                ext = file_path.suffix.lower()
                if ext == '.xlsx':
                    return 'xlsx'
                elif ext == '.docx':
                    return 'docx'
                elif ext == '.pptx':
                    return 'pptx'
                
        except Exception as e:
            self.logger.error(f"Errore rilevamento tipo Office per {file_path}: {e}")
        
        return None
    
    def _parse_office_file(self, file_path: Path, office_type: str) -> Dict[str, Any]:
        """
        Parsa un file Office specifico.
        
        Args:
            file_path: Percorso del file
            office_type: Tipo di file Office
            
        Returns:
            Dati parsati
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Usa il parser specifico per il tipo di file
                if office_type in self.office_types:
                    parser_func = self.office_types[office_type]['parser']
                    return parser_func(zip_file, file_path)
                else:
                    return {"error": f"Tipo di file Office non supportato: {office_type}"}
                    
        except Exception as e:
            return {"error": f"Errore parsing file Office: {e}"}
    
    def _parse_excel(self, zip_file: zipfile.ZipFile, file_path: Path) -> Dict[str, Any]:
        """
        Parsa un file Excel (XLSX).
        
        Args:
            zip_file: File ZIP aperto
            file_path: Percorso del file originale
            
        Returns:
            Dati parsati dal file Excel
        """
        try:
            # Leggi il file workbook.xml
            if 'xl/workbook.xml' in zip_file.namelist():
                workbook_content = zip_file.read('xl/workbook.xml').decode('utf-8')
                workbook_root = ET.fromstring(workbook_content)
                
                # Estrai informazioni sui fogli
                sheets = []
                for sheet in workbook_root.findall('.//{*}sheet'):
                    sheet_name = sheet.get('name', 'Unknown')
                    sheet_id = sheet.get('sheetId', '0')
                    sheets.append({
                        'name': sheet_name,
                        'id': sheet_id
                    })
                
                # Estrai dati dai fogli di calcolo
                sheet_data = []
                for sheet in sheets:
                    sheet_file = f'xl/worksheets/sheet{sheet["id"]}.xml'
                    if sheet_file in zip_file.namelist():
                        sheet_content = zip_file.read(sheet_file).decode('utf-8')
                        sheet_root = ET.fromstring(sheet_content)
                        
                        # Estrai celle
                        cells = []
                        for row in sheet_root.findall('.//{*}row'):
                            row_data = []
                            for cell in row.findall('.//{*}c'):
                                cell_value = cell.get('v', '')
                                cell_ref = cell.get('r', '')
                                row_data.append({
                                    'reference': cell_ref,
                                    'value': cell_value
                                })
                            if row_data:
                                cells.append(row_data)
                        
                        sheet_data.append({
                            'sheet_name': sheet['name'],
                            'cells': cells
                        })
                
                return {
                    'file_type': 'excel',
                    'file_path': str(file_path),
                    'sheets': sheets,
                    'sheet_data': sheet_data,
                    'total_sheets': len(sheets),
                    'total_cells': sum(len(cells) for cells in sheet_data)
                }
            else:
                return {"error": "File workbook.xml non trovato"}
                
        except Exception as e:
            return {"error": f"Errore parsing Excel: {e}"}
    
    def _parse_word(self, zip_file: zipfile.ZipFile, file_path: Path) -> Dict[str, Any]:
        """
        Parsa un file Word (DOCX).
        
        Args:
            zip_file: File ZIP aperto
            file_path: Percorso del file originale
            
        Returns:
            Dati parsati dal file Word
        """
        try:
            # Leggi il file document.xml
            if 'word/document.xml' in zip_file.namelist():
                document_content = zip_file.read('word/document.xml').decode('utf-8')
                document_root = ET.fromstring(document_content)
                
                # Estrai paragrafi
                paragraphs = []
                for para in document_root.findall('.//{*}p'):
                    text_elements = para.findall('.//{*}t')
                    if text_elements:
                        text = ' '.join(elem.text or '' for elem in text_elements)
                        if text.strip():
                            paragraphs.append(text.strip())
                
                return {
                    'file_type': 'word',
                    'file_path': str(file_path),
                    'paragraphs': paragraphs,
                    'total_paragraphs': len(paragraphs),
                    'total_words': sum(len(p.split()) for p in paragraphs)
                }
            else:
                return {"error": "File document.xml non trovato"}
                
        except Exception as e:
            return {"error": f"Errore parsing Word: {e}"}
    
    def _parse_powerpoint(self, zip_file: zipfile.ZipFile, file_path: Path) -> Dict[str, Any]:
        """
        Parsa un file PowerPoint (PPTX).
        
        Args:
            zip_file: File ZIP aperto
            file_path: Percorso del file originale
            
        Returns:
            Dati parsati dal file PowerPoint
        """
        try:
            # Leggi il file presentation.xml
            if 'ppt/presentation.xml' in zip_file.namelist():
                presentation_content = zip_file.read('ppt/presentation.xml').decode('utf-8')
                presentation_root = ET.fromstring(presentation_content)
                
                # Estrai slide
                slides = []
                slide_files = [f for f in zip_file.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
                
                for slide_file in slide_files:
                    slide_content = zip_file.read(slide_file).decode('utf-8')
                    slide_root = ET.fromstring(slide_content)
                    
                    # Estrai testo dalle slide
                    text_elements = slide_root.findall('.//{*}t')
                    slide_text = ' '.join(elem.text or '' for elem in text_elements if elem.text)
                    
                    if slide_text.strip():
                        slides.append(slide_text.strip())
                
                return {
                    'file_type': 'powerpoint',
                    'file_path': str(file_path),
                    'slides': slides,
                    'total_slides': len(slides),
                    'total_words': sum(len(s.split()) for s in slides)
                }
            else:
                return {"error": "File presentation.xml non trovato"}
                
        except Exception as e:
            return {"error": f"Errore parsing PowerPoint: {e}"} 