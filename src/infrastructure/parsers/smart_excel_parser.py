"""
Parser intelligente per file Excel usando pandas.

WHY: Usa pandas per estrarre dati strutturati da Excel in modo efficiente,
evitando celle vuote e creando output compatibile con il sistema di log.
"""

import pandas as pd
import numpy as np
from typing import Iterator, Dict, Any, List, Optional
from pathlib import Path
import logging
from datetime import datetime

from ...domain.interfaces.log_parser import LogParser
from ...domain.entities.log_entry import LogEntry
from ...domain.entities.parsed_record import ParsedRecord


class SmartExcelParser(LogParser):
    """
    Parser intelligente per file Excel.
    
    WHY: Usa pandas per estrarre dati strutturati da Excel in modo efficiente,
    evitando celle vuote e creando output compatibile con il sistema di log.
    
    Contract:
        - Input: File Excel (XLSX, XLS)
        - Output: Record strutturati come log parsati
        - Side effects: Nessuno, analisi pura
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Inizializza il parser Excel intelligente.
        
        Args:
            strict_mode: Modalità strict per parsing rigoroso
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)
    
    @property
    def name(self) -> str:
        """Get the name of this parser."""
        return "smart_excel_parser"
    
    @property
    def supported_formats(self) -> List[str]:
        """Get list of supported formats."""
        return ["xlsx", "xls", "excel"]
    
    @property
    def priority(self) -> int:
        """Get parser priority (lower = higher priority)."""
        return 3  # High priority for Excel files
    
    def can_parse(self, content: str, filename: str = None) -> bool:
        """
        Determina se il contenuto è un file Excel valido.
        
        Args:
            content: Contenuto da analizzare
            filename: Nome del file (opzionale)
            
        Returns:
            True se il contenuto è riconosciuto come Excel
        """
        if filename:
            file_path = Path(filename)
            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                return True
        
        # Controlla se il contenuto inizia con magic number ZIP (XLSX)
        if content.startswith('PK'):
            return True
        
        return False
    
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        """
        Parsa un file Excel in modo intelligente.
        
        Args:
            content: Contenuto del file (non usato)
            filename: Nome del file da parsare
            
        Yields:
            Dizionari con i dati parsati strutturati
        """
        try:
            if not filename:
                self.logger.error("Nome file richiesto per parsing Excel")
                return
            
            file_path = Path(filename)
            
            # Leggi il file Excel con pandas
            excel_data = self._read_excel_file(file_path)
            
            # Converti in record strutturati
            for record in self._convert_to_structured_records(excel_data, file_path):
                yield record
                
        except Exception as e:
            self.logger.error(f"Errore parsing Excel {filename}: {e}")
            yield {
                'error': str(e),
                'parser_type': 'SmartExcel',
                'filename': filename,
                'parsed_at': datetime.now().isoformat()
            }
    
    def _read_excel_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Legge il file Excel con pandas.
        
        Args:
            file_path: Percorso del file Excel
            
        Returns:
            Dati Excel strutturati
        """
        try:
            # Leggi tutti i fogli
            excel_file = pd.ExcelFile(file_path)
            sheets_data = {}
            
            for sheet_name in excel_file.sheet_names:
                # Leggi il foglio come DataFrame
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Pulisci il DataFrame
                df_clean = self._clean_dataframe(df)
                
                sheets_data[sheet_name] = {
                    'dataframe': df_clean,
                    'shape': df_clean.shape,
                    'columns': list(df_clean.columns),
                    'dtypes': df_clean.dtypes.to_dict(),
                    'null_counts': df_clean.isnull().sum().to_dict(),
                    'sample_data': df_clean.head(10).to_dict('records')
                }
            
            return {
                'file_path': str(file_path),
                'sheets': sheets_data,
                'total_sheets': len(sheets_data),
                'file_size': file_path.stat().st_size
            }
            
        except Exception as e:
            raise Exception(f"Errore lettura Excel: {e}")
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Pulisce il DataFrame rimuovendo righe e colonne vuote.
        
        Args:
            df: DataFrame da pulire
            
        Returns:
            DataFrame pulito
        """
        # Rimuovi righe completamente vuote
        df_clean = df.dropna(how='all')
        
        # Rimuovi colonne completamente vuote
        df_clean = df_clean.dropna(axis=1, how='all')
        
        # Reset degli indici
        df_clean = df_clean.reset_index(drop=True)
        
        return df_clean
    
    def _convert_to_structured_records(self, excel_data: Dict[str, Any], file_path: Path) -> Iterator[Dict[str, Any]]:
        """
        Converte i dati Excel in record strutturati.
        
        Args:
            excel_data: Dati Excel parsati
            file_path: Percorso del file originale
            
        Yields:
            Record strutturati
        """
        for sheet_name, sheet_data in excel_data['sheets'].items():
            df = sheet_data['dataframe']
            
            # Se il DataFrame è vuoto, salta
            if df.empty:
                continue
            
            # Determina il tipo di dati
            data_type = self._detect_data_type(df)
            
            # Crea record per ogni riga
            for index, row in df.iterrows():
                record = self._create_structured_record(
                    row, index, sheet_name, data_type, file_path
                )
                yield record
    
    def _detect_data_type(self, df: pd.DataFrame) -> str:
        """
        Determina il tipo di dati nel DataFrame.
        
        Args:
            df: DataFrame da analizzare
            
        Returns:
            Tipo di dati rilevato
        """
        # Analizza le colonne per determinare il tipo
        column_names = [str(col).lower() for col in df.columns]
        
        # Pattern per diversi tipi di dati
        if any('timestamp' in col or 'date' in col or 'time' in col for col in column_names):
            return 'temporal_data'
        elif any('ip' in col or 'address' in col for col in column_names):
            return 'network_data'
        elif any('user' in col or 'login' in col or 'auth' in col for col in column_names):
            return 'user_data'
        elif any('error' in col or 'log' in col or 'event' in col for col in column_names):
            return 'log_data'
        elif any('security' in col or 'threat' in col or 'attack' in col for col in column_names):
            return 'security_data'
        else:
            return 'general_data'
    
    def _create_structured_record(self, row: pd.Series, index: int, sheet_name: str, 
                                data_type: str, file_path: Path) -> Dict[str, Any]:
        """
        Crea un record strutturato da una riga del DataFrame.
        
        Args:
            row: Riga del DataFrame
            index: Indice della riga
            sheet_name: Nome del foglio
            data_type: Tipo di dati
            file_path: Percorso del file
            
        Returns:
            Record strutturato
        """
        # Converti la riga in dizionario
        row_dict = row.to_dict()
        
        # Pulisci i valori
        cleaned_dict = {}
        for key, value in row_dict.items():
            if pd.isna(value):
                continue
            if isinstance(value, (int, float, str)):
                cleaned_dict[str(key)] = value
            else:
                cleaned_dict[str(key)] = str(value)
        
        # Crea record strutturato con dati direttamente (senza wrapper parsed_data)
        record = cleaned_dict
        
        return record
    
    def _extract_temporal_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estrae metadati temporali."""
        metadata = {}
        for key, value in data.items():
            if 'timestamp' in key.lower() or 'date' in key.lower() or 'time' in key.lower():
                metadata['temporal_field'] = key
                metadata['temporal_value'] = value
                break
        return metadata
    
    def _extract_network_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estrae metadati di rete."""
        metadata = {}
        for key, value in data.items():
            if 'ip' in key.lower() or 'address' in key.lower():
                metadata['network_field'] = key
                metadata['network_value'] = value
                break
        return metadata
    
    def _extract_security_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estrae metadati di sicurezza."""
        metadata = {}
        for key, value in data.items():
            if 'security' in key.lower() or 'threat' in key.lower() or 'attack' in key.lower():
                metadata['security_field'] = key
                metadata['security_value'] = value
                break
        return metadata 