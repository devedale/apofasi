"""
Parser specializzato per file di log in formato XML.

WHY: I file XML richiedono parsing strutturale, non line-by-line.
Questo parser mantiene la gerarchia e raggruppa correttamente i dati.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, Optional, Dict, Any

from ...domain.entities.log_entry import LogEntry
from ...domain.entities.parsed_record import ParsedRecord
from ...core.services.pattern_detection_service import PatternDetectionService
from .base_parser import BaseParser


class XMLLogParser(BaseParser):
    """
    Parser per file di log XML strutturati.
    
    Contract:
        - Input: File XML con elementi <log> che contengono dati strutturati
        - Output: Record parsati con struttura XML mantenuta
        - Side effects: Pattern detection applicato ai valori degli elementi
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inizializza l'XMLLogParser.
        
        Args:
            config: Configurazione del parser
        """
        super().__init__(config)
        self.pattern_detection_service = PatternDetectionService(config)
    
    def can_parse(self, content: str, filename: Optional[Path] = None) -> bool:
        """
        Verifica se questo parser può gestire il contenuto.
        
        Args:
            content: Contenuto da verificare
            filename: Nome del file (opzionale)
            
        Returns:
            True se può parsare il contenuto
        """
        # Verifica estensione XML
        if filename and filename.suffix.lower() == '.xml':
            return True
            
        # Verifica contenuto XML
        content_stripped = content.strip()
        return (content_stripped.startswith('<?xml') or 
                content_stripped.startswith('<') and 
                ('log' in content_stripped.lower()))
    
    def parse(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Parsa un file XML completo e estrae record strutturati.
        
        Args:
            log_entry: Entry del log da parsare
            
        Yields:
            ParsedRecord instances per ogni elemento log trovato
        """
        try:
            # Parse l'intero contenuto XML
            full_content = self._get_full_file_content(log_entry.source_file)
            root = ET.fromstring(full_content)
            
            # Trova tutti gli elementi log
            log_elements = self._find_log_elements(root)
            
            for idx, log_element in enumerate(log_elements, 1):
                # Estrai dati strutturati dall'elemento log
                parsed_data = self._extract_log_data(log_element)
                
                # Crea il contenuto originale ricostruito
                original_content = ET.tostring(log_element, encoding='unicode').strip()
                
                # Applica pattern detection ai valori estratti
                enriched_data = self.pattern_detection_service.add_template_and_patterns(
                    original_content, parsed_data
                )
                
                yield ParsedRecord(
                    original_content=original_content,
                    parsed_data=enriched_data,
                    parser_name="xml_log",
                    source_file=log_entry.source_file,
                    line_number=idx,  # Numero sequenziale dell'elemento log
                    confidence_score=0.9  # Alta confidenza per XML ben formato
                )
                
        except ET.ParseError as e:
            # XML malformato - fallback al parsing line-by-line
            yield ParsedRecord(
                original_content=log_entry.content,
                parsed_data={"error": f"XML parse error: {str(e)}"},
                parser_name="xml_log",
                source_file=log_entry.source_file,
                line_number=log_entry.line_number,
                confidence_score=0.1
            )
        except Exception as e:
            # Errore generico
            yield ParsedRecord(
                original_content=log_entry.content,
                parsed_data={"error": f"XML parser error: {str(e)}"},
                parser_name="xml_log",
                source_file=log_entry.source_file,
                line_number=log_entry.line_number,
                confidence_score=0.1
            )
    
    def _get_full_file_content(self, file_path: Path) -> str:
        """
        Legge l'intero contenuto del file XML.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            Contenuto completo del file
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _find_log_elements(self, root: ET.Element) -> list:
        """
        Trova tutti gli elementi che rappresentano singoli log entries.
        
        Args:
            root: Elemento radice XML
            
        Returns:
            Lista di elementi log
        """
        # Cerca elementi log a qualsiasi livello
        log_elements = []
        
        # Cerca elementi chiamati 'log'
        log_elements.extend(root.findall('.//log'))
        
        # Se non trova log, cerca altri pattern comuni
        if not log_elements:
            # Cerca entry, event, record, etc.
            for tag in ['entry', 'event', 'record', 'item']:
                log_elements.extend(root.findall(f'.//{tag}'))
        
        # Se ancora non trova nulla, usa i figli diretti
        if not log_elements and len(root) > 0:
            log_elements = list(root)
        
        return log_elements
    
    def _extract_log_data(self, log_element: ET.Element) -> Dict[str, Any]:
        """
        Estrae dati strutturati da un elemento log XML.
        
        Args:
            log_element: Elemento XML del log
            
        Returns:
            Dizionario con i dati estratti
        """
        data = {}
        
        # Aggiungi attributi dell'elemento
        if log_element.attrib:
            data['attributes'] = log_element.attrib
        
        # Estrai tutti i sottoelementi
        for child in log_element:
            field_name = child.tag
            field_value = child.text.strip() if child.text else ""
            
            # Se il campo già esiste, crea una lista
            if field_name in data:
                if not isinstance(data[field_name], list):
                    data[field_name] = [data[field_name]]
                data[field_name].append(field_value)
            else:
                data[field_name] = field_value
        
        return data
