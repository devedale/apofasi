"""
Analizzatore per template e outliers nei risultati di parsing.

Questo modulo fornisce analisi sui template ricorrenti nei log,
identificazione di outliers e pattern anomali per migliorare
la qualità del parsing e la comprensione dei dati.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import statistics
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.core import LoggerService


@dataclass
class TemplateAnalysis:
    """Analisi di un singolo template."""
    template_id: str
    frequency: int
    percentage: float
    sample_messages: List[str]
    avg_confidence: float
    is_outlier: bool
    parser_type: str
    common_fields: Dict[str, Any]
    field_variations: Dict[str, List[str]]


class TemplateAnalyzer:
    """
    Analizzatore per template e outliers nei risultati di parsing.
    
    WHY: Identifica pattern ricorrenti e anomalie nei log per
    migliorare la comprensione dei dati e la qualità del parsing.
    """
    
    def __init__(self, logger: Optional[LoggerService] = None):
        """
        Inizializza l'analizzatore di template.
        
        Args:
            logger: Servizio di logging opzionale
        """
        self.logger = logger or LoggerService()
    
    def analyze(self, results: List[Dict[str, Any]]) -> List[TemplateAnalysis]:
        """
        Analizza i risultati per identificare template e outliers.
        
        WHY: Identifica pattern ricorrenti per ottimizzare il parsing
        e rileva anomalie per migliorare la qualità dei dati.
        
        Args:
            results: Lista dei risultati parsati
            
        Returns:
            Lista di analisi dei template
        """
        if not results:
            self.logger.warning("Nessun risultato da analizzare per template")
            return []
        
        self.logger.info(f"Analizzando template per {len(results)} record")
        
        # Raggruppa per parser
        parser_groups = defaultdict(list)
        for result in results:
            if result.get('success', False):
                parser_name = result.get('parser_type', 'unknown')
                parser_groups[parser_name].append(result)
        
        template_analyses = []
        
        # Analizza template per ogni parser
        for parser_name, parser_results in parser_groups.items():
            parser_templates = self._analyze_parser_templates(parser_name, parser_results)
            template_analyses.extend(parser_templates)
        
        # Ordina per frequenza decrescente
        template_analyses.sort(key=lambda x: x.frequency, reverse=True)
        
        self.logger.info(f"Identificati {len(template_analyses)} template")
        
        return template_analyses
    
    def _analyze_parser_templates(self, parser_name: str, results: List[Dict[str, Any]]) -> List[TemplateAnalysis]:
        """
        Analizza i template per un singolo parser.
        
        Args:
            parser_name: Nome del parser
            results: Risultati del parser
            
        Returns:
            Lista di analisi dei template
        """
        # Estrai messaggi e strutture
        messages = []
        structures = []
        
        for result in results:
            message = result.get('message', '')
            structure = result.get('parsed_data', {})
            
            if message:
                messages.append(message)
            if structure:
                structures.append(structure)
        
        # Identifica template basati su struttura
        template_groups = self._group_by_structure(structures, messages)
        
        # Calcola statistiche per ogni template
        template_analyses = []
        total_records = len(results)
        
        for template_id, (structure, group_messages) in template_groups.items():
            frequency = len(group_messages)
            percentage = (frequency / total_records) * 100 if total_records > 0 else 0
            
            # Calcola confidence media per questo template
            template_results = [r for r in results if r.get('message', '') in group_messages]
            confidence_values = [r.get('confidence', 0.0) for r in template_results if r.get('confidence') is not None]
            avg_confidence = statistics.mean(confidence_values) if confidence_values else 0.0
            
            # Identifica se è un outlier
            is_outlier = self._is_outlier_template(frequency, total_records)
            
            # Analizza campi comuni
            common_fields = self._analyze_common_fields(template_results)
            field_variations = self._analyze_field_variations(template_results)
            
            # Sample messages (massimo 5)
            sample_messages = group_messages[:5]
            
            analysis = TemplateAnalysis(
                template_id=template_id,
                frequency=frequency,
                percentage=percentage,
                sample_messages=sample_messages,
                avg_confidence=avg_confidence,
                is_outlier=is_outlier,
                parser_type=parser_name,
                common_fields=common_fields,
                field_variations=field_variations
            )
            
            template_analyses.append(analysis)
        
        return template_analyses
    
    def _group_by_structure(self, structures: List[Dict], messages: List[str]) -> Dict[str, Tuple[Dict, List[str]]]:
        """
        Raggruppa risultati per struttura simile.
        
        Args:
            structures: Liste di strutture parsate
            messages: Liste di messaggi originali
            
        Returns:
            Dizionario template_id -> (struttura, messaggi)
        """
        template_groups = {}
        
        for i, (structure, message) in enumerate(zip(structures, messages)):
            # Crea una chiave per la struttura
            structure_key = self._create_structure_key(structure)
            
            if structure_key not in template_groups:
                template_groups[structure_key] = (structure, [])
            
            template_groups[structure_key][1].append(message)
        
        return template_groups
    
    def _create_structure_key(self, structure: Dict[str, Any]) -> str:
        """
        Crea una chiave unica per una struttura.
        
        Args:
            structure: Struttura parsata
            
        Returns:
            Chiave unica per la struttura
        """
        # Ordina le chiavi per consistenza
        sorted_keys = sorted(structure.keys())
        key_parts = []
        
        for key in sorted_keys:
            value = structure[key]
            # Normalizza il valore per il confronto
            if isinstance(value, (int, float)):
                key_parts.append(f"{key}:number")
            elif isinstance(value, str):
                # Categorizza stringhe per lunghezza
                if len(value) < 10:
                    key_parts.append(f"{key}:short")
                elif len(value) < 50:
                    key_parts.append(f"{key}:medium")
                else:
                    key_parts.append(f"{key}:long")
            else:
                key_parts.append(f"{key}:other")
        
        return "|".join(key_parts)
    
    def _is_outlier_template(self, frequency: int, total_records: int) -> bool:
        """
        Determina se un template è un outlier.
        
        Args:
            frequency: Frequenza del template
            total_records: Numero totale di record
            
        Returns:
            True se è un outlier
        """
        if total_records == 0:
            return False
        
        percentage = (frequency / total_records) * 100
        
        # Un template è un outlier se:
        # 1. Rappresenta meno del 1% dei record (troppo raro)
        # 2. Rappresenta più del 80% dei record (troppo comune)
        return percentage < 1.0 or percentage > 80.0
    
    def _analyze_common_fields(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analizza i campi comuni in un template.
        
        Args:
            results: Risultati per questo template
            
        Returns:
            Analisi dei campi comuni
        """
        field_analysis = {}
        
        for result in results:
            parsed_data = result.get('parsed_data', {})
            
            for field_name, field_value in parsed_data.items():
                if field_name not in field_analysis:
                    field_analysis[field_name] = {
                        'count': 0,
                        'types': set(),
                        'values': []
                    }
                
                field_analysis[field_name]['count'] += 1
                field_analysis[field_name]['types'].add(type(field_value).__name__)
                field_analysis[field_name]['values'].append(str(field_value))
        
        # Normalizza l'analisi
        for field_name, analysis in field_analysis.items():
            analysis['types'] = list(analysis['types'])
            # Limita i valori per evitare output troppo grandi
            analysis['values'] = analysis['values'][:10]
        
        return field_analysis
    
    def _analyze_field_variations(self, results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Analizza le variazioni nei valori dei campi.
        
        Args:
            results: Risultati per questo template
            
        Returns:
            Variazioni per campo
        """
        field_variations = defaultdict(set)
        
        for result in results:
            parsed_data = result.get('parsed_data', {})
            
            for field_name, field_value in parsed_data.items():
                field_variations[field_name].add(str(field_value))
        
        # Converti set in liste e limita
        return {
            field_name: list(values)[:20]  # Massimo 20 valori diversi
            for field_name, values in field_variations.items()
        } 