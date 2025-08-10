"""
Adaptive Parser - Parser generico che si adatta automaticamente ai formati

Questo parser utilizza tecniche di machine learning e pattern recognition
per identificare automaticamente la struttura dei log senza hardcodare
campi specifici per ogni formato.

WHY: Fornisce un'astrazione completa che gestisce qualsiasi formato
di log senza richiedere configurazione specifica per ogni tipo.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import re
import json
import csv
from typing import Iterator, Dict, Any, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass
from datetime import datetime

from ...domain.entities.log_entry import LogEntry
from ...domain.entities.parsed_record import ParsedRecord
from ...core.services.pattern_detection_service import PatternDetectionService
from .base_parser import BaseParser, ParseError

from ...core.services.regex_service import RegexService


@dataclass
class FieldPattern:
    """Pattern identificato per un campo."""
    name: str
    pattern: str
    confidence: float
    examples: List[str]
    field_type: str  # 'timestamp', 'ip', 'number', 'text', 'enum'


@dataclass
class LogStructure:
    """Struttura identificata per un formato di log."""
    separator: str
    fields: List[FieldPattern]
    confidence: float
    sample_lines: List[str]
    is_csv_structure: bool = False
    csv_headers: Optional[List[str]] = None


class AdaptiveParser(BaseParser):
    """
    Parser adattivo potenziato che combina il clustering di Drain3 con
    l'arricchimento contestuale basato su regex.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.config = config or {}
        self.regex_service = RegexService()
        self.pattern_detection_service = PatternDetectionService(config)
        
        # Servizio regex centralizzato per generare anonymized_template
        try:
            from ...domain.services.centralized_regex_service import CentralizedRegexServiceImpl
            self.centralized_regex = CentralizedRegexServiceImpl(config)
        except ImportError:
            self.centralized_regex = None
        
        self.parsing_patterns = self.regex_service.get_patterns_by_category('parsing')

    def can_parse(self, content: str, filename: Optional[Path] = None) -> bool:
        """
        L'AdaptiveParser è un parser di fallback universale, quindi può
        sempre tentare di processare qualsiasi contenuto non vuoto.
        """
        return bool(content and content.strip())
    
    def parse(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Parsa una riga di log usando il PatternDetectionService per generare template e cluster,
        poi prepara il record per il processing Drain3 centralizzato.
        """
        content = log_entry.content
        
        # 1. Estrai coppie chiave-valore per creare parsed_data strutturati
        key_value_data = self._extract_key_value_pairs(content)
        
        # 2. Usa PatternDetectionService per generare template, cluster e pattern
        # Questo è il flusso originale che funzionava!
        enriched_data = self.pattern_detection_service.add_template_and_patterns(content, key_value_data)
        
        # 3. Genera anonymized_template se disponibile il servizio centralizzato
        anonymized_template = None
        if self.centralized_regex:
            try:
                anonymized_template = self.centralized_regex.get_template_from_content(content, anonymized=True)
            except Exception as e:
                print(f"⚠️ Errore generazione anonymized_template: {e}")
        
        # 4. Struttura i parsed_data in modo chiaro
        structured_parsed_data = {
            "data": key_value_data,  # Dati parsati (coppie key=value)
            "template": enriched_data.get('template'),
            "cluster_id": enriched_data.get('cluster_id'),
            "cluster_size": enriched_data.get('cluster_size'),
            "detected_patterns": enriched_data.get('detected_patterns'),
            "regex_patterns": enriched_data.get('regex_patterns', {})
        }
        
        # 5. Crea il record con tutti i metadati - il Drain3Service centralizzato si occuperà del processing
        record = ParsedRecord(
            original_content=content,
            parsed_data=structured_parsed_data,  # Dati strutturati con sezione data
            parser_name="adaptive_drain",
            source_file=log_entry.source_file,
            line_number=log_entry.line_number,
            confidence_score=0.6,  # Confidenza media, dato che è un'inferenza
            template=enriched_data.get('template'),
            anonymized_template=anonymized_template,
            cluster_id=enriched_data.get('cluster_id'),
            cluster_size=enriched_data.get('cluster_size'),
            detected_patterns=enriched_data.get('detected_patterns')
        )
        
        yield record

    def _extract_variables(self, content: str, template: str) -> List[str]:
        """
        Estrae le variabili dal contenuto del log basandosi sul template di Drain.
        """
        # Sostituisce il placeholder <*> nel template con un gruppo di cattura regex
        regex_pattern = re.escape(template).replace(r'\<\*\>', r'(.+?)')
        match = re.match(regex_pattern, content)
        
        if match:
            return list(match.groups())
        return []

    def _enrich_variables(self, variables: List[str]) -> Dict[str, Any]:
        """
        Analizza le variabili estratte con i pattern regex per classificarle.
        """
        enriched_data = {}
        unmatched_vars = []
        
        for var in variables:
            matched = False
            for pattern_name, pattern_config in self.parsing_patterns.items():
                pattern = pattern_config.get('pattern')
                if pattern and re.fullmatch(pattern, var):
                    # Se il pattern ha un solo campo di estrazione (es. 'level'),
                    # usa il nome del pattern come chiave.
                    field_name = pattern_config.get('description', pattern_name).lower().replace(' ', '_')
                    enriched_data[field_name] = var
                    matched = True
                    break
            
            if not matched:
                unmatched_vars.append(var)
        
        # Aggiunge le variabili non classificate in un campo generico
        if unmatched_vars:
            enriched_data['unmatched_variables'] = unmatched_vars
            
        return enriched_data

    
    def _identify_structure(self, lines: List[str]) -> Optional[LogStructure]:
        """
        Identifica automaticamente la struttura del log.
        
        Args:
            lines: Lista di righe da analizzare
            
        Returns:
            Struttura identificata o None se non rilevata
        """
        import signal
        import time
        
        # Timeout per evitare loop infiniti
        TIMEOUT_SECONDS = 30
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Analisi struttura timeout")
        
        # Imposta timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(TIMEOUT_SECONDS)
        
        try:
            # Analizza solo le prime 50 righe per performance (ridotto da 100)
            sample_lines = lines[:50]
            
            # Prova prima il rilevamento header CSV
            # csv_header_info = self.csv_header_detector.detect_headers(sample_lines)
            # if csv_header_info and csv_header_info.confidence > 0.6:
            #     # Crea struttura basata su header CSV
            #     structure = self._create_csv_structure(csv_header_info)
            #     if structure:
            #         self.logger.info(f"Header CSV rilevati: {len(csv_header_info.headers)} campi")
            #         return structure
            
            # Identifica separatori comuni con limite di tempo
            separators = self._identify_separators(sample_lines)
            
            best_structure = None
            best_confidence = 0.0
            
            # Limita il numero di separatori da testare
            for separator in separators[:5]:  # Massimo 5 separatori
                try:
                    structure = self._analyze_structure_with_separator(sample_lines, separator)
                    if structure and structure.confidence > best_confidence:
                        best_structure = structure
                        best_confidence = structure.confidence
                except Exception as e:
                    self.logger.warning(f"Errore analisi separatore '{separator}': {e}")
                    continue
            
            return best_structure
            
        except TimeoutError:
            self.logger.error("Timeout durante analisi struttura - usando fallback")
            return None
        except Exception as e:
            self.logger.error(f"Errore durante analisi struttura: {e}")
            return None
        finally:
            # Disabilita timeout
            signal.alarm(0)
    

    
    def _create_csv_structure(self, header_info) -> Optional[LogStructure]:
        """
        Crea una struttura basata su header CSV rilevati.
        
        Args:
            header_info: Informazioni sugli header CSV
            
        Returns:
            LogStructure basata su header CSV
        """
        # Metodo rimosso perché usa il detector legacy
        # Il MultiStrategyParser gestisce completamente i CSV
        return None
    
    def _classify_field_by_name(self, field_name: str) -> str:
        """
        Classifica un campo basandosi sul suo nome.
        
        Args:
            field_name: Nome del campo
            
        Returns:
            Tipo di campo
        """
        field_lower = field_name.lower()
        
        # Classifica basata su pattern nel nome
        if any(word in field_lower for word in ['timestamp', 'time', 'date', 'datetime']):
            return 'timestamp'
        elif any(word in field_lower for word in ['ip', 'address', 'src', 'dst']):
            return 'ip'
        elif any(word in field_lower for word in ['id', 'number', 'count', 'size', 'port']):
            return 'number'
        elif any(word in field_lower for word in ['type', 'status', 'level', 'method', 'protocol']):
            return 'enum'
        else:
            return 'text'
    
    def _identify_separators(self, lines: List[str]) -> List[str]:
        """
        Identifica i separatori più probabili.
        
        Args:
            lines: Righe da analizzare
            
        Returns:
            Lista di separatori ordinati per frequenza
        """
        separator_counts = Counter()
        
        for line in lines:
            if not line.strip():
                continue
            
            # Conta caratteri di separazione
            for char in line:
                if char in ' \t|,;:':
                    separator_counts[char] += 1
        
        # Restituisce separatori ordinati per frequenza
        return [sep for sep, count in separator_counts.most_common(5) if count > 0]
    
    def _analyze_structure_with_separator(self, lines: List[str], separator: str) -> Optional[LogStructure]:
        """
        Analizza la struttura usando un separatore specifico.
        
        Args:
            lines: Righe da analizzare
            separator: Separatore da utilizzare
            
        Returns:
            Struttura identificata o None
        """
        field_analysis = defaultdict(list)
        
        # Analizza ogni riga con limite per evitare loop
        max_lines = min(len(lines), 20)  # Massimo 20 righe per analisi
        
        for line in lines[:max_lines]:
            if not line.strip():
                continue
            
            parts = line.split(separator)
            # Limita il numero di parti per evitare campi eccessivi
            for i, part in enumerate(parts[:20]):  # Massimo 20 campi
                field_analysis[i].append(part.strip())
        
        # Identifica pattern per ogni posizione
        fields = []
        total_confidence = 0.0
        
        # Limita il numero di posizioni da analizzare
        for position, values in list(field_analysis.items())[:10]:  # Massimo 10 posizioni
            if len(values) < 2:  # Ridotto da 3 a 2
                continue
            
            try:
                field_pattern = self._identify_field_pattern(position, values)
                if field_pattern:
                    fields.append(field_pattern)
                    total_confidence += field_pattern.confidence
            except Exception as e:
                self.logger.warning(f"Errore analisi campo {position}: {e}")
                continue
        
        if not fields:
            return None
        
        avg_confidence = total_confidence / len(fields)
        
        return LogStructure(
            separator=separator,
            fields=fields,
            confidence=avg_confidence,
            sample_lines=lines[:3]  # Ridotto da 5 a 3
        )
    
    def _identify_field_pattern(self, position: int, values: List[str]) -> Optional[FieldPattern]:
        """
        Identifica il pattern per un campo specifico.
        
        Args:
            position: Posizione del campo
            values: Valori del campo
            
        Returns:
            Pattern identificato o None
        """
        # Rimuovi valori vuoti
        non_empty_values = [v for v in values if v.strip()]
        if len(non_empty_values) < 3:
            return None
        
        # Identifica il tipo di campo
        field_type, confidence = self._classify_field_type(non_empty_values)
        
        # Genera pattern regex
        pattern = self._generate_pattern(non_empty_values)
        
        # Nome del campo basato su posizione e tipo
        field_name = f"field_{position}_{field_type}"
        
        return FieldPattern(
            name=field_name,
            pattern=pattern,
            confidence=confidence,
            examples=non_empty_values[:3],
            field_type=field_type
        )
    
    def _classify_field_type(self, values: List[str]) -> Tuple[str, float]:
        """
        Classifica il tipo di un campo basato sui valori.
        
        Args:
            values: Valori del campo
            
        Returns:
            Tupla (tipo, confidenza)
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Regex timeout")
        
        # Timeout per regex (5 secondi)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)
        
        try:
            type_scores = defaultdict(float)
            
            # Limita il numero di valori da analizzare
            sample_values = values[:10]  # Massimo 10 valori
            
            for value in sample_values:
                # Testa ogni tipo di pattern con timeout
                for field_type, patterns in self.field_patterns.items():
                    for pattern in patterns:
                        try:
                            if re.match(pattern, value):
                                type_scores[field_type] += 1
                                break
                        except Exception:
                            # Ignora pattern problematici
                            continue
            
            if not type_scores:
                return 'text', 0.5
            
            # Trova il tipo più frequente
            best_type = max(type_scores, key=type_scores.get)
            confidence = type_scores[best_type] / len(sample_values)
            
            return best_type, confidence
            
        except TimeoutError:
            self.logger.warning("Timeout durante classificazione campo - usando text")
            return 'text', 0.3
        except Exception as e:
            self.logger.warning(f"Errore classificazione campo: {e} - usando text")
            return 'text', 0.3
        finally:
            signal.alarm(0)
    
    def _generate_pattern(self, values: List[str]) -> str:
        """
        Genera un pattern regex per i valori.
        
        Args:
            values: Valori da analizzare
            
        Returns:
            Pattern regex
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Pattern generation timeout")
        
        # Timeout per regex (3 secondi)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(3)
        
        try:
            if not values:
                return r'.*'
            
            # Limita il numero di valori da analizzare
            sample_values = values[:5]  # Massimo 5 valori
            
            # Pattern semplice basato sul primo valore
            first_value = sample_values[0]
            
            # Se tutti i valori sono uguali, usa il valore esatto
            if all(v == first_value for v in sample_values):
                return re.escape(first_value)
            
            # Pattern generico per il tipo di contenuto
            try:
                if re.match(r'\d+', first_value):
                    return r'\d+'
                elif re.match(r'\w+', first_value):
                    return r'\w+'
                else:
                    return r'.*'
            except Exception:
                return r'.*'
                
        except TimeoutError:
            self.logger.warning("Timeout durante generazione pattern - usando .*")
            return r'.*'
        except Exception as e:
            self.logger.warning(f"Errore generazione pattern: {e} - usando .*")
            return r'.*'
        finally:
            signal.alarm(0)
    
    def _parse_line(self, line: str, structure: LogStructure, line_number: int) -> Optional[Dict[str, Any]]:
        """
        Parsa una singola riga usando la struttura identificata.
        
        Args:
            line: Righe da parsare
            structure: Struttura identificata
            line_number: Numero di riga per logging
            
        Returns:
            Record parsato o None se fallisce
        """
        try:
            # Gestione speciale per strutture CSV
            if structure.is_csv_structure and structure.csv_headers:
                return self._parse_csv_line(line, structure, line_number)
            
            parts = line.split(structure.separator)
            
            if len(parts) != len(structure.fields):
                # Aggiusta il numero di parti se necessario
                if len(parts) < len(structure.fields):
                    parts.extend([''] * (len(structure.fields) - len(parts)))
                else:
                    parts = parts[:len(structure.fields)]
            
            record = {
                'line_number': line_number,
                'raw_line': line,
                'parser_type': 'adaptive',
                'parsed_at': datetime.now().isoformat(),
                'structure_confidence': structure.confidence
            }
            
            # Estrai campi usando i pattern identificati
            for i, (part, field_pattern) in enumerate(zip(parts, structure.fields)):
                value = part.strip()
                
                # Valida il valore usando il pattern
                if re.match(field_pattern.pattern, value):
                    record[field_pattern.name] = value
                else:
                    # Usa il valore anche se non matcha perfettamente
                    record[field_pattern.name] = value
                    self.logger.debug(f"Valore '{value}' non matcha pattern '{field_pattern.pattern}' "
                                   f"per campo {field_pattern.name}")
            
            # Analizza campi annidati per campi di testo
            record = self._extract_nested_fields(record)
            
            return record
            
        except Exception as e:
            self.logger.warning(f"Errore parsing riga {line_number}: {e}")
            return None
    
    def _parse_csv_line(self, line: str, structure: LogStructure, line_number: int) -> Optional[Dict[str, Any]]:
        """
        Parsa una riga CSV usando gli header rilevati.
        
        Args:
            line: Riga CSV da parsare
            structure: Struttura CSV con header
            line_number: Numero di riga
            
        Returns:
            Record parsato o None
        """
        try:
            if not line.strip():
                return None
            
            # Dividi la riga usando il separatore CSV
            parts = line.split(structure.separator)
            
            # Crea record base
            record = {
                'line_number': line_number,
                'raw_line': line,
                'parser_type': 'adaptive_csv',
                'parsed_at': datetime.now().isoformat(),
                'structure_confidence': structure.confidence,
                'csv_headers': structure.csv_headers
            }
            
            # Mappa i valori agli header
            for i, header in enumerate(structure.csv_headers):
                if i < len(parts):
                    value = parts[i].strip()
                    record[header] = value
                else:
                    record[header] = ""
            
            # Aggiungi campi extra se ci sono più valori che header
            for i in range(len(structure.csv_headers), len(parts)):
                record[f'extra_field_{i}'] = parts[i].strip()
            
            return record
            
        except Exception as e:
            self.logger.warning(f"Errore parsing riga CSV {line_number}: {e}")
            return None
    
    def _extract_nested_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estrae campi annidati dai campi di testo.
        
        WHY: Migliora la struttura dei dati parsati identificando
        campi chiave-valore annidati nei campi di testo.
        
        Args:
            record: Record da processare
            
        Returns:
            Record con campi annidati estratti
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Nested fields extraction timeout")
        
        # Timeout per estrazione campi annidati (5 secondi)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)
        
        try:
            # Crea una copia del record per evitare modifiche durante l'iterazione
            new_record = record.copy()
            
            # Limita il numero di campi da processare
            processed_fields = 0
            max_fields = 10  # Massimo 10 campi da processare
            
            for key, value in record.items():
                if processed_fields >= max_fields:
                    break
                    
                if isinstance(value, str) and '=' in value and len(value) < 500:  # Limite lunghezza
                    try:
                        # Identifica pattern di campi annidati
                        nested_fields = self._extract_key_value_pairs(value)
                        if nested_fields:
                            # Aggiungi campi annidati al record
                            for nested_key, nested_value in nested_fields.items():
                                new_record[f"{key}_{nested_key}"] = nested_value
                            
                            # Mantieni il campo originale per compatibilità
                            new_record[f"{key}_original"] = value
                            
                            processed_fields += 1
                    except Exception as e:
                        self.logger.warning(f"Errore estrazione campi annidati per {key}: {e}")
                        continue
            
            return new_record
            
        except TimeoutError:
            self.logger.warning("Timeout durante estrazione campi annidati")
            return record  # Ritorna il record originale
        except Exception as e:
            self.logger.warning(f"Errore estrazione campi annidati: {e}")
            return record  # Ritorna il record originale
        finally:
            signal.alarm(0)
    
    def _extract_key_value_pairs(self, text: str) -> Dict[str, str]:
        """
        Estrae coppie chiave-valore da un testo.
        
        WHY: Identifica automaticamente strutture chiave-valore
        come lock=233570404, flags=0x1, etc.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Dizionario con coppie chiave-valore
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Key-value extraction timeout")
        
        # Timeout per regex (3 secondi)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(3)
        
        try:
            pairs = {}
            
            # Limita la lunghezza del testo per evitare loop infiniti
            if len(text) > 1000:
                text = text[:1000]
            
            # Pattern semplificato e robusto
            # Pattern 1: chiave=valore semplice
            simple_pattern = r'(\w+)=([^=,\s]+)'
            
            try:
                matches = re.findall(simple_pattern, text)
                for key, value in matches:
                    clean_value = value.strip()
                    if clean_value and len(pairs) < 20:  # Limite di 20 coppie
                        pairs[key] = clean_value
            except Exception as e:
                self.logger.warning(f"Errore pattern semplice: {e}")
            
            # Pattern 2: chiave="valore"
            quoted_pattern = r'(\w+)="([^"]+)"'
            
            try:
                quoted_matches = re.findall(quoted_pattern, text)
                for key, value in quoted_matches:
                    clean_value = value.strip()
                    if clean_value and len(pairs) < 20 and key not in pairs:
                        pairs[key] = clean_value
            except Exception as e:
                self.logger.warning(f"Errore pattern virgolettato: {e}")
            
            # Pattern 3: chiave=valore con spazi (limitato)
            space_pattern = r'(\w+)=\s*([^=,]+?)(?=\s*\w+=|$)'
            
            try:
                space_matches = re.findall(space_pattern, text)
                for key, value in space_matches:
                    clean_value = value.strip()
                    if clean_value and len(pairs) < 20 and key not in pairs:
                        pairs[key] = clean_value
            except Exception as e:
                self.logger.warning(f"Errore pattern con spazi: {e}")
            
            return pairs
            
        except TimeoutError:
            self.logger.warning("Timeout durante estrazione chiave-valore")
            return {}
        except Exception as e:
            self.logger.warning(f"Errore estrazione chiave-valore: {e}")
            return {}
        finally:
            signal.alarm(0) 