"""
Multi-strategy parser che combina diversi approcci di parsing.

DESIGN: Usa il servizio regex centralizzato per garantire coerenza
tra anonimizzazione, pattern detection e template generation.
"""

import csv
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Iterator, List, Optional, Tuple

from ...domain.interfaces.log_parser import LogParser
from ...domain.entities.log_entry import LogEntry
from ...domain.entities.parsed_record import ParsedRecord
from ...domain.services.centralized_regex_service import CentralizedRegexService, CentralizedRegexServiceImpl
from ...core.services.pattern_detection_service import PatternDetectionService
from ...core.services.regex_service import RegexService

class MultiStrategyParser(LogParser):
    def __init__(self, config: Dict[str, Any], centralized_regex_service: Optional["CentralizedRegexService"] = None):
        """
        Inizializza il parser multi-strategy.
        
        Args:
            config: Configurazione del parser
            centralized_regex_service: Servizio regex centralizzato per coerenza
        """
        self._config = config
        
        # Servizio regex centralizzato per coerenza
        self._centralized_regex = centralized_regex_service or CentralizedRegexServiceImpl(config)
        
        # Pattern detection service
        self._pattern_detection_service = PatternDetectionService(config, self._centralized_regex)
        
        # Parsing patterns
        self._parsing_patterns = config.get("parsing_patterns", {})
        
        # CSV headers cache
        self.csv_headers: Dict[Path, Tuple[List[str], str]] = {}
        
        # Adaptive parser per fallback
        try:
            from ...infrastructure.parsers.adaptive_parser import AdaptiveParser
            self.adaptive_parser = AdaptiveParser(config)
        except ImportError:
            # Se non disponibile, crea un parser di fallback semplice
            self.adaptive_parser = None

    @property
    def name(self) -> str: return "MultiStrategyParser"
    @property
    def supported_formats(self) -> List[str]: return ["csv", "json", "syslog", "fortinet", "apache", "txt", "log"]
    @property
    def priority(self) -> int: return -1

    def can_parse(self, content: str, filename: Optional[Path] = None) -> bool:
        return True

    def parse(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Parsa il contenuto usando strategie multiple.
        
        WHY: source_file deve essere SEMPRE definito per evitare errori
        "source_file is not defined". Validiamo by design.
        
        Args:
            log_entry: Entry del log da parsare
            
        Yields:
            ParsedRecord instances
            
        Raises:
            ValueError: Se log_entry.source_file è None o vuoto
        """
        # VALIDAZIONE BY DESIGN: source_file deve essere sempre definito
        if not log_entry.source_file:
            raise ValueError(
                f"LogEntry deve avere source_file definito. "
                f"Ricevuto: {log_entry.source_file}"
            )
        
        try:
            # Prova prima il parsing strutturato
            parsed_data, parser_type = self._try_structured_parsing(log_entry)
            
            if parsed_data:
                # Crea il record con source_file SEMPRE definito
                yield self._create_record(log_entry, parsed_data, parser_type)
                return
            
            # Fallback al parser adattivo se disponibile
            if self.adaptive_parser:
                try:
                    yield from self.adaptive_parser.parse(log_entry)
                    return
                except Exception as e:
                    print(f"⚠️ ADAPTIVE PARSER FAILED [{log_entry.source_file}:{log_entry.line_number}]: {str(e)}")
            
        except Exception as e:
            print(f"❌ MULTI-STRATEGY PARSER ERROR [{log_entry.source_file}:{log_entry.line_number}]: {str(e)}")
        
        # Fallback semplice se non c'è parser adattivo
        yield self._create_fallback_record(log_entry, "No adaptive parser available")

    def parse_with_fallback(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Metodo richiesto dal LogProcessingService per compatibilità.
        Delega al metodo parse principale.
        """
        yield from self.parse(log_entry)

    def _try_structured_parsing(self, log_entry: LogEntry) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        content = log_entry.content
        source_file = log_entry.source_file

        # Strategia 1: CSV per estensione
        if source_file and source_file.suffix.lower() == '.csv':
            parsed_data = self._parse_csv_line(log_entry)
            if parsed_data:
                parser_type = "csv_header" if parsed_data.get('__is_header__') else "csv"
                return parsed_data, parser_type

        # Strategia 2: JSON
        if content.strip().startswith('{') and content.strip().endswith('}'):
            parsed_data = self._parse_json(content)
            if parsed_data:
                return parsed_data, "json"

        # Strategia 3: Pattern-based (Regex, KV, etc.)
        parsed_data, pattern_name = self._parse_with_patterns(content)
        if parsed_data:
            return parsed_data, pattern_name
            
        return None, None

    def _parse_csv_line(self, log_entry: LogEntry) -> Optional[Dict[str, Any]]:
        content, source_file, line_number = log_entry.content, log_entry.source_file, log_entry.line_number
        if not source_file: return None
        
        try:
            # Se è la prima riga, prova a determinare se è un header
            if line_number == 1:
                # Usa csv.Sniffer per rilevare il dialetto
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(content, delimiters=',;|\\t')
                
                # Leggi la prima riga
                reader = csv.reader(io.StringIO(content), dialect)
                first_row = next(reader)
                
                # Determina se è un header basandosi su:
                # 1. Se tutti i valori sembrano essere nomi di colonne (no numeri, date, etc.)
                # 2. Se la riga successiva esiste e ha un formato diverso
                is_header = self._is_likely_header(first_row)
                
                if is_header:
                    clean_header = [h.strip().replace(' ', '_').replace('-', '_').lower() or f"field_{i}" for i, h in enumerate(first_row)]
                    self.csv_headers[source_file] = (clean_header, dialect.delimiter)
                    # Parsa la prima riga come dati usando i nomi degli header rilevati
                    return {clean_header[i]: first_row[i].strip() for i in range(len(first_row))}
                else:
                    # Se la prima riga non è un header, crea header generici
                    num_columns = len(first_row)
                    generic_header = [f"column_{i+1}" for i in range(num_columns)]
                    self.csv_headers[source_file] = (generic_header, dialect.delimiter)
                    # Restituisci i dati della prima riga
                    return {generic_header[i]: first_row[i].strip() for i in range(len(first_row))}
            
            elif source_file in self.csv_headers:
                header, delimiter = self.csv_headers[source_file]
                reader = csv.reader(io.StringIO(content), delimiter=delimiter)
                values = next(reader)
                # Gestisce il caso di righe con più o meno colonne dell'header
                return {header[i]: values[i].strip() for i in range(min(len(header), len(values)))}
        except Exception as e:
            print(f"❌ CSV parsing error on line {line_number}: {e}")
        return None
    
    def _is_likely_header(self, row: List[str]) -> bool:
        """
        Determina se una riga è probabilmente un header basandosi su:
        - Assenza di numeri o date
        - Presenza di caratteri tipici dei nomi di colonna
        - Lunghezza delle stringhe
        """
        if not row:
            return False
        
        header_indicators = 0
        total_fields = len(row)
        
        for field in row:
            field = field.strip()
            if not field:
                continue
                
            # Indicatori che suggeriscono un header
            if any(indicator in field.lower() for indicator in ['id', 'name', 'type', 'date', 'time', 'ip', 'user', 'session', 'attack', 'protocol', 'browser']):
                header_indicators += 1
            elif field.replace('_', '').replace('-', '').replace(' ', '').isalpha():
                header_indicators += 1
            elif len(field) <= 20 and not any(char.isdigit() for char in field):
                header_indicators += 0.5
            
            # Indicatori che suggeriscono dati (non header)
            if any(char.isdigit() for char in field):
                header_indicators -= 0.5
            if field.count('.') > 0 and any(char.isdigit() for char in field):
                header_indicators -= 1  # Probabilmente un numero decimale
        
        # Se più del 60% dei campi sembrano header, considera la riga come header
        return header_indicators / total_fields > 0.6

    def _parse_json(self, content: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def _parse_with_patterns(self, content: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        # Ordina i pattern per priorità (pattern più specifici prima)
        priority_patterns = [
            'fortinet_log_kv',
            'syslog_format', 
            'syslog_bracket_format',
            'timestamp_bracket_format',
            'timestamp_level_format'
        ]
        
        best_match = None
        best_confidence = 0
        best_parser_type = None
        
        # Prima prova i pattern prioritari
        for pattern_name in priority_patterns:
            if pattern_name in self._parsing_patterns:
                config = self._parsing_patterns[pattern_name]
                pattern = self._regex_service.get_compiled_pattern(pattern_name)
                if not pattern: continue
                
                match = pattern.search(content)
                if match:
                    confidence = config.get('confidence', 0.5)
                    
                    # Se questo pattern ha confidenza più alta, usalo
                    if confidence > best_confidence:
                        parser_type = config.get('parser_type', 'generic_regex')
                        
                        if parser_type == 'generic_kv':
                            parsed_data = self._parse_key_value(content, config)
                        else: # Default a 'generic_regex'
                            parsed_data = match.groupdict()
                            if not parsed_data:
                                parsed_data = {f"field_{i+1}": group for i, group in enumerate(match.groups())}
                        
                        if 'enrichment' in config:
                            self._enrich_data(parsed_data, config['enrichment'])
                        
                        best_match = parsed_data
                        best_confidence = confidence
                        best_parser_type = config.get('description', pattern_name).lower().replace(' ', '_')
        
        # Se nessun pattern prioritario funziona, prova tutti gli altri
        for name, config in self._parsing_patterns.items():
            if name in priority_patterns:
                continue  # Già provati sopra
                
            # Salta i pattern problematici
            if name in ['timestamp_pipe_format', 'git_config_format', 'git_config_key_value']:
                continue
                
            pattern = self._regex_service.get_compiled_pattern(name)
            if not pattern: continue
            
            match = pattern.search(content)
            if match:
                confidence = config.get('confidence', 0.5)
                
                if confidence > best_confidence:
                    parser_type = config.get('parser_type', 'generic_regex')
                    
                    if parser_type == 'generic_kv':
                        parsed_data = self._parse_key_value(content, config)
                    else: # Default a 'generic_regex'
                        parsed_data = match.groupdict()
                        if not parsed_data:
                            parsed_data = {f"field_{i+1}": group for i, group in enumerate(match.groups())}
                    
                    if 'enrichment' in config:
                        self._enrich_data(parsed_data, config['enrichment'])
                    
                    best_match = parsed_data
                    best_confidence = confidence
                    best_parser_type = config.get('description', name).lower().replace(' ', '_')
        
        if best_match:
            return best_match, best_parser_type
        return None, None

    def _parse_key_value(self, content: str, config: Dict[str, Any]) -> Dict[str, str]:
        delimiter = config.get('delimiter', ' ')
        kv_separator = config.get('kv_separator', '=')
        
        # Regex semplificata per trovare coppie chiave=valore
        kv_pattern = re.compile(rf'([^{kv_separator}\s]+){kv_separator}("([^"]*)"|([^\s]+))')
        matches = kv_pattern.findall(content)
        
        result = {}
        for match in matches:
            if len(match) >= 3:
                key, quoted_val, unquoted_val = match[:3]
                value = quoted_val if quoted_val else unquoted_val
                if value:
                    result[key] = value.strip()
        
        return result

    def _enrich_data(self, data: Dict[str, Any], enrichment_configs: List[Dict[str, Any]]):
        for config in enrichment_configs:
            source_field = config.get('source_field')
            if source_field in data and isinstance(data[source_field], str):
                enrich_pattern_str = config.get('pattern')
                if not enrich_pattern_str: continue
                
                match = re.search(enrich_pattern_str, data[source_field])
                if match:
                    enrich_data = match.groupdict()
                    # Sovrascrive il campo originale e aggiunge i nuovi campi
                    if source_field in enrich_data:
                        original_value = data[source_field]
                        data.update(enrich_data)
                        data[source_field] = enrich_data.get(source_field, original_value)
                    else:
                        data.update(enrich_data)
    
    def _anonymize_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        anonymized_data = parsed_data.copy()
        for key, value in anonymized_data.items():
            if isinstance(value, str):
                anonymized_data[key] = self._regex_service.apply_patterns_by_category(value, 'anonymization')
        return anonymized_data

    # --- Metodi per creare i ParsedRecord ---
    def _create_record(self, log_entry: LogEntry, parsed_data: Dict[str, Any], parser_type: str) -> ParsedRecord:
        """
        Crea un record parsato con metadati separati dai dati.
        
        WHY: source_file deve essere SEMPRE definito per evitare errori
        "source_file is not defined". Validiamo by design.
        
        DESIGN: Usa il servizio regex centralizzato per garantire coerenza
        tra template generation e anonimizzazione.
        
        Args:
            log_entry: Entry del log con source_file OBBLIGATORIO
            parsed_data: Dati parsati
            parser_type: Tipo di parser utilizzato
            
        Returns:
            ParsedRecord con source_file sempre definito
            
        Raises:
            ValueError: Se log_entry.source_file è None o vuoto
        """
        # VALIDAZIONE BY DESIGN: source_file deve essere sempre definito
        if not log_entry.source_file:
            raise ValueError(
                f"LogEntry deve avere source_file definito. "
                f"Ricevuto: {log_entry.source_file}"
            )
        
        # Arricchisce i dati con template, cluster e pattern detection
        enriched_data = self._pattern_detection_service.add_template_and_patterns(
            log_entry.content, parsed_data
        )
        
        # Estrai metadati dai dati arricchiti (con fallback sicuri)
        metadata = {
            'template': enriched_data.pop('template', None),
            'cluster_id': enriched_data.pop('cluster_id', None),
            'cluster_size': enriched_data.pop('cluster_size', None),
            'detected_patterns': enriched_data.pop('detected_patterns', None),
        }
        
        # GENERA TEMPLATE COERENTI usando il servizio centralizzato
        # Template originale (per compatibilità)
        original_template = metadata['template']
        
        # Template anonimizzato (nuovo - coerente con anonymized_message)
        anonymized_template = None
        if self._centralized_regex:
            try:
                anonymized_template = self._centralized_regex.get_template_from_content(
                    log_entry.content, anonymized=True
                )
            except Exception as e:
                print(f"⚠️ Errore generazione template anonimizzato: {e}")
                anonymized_template = None
        
        # Estrai timestamp dal log se presente
        log_timestamp = self._extract_timestamp_from_data(parsed_data, log_entry.content)
        if log_timestamp:
            # Mantieni timestamp_info direttamente dentro parsed_data (richiesta utente)
            enriched_data['timestamp_info'] = log_timestamp
        
        # BY DESIGN: Estrai e aggiungi chiavi rilevate
        enriched_data = self.extract_detected_keys(log_entry.content, enriched_data)
        
        # Ottieni detected_headers se disponibili per questo file
        detected_headers = None
        if log_entry.source_file in self.csv_headers:
            header_fields, _ = self.csv_headers[log_entry.source_file]
            detected_headers = header_fields
        
        return ParsedRecord(
            timestamp=datetime.now(),
            original_content=log_entry.content,
            parsed_data=enriched_data,  # Solo i dati effettivi del log
            parser_name=parser_type,
            source_file=log_entry.source_file,  # ✅ SEMPRE definito
            line_number=log_entry.line_number,
            confidence_score=0.9,
            # Metadati del parsing
            detected_headers=detected_headers,
            template=original_template,  # ✅ Template originale
            anonymized_template=anonymized_template,  # ✅ Template anonimizzato coerente
            cluster_id=metadata['cluster_id'],
            cluster_size=metadata['cluster_size'],
            detected_patterns=metadata['detected_patterns'],
            log_timestamp=None,
        )

    def _extract_timestamp_from_data(self, parsed_data: Dict[str, Any], original_content: str = None) -> Optional[Dict[str, Any]]:
        """
        Estrae il timestamp dai dati parsati del log.
        
        WHY: Il timestamp del log è diverso dal timestamp di creazione del record.
        """
        # Cerca campi che potrebbero contenere timestamp
        timestamp_fields = ['timestamp', 'time', 'date', 'datetime', 'created_at', 'updated_at']
        
        for field in timestamp_fields:
            if field in parsed_data:
                value = parsed_data[field]
                if value and str(value).strip():
                    # Parsa il timestamp se possibile
                    parsed_timestamp = self._parse_timestamp_value(value)
                    if parsed_timestamp:
                        return {
                            'field': field,
                            'value': value,
                            'parsed_timestamp': parsed_timestamp,
                            'confidence': 0.9,
                            'source': 'parsed_data'
                        }
                    else:
                        return {
                            'field': field,
                            'value': value,
                            'confidence': 0.5,
                            'source': 'parsed_data'
                        }
        
        # Se non trova timestamp nei dati parsati, cerca nel contenuto originale
        if original_content:
            # Cerca pattern di timestamp nel contenuto originale
            timestamp_patterns = [
                r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?',  # 2020-02-07 23:46:57
                r'\d{4}-\d{2}-\d{2}',  # 2020-02-07
                r'\d{2}:\d{2}:\d{2}',  # 23:46:57
            ]
            
            for pattern in timestamp_patterns:
                match = re.search(pattern, original_content)
                if match:
                    timestamp_str = match.group(0)
                    parsed_timestamp = self._parse_timestamp_value(timestamp_str)
                    if parsed_timestamp:
                        return {
                            'field': 'content',
                            'value': timestamp_str,
                            'parsed_timestamp': parsed_timestamp,
                            'confidence': 0.7,
                            'source': 'content_scan'
                        }
        
        return None
    
    def _parse_timestamp_value(self, value: str) -> Optional[str]:
        """
        Parsa un valore di timestamp in formato ISO.
        
        Args:
            value: Valore del timestamp da parsare
            
        Returns:
            Timestamp in formato ISO o None se non parsabile
        """
        from datetime import datetime
        import re
        
        # Rimuovi spazi extra
        value = str(value).strip()
        
        # Pattern comuni per timestamp
        patterns = [
            # ISO format: 2020-02-07 23:46:57
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
            # ISO format with milliseconds: 2020-02-07 23:46:57.123
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)',
            # Date only: 2020-02-07
            r'(\d{4}-\d{2}-\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, value)
            if match:
                timestamp_str = match.group(1)
                try:
                    # Prova a parsare il timestamp
                    if '.' in timestamp_str:
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                    elif ' ' in timestamp_str:
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d')
                    
                    return dt.isoformat()
                except ValueError:
                    continue
        
        return None

    def _create_fallback_record(self, log_entry: LogEntry, error_msg: str) -> ParsedRecord:
        """
        Crea un record di fallback quando il parsing fallisce.
        
        WHY: source_file deve essere SEMPRE definito per evitare errori
        "source_file is not defined". Validiamo by design.
        
        Args:
            log_entry: Entry del log con source_file OBBLIGATORIO
            error_msg: Messaggio di errore
            
        Returns:
            ParsedRecord di fallback con source_file sempre definito
            
        Raises:
            ValueError: Se log_entry.source_file è None o vuoto
        """
        # VALIDAZIONE BY DESIGN: source_file deve essere sempre definito
        if not log_entry.source_file:
            raise ValueError(
                f"LogEntry deve avere source_file definito. "
                f"Ricevuto: {log_entry.source_file}"
            )
        
        record = ParsedRecord(
            timestamp=datetime.now(),
            original_content=log_entry.content,
            parsed_data={},
            parser_name="fallback_failure",
            source_file=log_entry.source_file,  # ✅ SEMPRE definito
            line_number=log_entry.line_number,
            confidence_score=0.1
        )
        record.add_error(error_msg)
        return record

    def extract_detected_keys(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estrae e aggiunge le chiavi rilevate al parsed_data.
        
        WHY: By design, tutti i parser devono implementare questa funzione
        per garantire coerenza nell'estrazione di chiavi e pattern rilevati.
        
        DESIGN: Estrazione intelligente multi-strategy che:
        1. Combina risultati da diversi parser
        2. Identifica pattern comuni e specifici
        3. Estrae metadati e caratteristiche
        4. Garantisce coerenza tra strategie diverse
        
        Args:
            content: Contenuto originale del log
            parsed_data: Dati già parsati dal parser
            
        Returns:
            parsed_data arricchito con chiavi rilevate
        """
        enriched_data = parsed_data.copy()
        
        # 1. ESTRAZIONE PATTERN BASE
        base_patterns = self._extract_base_patterns(content)
        enriched_data['_base_patterns'] = base_patterns
        
        # 2. ESTRAZIONE PATTERN SPECIFICI PER STRATEGIA
        if self._centralized_regex:
            # Pattern da regex centralizzati
            regex_patterns = self._extract_regex_patterns(content)
            enriched_data['_regex_patterns'] = regex_patterns
        
        # 3. ANALISI STRUTTURALE
        structural_analysis = self._analyze_structural_patterns(content, enriched_data)
        enriched_data['_structural_analysis'] = structural_analysis
        
        # 4. METADATI STANDARD
        enriched_data.update({
            '_detected_keys': {
                'parser_type': 'multi_strategy',
                'has_patterns': True,
                'strategy_count': len(self.parsers) if hasattr(self, 'parsers') else 1,
                'extraction_timestamp': datetime.now().isoformat()
            }
        })
        
        return enriched_data
    
    def _extract_base_patterns(self, content: str) -> Dict[str, Any]:
        """
        Estrae pattern base dal contenuto.
        
        Returns:
            Pattern base rilevati
        """
        patterns = {}
        
        # Pattern di timestamp
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}:\d{2}:\d{2}',  # HH:MM:SS
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        ]
        
        for pattern in timestamp_patterns:
            matches = re.findall(pattern, content)
            if matches:
                patterns['timestamp_patterns'] = {
                    'pattern': pattern,
                    'matches': len(matches),
                    'examples': matches[:5]
                }
        
        # Pattern di IP
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ip_matches = re.findall(ip_pattern, content)
        if ip_matches:
            patterns['ip_addresses'] = {
                'count': len(ip_matches),
                'examples': list(set(ip_matches))[:5]
            }
        
        # Pattern di email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, content)
        if email_matches:
            patterns['email_addresses'] = {
                'count': len(email_matches),
                'examples': email_matches[:5]
            }
        
        return patterns
    
    def _extract_regex_patterns(self, content: str) -> Dict[str, Any]:
        """
        Estrae pattern usando regex centralizzati.
        
        Returns:
            Pattern regex rilevati
        """
        if not self._centralized_regex:
            return {}
        
        patterns = {}
        
        try:
            # Pattern di anonimizzazione
            anonymization_patterns = self._centralized_regex.get_anonymization_patterns()
            for pattern_name, pattern_config in anonymization_patterns.items():
                pattern_str = pattern_config.get('pattern', '')
                if pattern_str:
                    matches = re.findall(pattern_str, content)
                    if matches:
                        patterns[f'anonymization_{pattern_name}'] = {
                            'count': len(matches),
                            'examples': matches[:3]
                        }
            
            # Pattern di parsing
            parsing_patterns = self._centralized_regex.get_parsing_patterns()
            for pattern_name, pattern_config in parsing_patterns.items():
                pattern_str = pattern_config.get('pattern', '')
                if pattern_str:
                    matches = re.findall(pattern_str, content)
                    if matches:
                        patterns[f'parsing_{pattern_name}'] = {
                            'count': len(matches),
                            'examples': matches[:3]
                        }
                        
        except Exception as e:
            patterns['error'] = str(e)
        
        return patterns
    
    def _analyze_structural_patterns(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analizza pattern strutturali nel contenuto.
        
        Returns:
            Analisi strutturale
        """
        analysis = {}
        
        # Analisi lunghezza
        analysis['length'] = {
            'content_length': len(content),
            'word_count': len(content.split()),
            'line_count': len(content.split('\n'))
        }
        
        # Analisi caratteri
        char_analysis = {}
        for char in content:
            if char.isalpha():
                char_analysis['alphabetic'] = char_analysis.get('alphabetic', 0) + 1
            elif char.isdigit():
                char_analysis['numeric'] = char_analysis.get('numeric', 0) + 1
            elif char.isspace():
                char_analysis['whitespace'] = char_analysis.get('whitespace', 0) + 1
            else:
                char_analysis['special'] = char_analysis.get('special', 0) + 1
        
        analysis['character_distribution'] = char_analysis
        
        # Analisi struttura
        if 'csv' in content.lower() or ',' in content:
            analysis['structure_type'] = 'csv_like'
        elif '{' in content and '}' in content:
            analysis['structure_type'] = 'json_like'
        elif '=' in content and '&' in content:
            analysis['structure_type'] = 'key_value_like'
        else:
            analysis['structure_type'] = 'text_like'
        
        return analysis
