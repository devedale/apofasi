"""
CSV Header Detection - Rilevamento intelligente degli header CSV

Questo modulo implementa algoritmi per rilevare automaticamente
gli header CSV e distinguerli dai dati, risolvendo il problema
dei campi field_0, field_1, etc.

WHY: Risolve il problema critico di non riconoscere gli header CSV
che porta a campi generici invece di nomi significativi.
"""

import re
import csv
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CSVHeaderInfo:
    """Informazioni sugli header CSV rilevati."""
    headers: List[str]
    confidence: float
    delimiter: str
    is_header_row: bool
    header_row_index: int
    sample_data_rows: List[List[str]]


class CSVHeaderDetector:
    """
    Rilevatore intelligente di header CSV.
    
    WHY: Risolve il problema di non riconoscere gli header CSV
    che porta a campi generici invece di nomi significativi.
    """
    
    def __init__(self):
        """Inizializza il rilevatore di header CSV."""
        # Pattern per identificare header CSV
        self.header_indicators = [
            # Nomi di campo comuni in cybersecurity
            'session_id', 'network_packet_size', 'protocol_type', 'login_attempts',
            'session_duration', 'encryption_used', 'ip_reputation_score', 'failed_logins',
            'browser_type', 'unusual_time_access', 'attack_detected',
            'timestamp', 'time', 'date', 'datetime', 'event_time',
            'source_ip', 'destination_ip', 'src_ip', 'dst_ip', 'ip_address',
            'user_id', 'username', 'user', 'uid',
            'event_id', 'event_type', 'severity', 'level', 'priority',
            'component', 'service', 'module', 'class',
            'message', 'content', 'description', 'details',
            'status', 'result', 'action', 'operation',
            'port', 'protocol', 'service_name',
            'hash', 'checksum', 'signature',
            'country', 'location', 'region',
            'device_id', 'hostname', 'server_name',
            'request_method', 'http_method', 'url', 'path',
            'response_code', 'status_code', 'http_status',
            'bytes_sent', 'bytes_received', 'data_size',
            'duration', 'response_time', 'latency',
            'agent', 'user_agent', 'browser',
            'referrer', 'referer', 'origin',
            'cookie', 'session', 'token',
            'authentication', 'auth', 'login',
            'error', 'exception', 'failure',
            'warning', 'alert', 'notification',
            'blocked', 'denied', 'allowed', 'permitted',
            'suspicious', 'anomaly', 'threat', 'attack',
            'malware', 'virus', 'trojan', 'backdoor',
            'scan', 'probe', 'brute_force', 'dictionary',
            'injection', 'xss', 'sql_injection', 'csrf',
            'ddos', 'flood', 'overload', 'spam',
            'phishing', 'social_engineering', 'credential_stuffing',
            'privilege_escalation', 'lateral_movement', 'persistence',
            'exfiltration', 'data_theft', 'leak', 'breach'
        ]
        
        # Pattern per identificare dati (non header)
        self.data_indicators = [
            # Pattern numerici
            r'^\d+$',  # Solo numeri
            r'^\d+\.\d+$',  # Decimali
            r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',  # IP
            r'^[0-9a-fA-F]{32,64}$',  # Hash
            r'^\d{4}-\d{2}-\d{2}$',  # Data
            r'^\d{2}:\d{2}:\d{2}$',  # Ora
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO timestamp
            # Pattern di testo specifico
            r'^(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)$',  # HTTP methods
            r'^(TCP|UDP|ICMP|HTTP|HTTPS|FTP|SSH|TELNET)$',  # Protocolli
            r'^(ERROR|WARNING|INFO|DEBUG|CRITICAL)$',  # Log levels
            r'^(true|false|TRUE|FALSE)$',  # Booleani
            r'^(SID_|ID_|UID_|PID_)\d+$',  # ID con prefisso
        ]
    
    def detect_headers(self, lines: List[str]) -> Optional[CSVHeaderInfo]:
        """
        Rileva gli header CSV dalle righe fornite.
        
        WHY: Identifica automaticamente la riga di header
        per evitare campi generici field_0, field_1, etc.
        
        Args:
            lines: Lista di righe CSV
            
        Returns:
            CSVHeaderInfo con informazioni sugli header o None
        """
        if len(lines) < 2:
            return None
        
        # Prova diversi delimitatori
        delimiters = [',', ';', '\t', '|']
        
        best_header_info = None
        best_confidence = 0.0
        
        for delimiter in delimiters:
            header_info = self._analyze_with_delimiter(lines, delimiter)
            if header_info and header_info.confidence > best_confidence:
                best_header_info = header_info
                best_confidence = header_info.confidence
        
        return best_header_info
    
    def _analyze_with_delimiter(self, lines: List[str], delimiter: str) -> Optional[CSVHeaderInfo]:
        """
        Analizza le righe con un delimitatore specifico.
        
        Args:
            lines: Righe da analizzare
            delimiter: Delimitatore da utilizzare
            
        Returns:
            CSVHeaderInfo o None
        """
        # Parsa le prime righe per analisi
        parsed_lines = []
        for line in lines[:10]:  # Analizza solo le prime 10 righe
            if line.strip():
                parts = [part.strip() for part in line.split(delimiter)]
                parsed_lines.append(parts)
        
        if len(parsed_lines) < 2:
            return None
        
        # Trova la riga che sembra più un header
        header_row_index = self._find_header_row(parsed_lines)
        if header_row_index is None:
            return None
        
        headers = parsed_lines[header_row_index]
        
        # Calcola confidence basata su indicatori
        confidence = self._calculate_header_confidence(headers)
        
        # Verifica che le righe successive siano dati
        sample_data_rows = []
        for i in range(header_row_index + 1, min(len(parsed_lines), header_row_index + 4)):
            if len(parsed_lines[i]) == len(headers):
                sample_data_rows.append(parsed_lines[i])
        
        if not sample_data_rows:
            return None
        
        return CSVHeaderInfo(
            headers=headers,
            confidence=confidence,
            delimiter=delimiter,
            is_header_row=True,
            header_row_index=header_row_index,
            sample_data_rows=sample_data_rows
        )
    
    def _find_header_row(self, parsed_lines: List[List[str]]) -> Optional[int]:
        """
        Trova la riga che sembra più un header.
        
        Args:
            parsed_lines: Righe parsate
            
        Returns:
            Indice della riga header o None
        """
        best_row_index = None
        best_score = 0.0
        
        for row_index, row in enumerate(parsed_lines):
            if len(row) < 2:  # Header deve avere almeno 2 colonne
                continue
            
            score = self._calculate_header_score(row)
            if score > best_score:
                best_score = score
                best_row_index = row_index
        
        # Richiede un punteggio minimo per essere considerato header
        if best_score > 0.3:
            return best_row_index
        
        return None
    
    def _calculate_header_score(self, row: List[str]) -> float:
        """
        Calcola un punteggio per determinare se una riga è un header.
        
        Args:
            row: Riga da valutare
            
        Returns:
            Punteggio da 0.0 a 1.0
        """
        if not row:
            return 0.0
        
        score = 0.0
        total_fields = len(row)
        
        # Conta indicatori positivi
        header_indicators = 0
        data_indicators = 0
        
        for field in row:
            field_lower = field.lower()
            
            # Controlla indicatori di header
            for indicator in self.header_indicators:
                if indicator in field_lower:
                    header_indicators += 1
                    break
            
            # Controlla indicatori di dati
            for pattern in self.data_indicators:
                if re.match(pattern, field):
                    data_indicators += 1
                    break
        
        # Calcola punteggio
        if total_fields > 0:
            header_ratio = header_indicators / total_fields
            data_ratio = data_indicators / total_fields
            
            # Header dovrebbe avere molti indicatori di header e pochi di dati
            score = header_ratio * (1.0 - data_ratio)
        
        return score
    
    def _calculate_header_confidence(self, headers: List[str]) -> float:
        """
        Calcola la confidence degli header rilevati.
        
        Args:
            headers: Lista di header
            
        Returns:
            Confidence da 0.0 a 1.0
        """
        if not headers:
            return 0.0
        
        # Conta indicatori di header
        header_matches = 0
        for header in headers:
            header_lower = header.lower()
            for indicator in self.header_indicators:
                if indicator in header_lower:
                    header_matches += 1
                    break
        
        # Calcola confidence
        confidence = header_matches / len(headers)
        
        # Bonus per header con nomi significativi
        if confidence > 0.5:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def clean_header_names(self, headers: List[str]) -> List[str]:
        """
        Pulisce i nomi degli header per uso sicuro.
        
        Args:
            headers: Header originali
            
        Returns:
            Header puliti
        """
        cleaned_headers = []
        
        for header in headers:
            # Pulisci il nome
            clean_header = header.strip()
            
            # Sostituisci spazi e caratteri speciali
            clean_header = re.sub(r'[^a-zA-Z0-9_]', '_', clean_header)
            
            # Rimuovi underscore multipli
            clean_header = re.sub(r'_+', '_', clean_header)
            
            # Rimuovi underscore iniziali/finali
            clean_header = clean_header.strip('_')
            
            # Assicurati che non sia vuoto
            if not clean_header:
                clean_header = f'field_{len(cleaned_headers)}'
            
            # Assicurati che sia unico
            if clean_header in cleaned_headers:
                clean_header = f'{clean_header}_{len(cleaned_headers)}'
            
            cleaned_headers.append(clean_header)
        
        return cleaned_headers
    
    def is_likely_csv_file(self, filename: str) -> bool:
        """
        Determina se un file è probabilmente CSV.
        
        Args:
            filename: Nome del file
            
        Returns:
            True se probabilmente CSV
        """
        if not filename:
            return False
        
        # Controlla estensione
        ext = Path(filename).suffix.lower()
        if ext in ['.csv', '.tsv']:
            return True
        
        # Controlla pattern nel nome
        csv_patterns = ['data', 'log', 'export', 'report', 'analysis']
        filename_lower = filename.lower()
        for pattern in csv_patterns:
            if pattern in filename_lower:
                return True
        
        return False


def integrate_csv_header_detection(parser_instance, lines: List[str], filename: str = None) -> Optional[Tuple[List[str], str]]:
    """
    Integra il rilevamento degli header CSV in un parser esistente.
    
    WHY: Funzione di utilità per integrare il rilevamento header
    in parser esistenti senza modificare la loro logica principale.
    
    Args:
        parser_instance: Istanza del parser
        lines: Righe da analizzare
        filename: Nome del file
        
    Returns:
        Tuple (headers, delimiter) o None
    """
    detector = CSVHeaderDetector()
    
    # Controlla se è un file CSV
    if filename and detector.is_likely_csv_file(filename):
        header_info = detector.detect_headers(lines)
        if header_info and header_info.confidence > 0.5:
            cleaned_headers = detector.clean_header_names(header_info.headers)
            return cleaned_headers, header_info.delimiter
    
    return None 