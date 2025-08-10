"""
Servizio per reportistiche e statistiche dettagliate (Versione Refactorizzata).

Questo servizio utilizza analizzatori specializzati per generare
report completi sui risultati di parsing, seguendo il principio
di Single Responsibility.

Author: Edoardo D'Alesio
Version: 2.0.0
"""

import json
import re
from datetime import datetime
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from src.core import LoggerService
from ...core.services.regex_service import RegexService
from .analyzers import (
    GeneralStatisticsAnalyzer, GeneralStatistics,
    ParserStatisticsAnalyzer, ParserStatistics,
    TemplateAnalyzer, TemplateAnalysis,
    AnonymizationAnalyzer, AnonymizationStats,
    IssuesAnalyzer, IssueAnalysis
)
from ...domain.services.timestamp_normalization_service import TimestampNormalizationService
from ...domain.services.unified_log_service import UnifiedLogService, UnifiedLogRecord
from ...domain.interfaces.unified_log_writer import UnifiedLogWriter
from ...infrastructure.unified.unified_log_writer_fs import UnifiedLogWriterFs
from ...domain.entities.parsed_record import ParsedRecord
from ...core.services.drain3_analyzer import Drain3Analyzer


class ReportingService:
    """
    Servizio per generare reportistiche e statistiche dettagliate.
    
    WHY: Utilizza analizzatori specializzati per mantenere il codice
    modulare e testabile, seguendo il principio di Single Responsibility.
    """
    
    def __init__(self, output_dir: Path, logger: Optional[LoggerService] = None, config: Optional[Dict[str, Any]] = None):
        """
        Inizializza il servizio di reporting.
        
        Args:
            output_dir: Directory di output
            logger: Servizio logger opzionale
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Inizializza servizi
        self.logger = logger or LoggerService()
        self.timestamp_normalizer = TimestampNormalizationService()
        self.unified_service = UnifiedLogService()
        self.drain3_analyzer = Drain3Analyzer()
        self.config = config or {}
        
        # Statistiche
        self.stats = {
            "total_files": 0,
            "total_records": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "processing_time": 0.0
        }
        
        # Inizializza analizzatori
        self.general_analyzer = GeneralStatisticsAnalyzer(self.logger)
        self.parser_analyzer = ParserStatisticsAnalyzer(self.logger)
        self.template_analyzer = TemplateAnalyzer(self.logger)
        self.anonymization_analyzer = AnonymizationAnalyzer(self.logger)
        self.issues_analyzer = IssuesAnalyzer(self.logger)
        
        # Inizializza servizio di normalizzazione temporale
        self.timestamp_normalizer = TimestampNormalizationService()
        
        # Inizializza writer unificato con DI (FS default)
        self.unified_writer: UnifiedLogWriter = UnifiedLogWriterFs(output_dir)
        
        # Inizializza RegexService centralizzato (singleton-like)
        self.regex_service = RegexService()
    
    def generate_comprehensive_report(self, parsed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un report completo con tutte le statistiche.
        
        WHY: Coordina tutti gli analizzatori per fornire una visione
        completa dei risultati di parsing.
        
        Args:
            parsed_results: Lista dei risultati parsati
            
        Returns:
            Report completo con statistiche
        """
        self.logger.info("🔍 Iniziando generazione report completo...")
        
        # Statistiche generali
        general_stats = self.general_analyzer.analyze(parsed_results)
        
        # Statistiche per parser
        parser_stats = self.parser_analyzer.analyze(parsed_results)
        
        # Analisi template e outliers
        template_analysis = self.template_analyzer.analyze(parsed_results)
        
        # Statistiche anonimizzazione
        anonymization_stats = self.anonymization_analyzer.analyze(parsed_results)
        
        # Problemi e warning
        issues_analysis = self.issues_analyzer.analyze(parsed_results)
        
        # Report completo
        comprehensive_report = {
            "report_generated_at": datetime.now().isoformat(),
            "total_records_processed": len(parsed_results),
            "general_statistics": self._convert_to_dict(general_stats),
            "parser_statistics": [self._convert_to_dict(stat) for stat in parser_stats],
            "template_analysis": [self._convert_to_dict(template) for template in template_analysis],
            "anonymization_statistics": self._convert_to_dict(anonymization_stats),
            "issues_analysis": self._convert_to_dict(issues_analysis),
            "recommendations": self._generate_recommendations(parser_stats, issues_analysis)
        }
        
        # Salva il report completo
        self._save_report(comprehensive_report, "comprehensive_report.json")
        
        # Genera solo il file unificato
        self._generate_unified_files(parsed_results)
        
        # Genera il file di anteprima JSON
        self._generate_samples_json_file(parsed_results)
        
        return comprehensive_report
    
    def generate_pure_data_files(self, parsed_results: List[Dict[str, Any]]):
        """
        Genera file di dati puri per analisi esterne.
        
        WHY: Fornisce dati strutturati per analisi con strumenti esterni
        come Excel, Python, R, etc.
        
        Args:
            parsed_results: Lista dei risultati parsati
        """
        self.logger.info("📊 Generando file di dati puri...")

        # Normalizza e riordina: mantieni tutto in chiaro e aggiungi solo 'anonymized_message'
        enriched_results: List[Dict[str, Any]] = []
        for item in parsed_results:
            if not isinstance(item, dict):
                continue
            normalized = self._normalize_output_record(item)
            enriched_results.append(normalized)

        # File JSON con tutti i dati (incluso messaggio anonimizzato)
        json_file = self.output_dir / "parsed_data.json"
        with open(json_file, 'w') as f:
            json.dump(enriched_results, f, indent=2)
        
        # File CSV per analisi
        csv_file = self.output_dir / "parsed_data.csv"
        self._save_as_csv(enriched_results, csv_file)
        
        # File di statistiche
        stats_file = self.output_dir / "statistics_summary.json"
        stats_data = {
            "total_records": len(enriched_results),
            "successful_parses": sum(1 for r in enriched_results if r.get('success', False)),
            "failed_parses": sum(1 for r in enriched_results if not r.get('success', False)),
            "parser_distribution": self._get_parser_distribution(enriched_results),
            "generated_at": datetime.now().isoformat()
        }
        with open(stats_file, 'w') as f:
            json.dump(stats_data, f, indent=2)
        
        self.logger.info(f"File generati: {json_file}, {csv_file}, {stats_file}")

    def _normalize_output_record(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rende l'output parsed_data.json più leggibile e coerente:
        - Mantiene parsed_data in chiaro (nessuna anonimizzazione)
        - Aggiunge solo 'anonymized_message'
        - Raggruppa informazioni Drain3 e parsing in sotto-sezioni
        - Evita ripetizioni di campi top-level sparsi
        """
        original = str(item.get('original_content', item.get('raw_line', '')))
        anonymized = self.regex_service.apply_patterns_by_category(original, 'anonymization')
        # Overlay di anonimizzazione per campi esplicitati in config (es. tz)
        anonym_cfg = (self.config.get('drain3', {}) or {}).get('anonymization', {}) or {}
        always_fields = set(anonym_cfg.get('always_anonymize', []) or [])
        parsed_data_local = item.get('parsed_data', {}) if isinstance(item.get('parsed_data'), dict) else {}
        if always_fields and isinstance(parsed_data_local, dict):
            for field in always_fields:
                if field in parsed_data_local and isinstance(parsed_data_local[field], str):
                    raw_val = parsed_data_local[field]
                    if raw_val:
                        # Se RegexService non cambia nulla, usa un placeholder generico per il campo
                        masked_val = self.regex_service.apply_patterns_by_category(raw_val, 'anonymization')
                        if masked_val == raw_val:
                            masked_val = f"<{field.upper()}>"
                        try:
                            anonymized = re.sub(re.escape(raw_val), masked_val, anonymized)
                        except re.error:
                            pass

        drain3 = OrderedDict()
        if 'drain3_cluster_id' in item:
            drain3['cluster_id'] = item.get('drain3_cluster_id')
        if 'drain3_template' in item:
            drain3['template'] = item.get('drain3_template')
        if 'cluster_size' in item:
            drain3['cluster_size'] = item.get('cluster_size')

        parsing = OrderedDict()
        # Aggiungi informazioni di parsing
        if 'parsing' in item:
            parsing = item['parsing']
            
            # Template originale (per compatibilità)
            if 'template' in item:
                parsing['template'] = item.get('template')
            
            # Template anonimizzato coerente (nuovo)
            if 'anonymized_template' in item:
                parsing['anonymized_template'] = item.get('anonymized_template')
            
            # Dati parsati originali
            if 'parsed_data' in item:
                parsing['data'] = item['parsed_data']
            
            # Dati parsati anonimizzati (se disponibili)
            if 'parsed_data_anonymized' in item:
                parsing['data_anonymized'] = item['parsed_data_anonymized']
            
            # Pattern rilevati
            if 'detected_patterns' in item:
                parsing['detected_patterns'] = item['detected_patterns']
            
            # Informazioni timestamp
            if 'timestamp_info' in item:
                parsing['timestamp_info'] = item['timestamp_info']
            
            # Template generato dal parser (per compatibilità)
            if 'parser_template' in item:
                parsing['parser_template'] = item.get('parser_template')

        # Metadati base, ordine amichevole
        out = OrderedDict()
        out['id'] = f"{item.get('source_file', 'unknown')}:{item.get('line_number', 1)}"
        out['source_file'] = item.get('source_file')
        out['line_number'] = item.get('line_number')
        out['parser_name'] = item.get('parser_name')
        out['timestamp'] = item.get('timestamp')

        # Messaggi
        out['original_content'] = original
        out['anonymized_message'] = anonymized

        # IMPORTANTE: Aggiungi i parsed_data direttamente per visibilità
        if 'parsed_data' in item and item['parsed_data']:
            out['parsed_data'] = item['parsed_data']

        # Sezioni raggruppate
        out['drain3'] = drain3
        out['parsing'] = parsing

        # Extra
        if 'success' in item:
            out['success'] = item.get('success')
        if 'confidence_score' in item:
            out['confidence_score'] = item.get('confidence_score')
        if 'processing_errors' in item:
            out['processing_errors'] = item.get('processing_errors')
        if 'processing_warnings' in item:
            out['processing_warnings'] = item.get('processing_warnings')

        return out

    def export_training_datasets(self, parsed_results: List[Dict[str, Any]]):
        """
        Esporta dataset di training per LogParser/LogPPT.

        - TSV: id, message, event, eventtemplate
        - JSON: [{log, template, parameters[]}]
        """
        # Costruisci ParsedRecord minimi dai risultati per riuso uniforme
        records: List[ParsedRecord] = []
        for result in parsed_results:
            if not isinstance(result, dict):
                continue
            if not result.get('success', False):
                continue
            # Caso A: risultato già "flat" (una singola riga parsata)
            if 'original_content' in result:
                file_path = Path(result.get('source_file', 'unknown'))
                original = result.get('original_content') or result.get('raw_line') or ''
                if original:
                    pr = ParsedRecord(
                        original_content=str(original),
                        parsed_data=result.get('parsed_data', {}) or {},
                        parser_name=result.get('parser_name', result.get('detected_format', 'unknown')),
                        source_file=file_path,
                        line_number=int(result.get('line_number', 1))
                    )
                    pr.drain3_cluster_id = result.get('drain3_cluster_id')
                    pr.drain3_template = result.get('drain3_template')
                    records.append(pr)
            # Caso B: risultato annidato (lista di record in result['parsed_data'])
            elif isinstance(result.get('parsed_data'), list):
                file_path = Path(result.get('file_path', 'unknown'))
                for rd in result.get('parsed_data', []):
                    if not isinstance(rd, dict):
                        continue
                    original = rd.get('original_content') or rd.get('raw_line') or ''
                    if not original:
                        continue
                    pr = ParsedRecord(
                        original_content=str(original),
                        parsed_data=rd,
                        parser_name=result.get('detected_format', 'unknown'),
                        source_file=file_path,
                        line_number=int(rd.get('line_number', 1))
                    )
                    pr.drain3_cluster_id = rd.get('drain3_cluster_id') or result.get('drain3_cluster_id')
                    pr.drain3_template = rd.get('drain3_template') or result.get('drain3_template')
                    records.append(pr)

        # TSV compat LogParser/LogPPT
        tsv_path = self.output_dir / 'training_logppt.tsv'
        with open(tsv_path, 'w', encoding='utf-8') as f:
            f.write('id\tmessage\tevent\teventtemplate\n')
            for rec in records:
                rid = f"{rec.source_file}:{rec.line_number}"
                message = rec.original_content.replace('\t', ' ').replace('\n', ' ')
                event = '' if rec.drain3_cluster_id is None else str(rec.drain3_cluster_id)
                tmpl = rec.drain3_template or ''
                f.write(f"{rid}\t{message}\t{event}\t{tmpl}\n")

        # JSON compat LogPPT (minimo: log, template, parameters)
        json_path = self.output_dir / 'training_logppt.json'
        json_items = [
            {
                'log': rec.original_content,
                'template': rec.drain3_template or '',
                'parameters': []
            }
            for rec in records
        ]
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_items, f, indent=2, ensure_ascii=False)

        self.logger.info(f"📦 Dataset training generati: {tsv_path}, {json_path}")

    def export_logppt_input_csv(self, parsed_results: List[Dict[str, Any]]):
        """
        Esporta un CSV compatibile con LogPPT per il parsing: colonna 'Content' con il messaggio originale.
        Output: '<dataset>_full.log_structured.csv' generico (dataset=clean_parser).
        """
        import csv
        csv_path = self.output_dir / 'clean_parser_full.log_structured.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(
                f,
                quoting=csv.QUOTE_MINIMAL,
                escapechar='\\',
                doublequote=True
            )
            writer.writerow(['Content'])
            for result in parsed_results:
                if not isinstance(result, dict) or not result.get('success', False):
                    continue
                # Flat
                if 'original_content' in result:
                    original = result.get('original_content') or result.get('raw_line') or ''
                    if original:
                        writer.writerow([original])
                # Nested
                elif isinstance(result.get('parsed_data'), list):
                    for rd in result.get('parsed_data', []):
                        if not isinstance(rd, dict):
                            continue
                        original = rd.get('original_content') or rd.get('raw_line') or ''
                        if original:
                            writer.writerow([original])
        self.logger.info(f"📝 CSV LogPPT input generato: {csv_path}")

    def export_drain3_dump(self, parsed_results: List[Dict[str, Any]]):
        """
        Esporta un dump completo di cluster/template Drain3 derivati dai risultati.
        Supporta ora il dual mining: messaggi originali e anonimizzati.
        """
        # Cluster separati per miner originale e anonimizzato
        original_clusters: Dict[str, Dict[str, Any]] = {}
        anonymized_clusters: Dict[str, Dict[str, Any]] = {}

        def add_cluster_entry(cid: Any, tmpl: Any, original: str, file_path: str, miner_type: str):
            if cid is None:
                return
            
            # Seleziona il dizionario appropriato
            clusters_dict = original_clusters if miner_type == "original" else anonymized_clusters
            
            key = f"{miner_type}_{cid}"
            entry = clusters_dict.setdefault(key, {
                'cluster_id': cid,
                'template': (tmpl or ''),
                'size': 0,
                'examples': [],
                'files': {},
                'miner_type': miner_type
            })
            entry['size'] += 1
            if original and len(entry['examples']) < 3:
                entry['examples'].append(original)
            entry['files'][file_path] = entry['files'].get(file_path, 0) + 1

        for result in parsed_results:
            if not isinstance(result, dict) or not result.get('success', False):
                continue
            file_path = result.get('file_path') or result.get('source_file') or 'unknown'

            # Caso flat (record singolo)
            if 'original_content' in result:
                # Cluster originale (compatibilità)
                cid = result.get('drain3_cluster_id')
                tmpl = result.get('drain3_template')
                original = result.get('original_content') or result.get('raw_line') or ''
                if cid is not None:
                    add_cluster_entry(cid, tmpl, original, file_path, "original")
                
                # Nuovi cluster dual mining
                pdata = result.get('parsed_data', {})
                if isinstance(pdata, dict):
                    # Cluster originale dal nuovo formato
                    if 'drain3_original' in pdata:
                        orig_data = pdata['drain3_original']
                        add_cluster_entry(
                            orig_data.get('cluster_id'), 
                            orig_data.get('template'), 
                            original, 
                            file_path, 
                            "original"
                        )
                    
                    # Cluster anonimizzato dal nuovo formato
                    if 'drain3_anonymized' in pdata:
                        anon_data = pdata['drain3_anonymized']
                        add_cluster_entry(
                            anon_data.get('cluster_id'), 
                            anon_data.get('template'), 
                            original, 
                            file_path, 
                            "anonymized"
                        )

            pdata = result.get('parsed_data')
            # Lista di record
            if isinstance(pdata, list):
                for rd in pdata:
                    if not isinstance(rd, dict):
                        continue
                    
                    # Cluster originale (compatibilità)
                    cid = rd.get('drain3_cluster_id') or result.get('drain3_cluster_id')
                    tmpl = rd.get('drain3_template') or result.get('drain3_template')
                    original = rd.get('original_content') or rd.get('raw_line') or ''
                    if cid is not None:
                        add_cluster_entry(cid, tmpl, original, file_path, "original")
                    
                    # Nuovi cluster dual mining
                    if 'drain3_original' in rd:
                        orig_data = rd['drain3_original']
                        add_cluster_entry(
                            orig_data.get('cluster_id'), 
                            orig_data.get('template'), 
                            original, 
                            file_path, 
                            "original"
                        )
                    
                    if 'drain3_anonymized' in rd:
                        anon_data = rd['drain3_anonymized']
                        add_cluster_entry(
                            anon_data.get('cluster_id'), 
                            anon_data.get('template'), 
                            original, 
                            file_path, 
                            "anonymized"
                        )
            
            # Dizionario singolo
            elif isinstance(pdata, dict):
                # Cluster originale (compatibilità)
                cid = pdata.get('drain3_cluster_id') or result.get('drain3_cluster_id')
                tmpl = pdata.get('drain3_template') or result.get('drain3_template')
                original = pdata.get('original_content') or pdata.get('raw_line') or result.get('original_content') or ''
                if cid is not None:
                    add_cluster_entry(cid, tmpl, original, file_path, "original")
                
                # Nuovi cluster dual mining
                if 'drain3_original' in pdata:
                    orig_data = pdata['drain3_original']
                    add_cluster_entry(
                        orig_data.get('cluster_id'), 
                        orig_data.get('template'), 
                        original, 
                        file_path, 
                        "original"
                    )
                
                if 'drain3_anonymized' in pdata:
                    anon_data = pdata['drain3_anonymized']
                    add_cluster_entry(
                        anon_data.get('cluster_id'), 
                        anon_data.get('template'), 
                        original, 
                        file_path, 
                        "anonymized"
                    )

        # Genera dump separati per ogni tipo di miner
        dump_data = {
            'summary': {
                'total_original_clusters': len(original_clusters),
                'total_anonymized_clusters': len(anonymized_clusters),
                'total_clusters': len(original_clusters) + len(anonymized_clusters)
            },
            'original_clusters': list(original_clusters.values()),
            'anonymized_clusters': list(anonymized_clusters.values())
        }
        
        # Dump completo combinato
        dump_path = self.output_dir / 'drain3_full.json'
        with open(dump_path, 'w', encoding='utf-8') as f:
            json.dump(dump_data, f, indent=2, ensure_ascii=False)
        
        # Dump separati per analisi specifiche
        original_dump_path = self.output_dir / 'drain3_original.json'
        with open(original_dump_path, 'w', encoding='utf-8') as f:
            json.dump({
                'clusters': list(original_clusters.values()),
                'summary': {'total_clusters': len(original_clusters)}
            }, f, indent=2, ensure_ascii=False)
        
        anonymized_dump_path = self.output_dir / 'drain3_anonymized.json'
        with open(anonymized_dump_path, 'w', encoding='utf-8') as f:
            json.dump({
                'clusters': list(anonymized_clusters.values()),
                'summary': {'total_clusters': len(anonymized_clusters)}
            }, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"🧩 Drain3 dual mining dump generato:")
        self.logger.info(f"   - Completo: {dump_path}")
        self.logger.info(f"   - Originale: {original_dump_path} ({len(original_clusters)} cluster)")
        self.logger.info(f"   - Anonimizzato: {anonymized_dump_path} ({len(anonymized_clusters)} cluster)")
    
    def generate_anonymized_data(self, parsed_results: List[Dict[str, Any]]):
        """
        Genera file di dati anonimizzati.
        
        WHY: Fornisce dati privi di informazioni sensibili per analisi
        e condivisione sicura.
        
        Args:
            parsed_results: Lista dei risultati parsati
        """
        self.logger.info("🔒 Generando dati anonimizzati...")
        
        anonymized_data = []
        for result in parsed_results:
            if result.get('success', False) and 'parsed_data' in result:
                for record in result['parsed_data']:
                    anonymized_record = self._anonymize_record(record)
                    anonymized_record['source_file'] = result.get('file_path', 'unknown')
                    anonymized_data.append(anonymized_record)
        
        # Salva file anonimizzato
        anonymized_file = self.output_dir / "anonymized_data.json"
        with open(anonymized_file, 'w') as f:
            json.dump(anonymized_data, f, indent=2)
        
        # CSV anonimizzato
        anonymized_csv = self.output_dir / "anonymized_data.csv"
        self._save_as_csv(anonymized_data, anonymized_csv)
        
        self.logger.info(f"Dati anonimizzati generati: {anonymized_file}, {anonymized_csv}")
    
    def generate_combined_data(self, parsed_results: List[Dict[str, Any]]):
        """
        Genera file di dati combinati da tutti i parser.
        
        WHY: Fornisce una vista unificata di tutti i dati parsati
        per analisi cross-format.
        
        Args:
            parsed_results: Lista dei risultati parsati
        """
        self.logger.info("🔗 Generando dati combinati...")
        
        combined_data = []
        for result in parsed_results:
            if result.get('success', False) and 'parsed_data' in result:
                for record in result['parsed_data']:
                    combined_record = record.copy()
                    combined_record['source_file'] = result.get('file_path', 'unknown')
                    combined_record['parser_type'] = result.get('detected_format', 'unknown')
                    combined_record['parsing_success'] = result.get('success', False)
                    combined_data.append(combined_record)
        
        # Salva file combinato
        combined_file = self.output_dir / "combined_data.json"
        with open(combined_file, 'w') as f:
            json.dump(combined_data, f, indent=2)
        
        # CSV combinato
        combined_csv = self.output_dir / "combined_data.csv"
        self._save_as_csv(combined_data, combined_csv)
        
        self.logger.info(f"Dati combinati generati: {combined_file}, {combined_csv}")
    
    def generate_temporal_organized_data(self, parsed_results: List[Dict[str, Any]]):
        """
        Genera file di dati organizzati temporalmente.
        
        WHY: Fornisce dati ordinati cronologicamente per analisi temporale
        sia per dati anonimizzati che non anonimizzati.
        
        Args:
            parsed_results: Lista dei risultati parsati
        """
        self.logger.info("🕐 Generando dati organizzati temporalmente...")
        
        # Estrai tutti i record parsati
        all_records = []
        for result in parsed_results:
            if result.get('success', False) and 'parsed_data' in result:
                for record in result['parsed_data']:
                    # Aggiungi metadati del file
                    record_with_metadata = record.copy()
                    record_with_metadata['source_file'] = result.get('file_path', 'unknown')
                    record_with_metadata['parser_type'] = result.get('detected_format', 'unknown')
                    record_with_metadata['parsing_success'] = result.get('success', False)
                    all_records.append(record_with_metadata)
        
        if not all_records:
            self.logger.warning("Nessun record da organizzare temporalmente")
            return
        
        # Normalizza timestamp per tutti i record (ottimizzato per file grandi)
        self.logger.info(f"Normalizzando timestamp per {len(all_records)} record...")
        normalized_records = []
        
        # Processa in batch per migliorare le performance
        batch_size = 1000
        for i in range(0, len(all_records), batch_size):
            batch = all_records[i:i + batch_size]
            self.logger.info(f"Processando batch {i//batch_size + 1}/{(len(all_records) + batch_size - 1)//batch_size} ({len(batch)} record)")
            
            for record in batch:
                # Rimuovi parsed_at per evitare confusione con timestamp originali
                record_for_normalization = record.copy()
                if 'parsed_at' in record_for_normalization:
                    del record_for_normalization['parsed_at']
                
                # Crea un ParsedRecord temporaneo per la normalizzazione
                original_content = str(record.get('raw_line', record.get('original_content', '')))
                if not original_content.strip():
                    original_content = f"Record from {record.get('source_file', 'unknown')}:{record.get('line_number', 1)}"
                
                temp_record = ParsedRecord(
                    original_content=original_content,
                    parsed_data=record_for_normalization,
                    parser_name=record.get('parser_type', 'unknown'),
                    source_file=Path(record.get('source_file', 'unknown')),
                    line_number=record.get('line_number', 1)
                )
                
                # Normalizza il timestamp
                normalized_temp_record = self.timestamp_normalizer.normalize_parsed_record(temp_record)
                
                # Aggiorna il record originale con il timestamp normalizzato
                if normalized_temp_record.timestamp:
                    record['normalized_timestamp'] = normalized_temp_record.timestamp.isoformat()
                else:
                    record['normalized_timestamp'] = None
                record['timestamp_confidence'] = normalized_temp_record.parsed_data.get('timestamp_info', {}).get('confidence', 0.0)
                record['timestamp_source'] = normalized_temp_record.parsed_data.get('timestamp_info', {}).get('source', 'unknown')
                
                normalized_records.append(record)
        
        # Ordina per timestamp normalizzato (ottimizzato per file grandi)
        self.logger.info("Ordinando record per timestamp...")
        
        # Crea ParsedRecord solo per quelli con timestamp per ridurre memoria
        records_with_timestamp = []
        records_without_timestamp = []
        
        for r in normalized_records:
            if r.get('normalized_timestamp'):
                try:
                    timestamp = datetime.fromisoformat(r['normalized_timestamp'])
                    original_content = str(r.get('raw_line', r.get('original_content', '')))
                    if not original_content.strip():
                        original_content = f"Record from {r.get('source_file', 'unknown')}:{r.get('line_number', 1)}"
                    
                    records_with_timestamp.append(ParsedRecord(
                        original_content=original_content,
                        parsed_data=r,
                        parser_name=r.get('parser_type', 'unknown'),
                        source_file=Path(r.get('source_file', 'unknown')),
                        line_number=r.get('line_number', 1),
                        timestamp=timestamp
                    ))
                except (ValueError, TypeError):
                    # Se il timestamp non è valido, mettilo con quelli senza timestamp
                    records_without_timestamp.append(r)
            else:
                records_without_timestamp.append(r)
        
        # Ordina solo quelli con timestamp
        if records_with_timestamp:
            sorted_records_with_timestamp = self.timestamp_normalizer.sort_records_by_timestamp(records_with_timestamp)
            # Converti di nuovo in dizionari
            sorted_data = []
            for record in sorted_records_with_timestamp:
                data_dict = record.parsed_data.copy()
                data_dict['normalized_timestamp'] = record.timestamp.isoformat() if record.timestamp else None
                sorted_data.append(data_dict)
            
            # Aggiungi quelli senza timestamp alla fine
            sorted_data.extend(records_without_timestamp)
        else:
            # Nessun record con timestamp, mantieni l'ordine originale
            sorted_data = normalized_records
        

        
        # Genera file temporali non anonimizzati
        temporal_file = self.output_dir / "temporal_data.json"
        with open(temporal_file, 'w') as f:
            json.dump(sorted_data, f, indent=2)
        
        temporal_csv = self.output_dir / "temporal_data.csv"
        self._save_as_csv(sorted_data, temporal_csv)
        
        # Genera file temporali anonimizzati
        anonymized_temporal_data = []
        for record in sorted_data:
            anonymized_record = self._anonymize_record(record)
            anonymized_temporal_data.append(anonymized_record)
        
        anonymized_temporal_file = self.output_dir / "temporal_data_anonymized.json"
        with open(anonymized_temporal_file, 'w') as f:
            json.dump(anonymized_temporal_data, f, indent=2)
        
        anonymized_temporal_csv = self.output_dir / "temporal_data_anonymized.csv"
        self._save_as_csv(anonymized_temporal_data, anonymized_temporal_csv)
        
        # Genera statistiche temporali
        # Crea ParsedRecord per le statistiche
        stats_records = []
        for record in sorted_data:
            if record.get('normalized_timestamp'):
                try:
                    timestamp = datetime.fromisoformat(record['normalized_timestamp'])
                    stats_records.append(ParsedRecord(
                        original_content=str(record.get('raw_line', '')),
                        parsed_data=record,
                        parser_name=record.get('parser_type', 'unknown'),
                        source_file=Path(record.get('source_file', 'unknown')),
                        line_number=record.get('line_number', 1),
                        timestamp=timestamp
                    ))
                except (ValueError, TypeError):
                    pass
        
        timeline_stats = self.timestamp_normalizer.get_timeline_statistics(stats_records)
        timeline_stats_file = self.output_dir / "temporal_statistics.json"
        with open(timeline_stats_file, 'w') as f:
            json.dump(timeline_stats, f, indent=2)
        
        self.logger.info(f"Dati temporali generati:")
        self.logger.info(f"  📊 Non anonimizzati: {temporal_file}, {temporal_csv}")
        self.logger.info(f"  🔒 Anonimizzati: {anonymized_temporal_file}, {anonymized_temporal_csv}")
        self.logger.info(f"  📈 Statistiche: {timeline_stats_file}")
        
        # Stampa statistiche temporali
        self._print_temporal_statistics(timeline_stats)
    
    def _print_temporal_statistics(self, stats: Dict[str, Any]):
        """
        Stampa statistiche temporali.
        
        Args:
            stats: Statistiche temporali
        """
        print("\n🕐 STATISTICHE TEMPORALI")
        print("=" * 40)
        print(f"📝 Total records: {stats.get('total_records', 0)}")
        print(f"⏰ Records with timestamp: {stats.get('records_with_timestamp', 0)}")
        print(f"📈 Timestamp coverage: {stats.get('timestamp_coverage', 0.0):.1%}")
        print(f"🎯 Average confidence: {stats.get('average_confidence', 0.0):.2f}")
        
        if stats.get('time_span'):
            time_span = stats['time_span']
            print(f"⏱️  Time span: {time_span.get('start', 'N/A')} to {time_span.get('end', 'N/A')}")
            print(f"⏱️  Duration: {time_span.get('duration_seconds', 0):.1f} seconds")
    
    def generate_unparsed_data(self, parsed_results: List[Dict[str, Any]]):
        """
        Genera file con dati non parsati.
        
        WHY: Fornisce visibilità sui dati che non sono stati
        parsati correttamente per debugging e miglioramento.
        
        Args:
            parsed_results: Lista dei risultati parsati
        """
        self.logger.info("❌ Generando dati non parsati...")
        
        unparsed_data = []
        for result in parsed_results:
            if not result.get('success', False):
                unparsed_record = {
                    'file_path': result.get('file_path', 'unknown'),
                    'parser_type': result.get('detected_format', 'unknown'),
                    'error': result.get('error', 'Unknown error'),
                    'file_size': result.get('file_size', 0),
                    'duration': result.get('duration', 0.0)
                }
                unparsed_data.append(unparsed_record)
        
        if unparsed_data:
            # Salva file non parsati
            unparsed_file = self.output_dir / "unparsed_data.json"
            with open(unparsed_file, 'w') as f:
                json.dump(unparsed_data, f, indent=2)
            
            # CSV non parsati
            unparsed_csv = self.output_dir / "unparsed_data.csv"
            self._save_as_csv(unparsed_data, unparsed_csv)
            
            self.logger.info(f"Dati non parsati generati: {unparsed_file}, {unparsed_csv}")
        else:
            self.logger.info("Nessun dato non parsato da salvare")
    
    def _anonymize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonimizza un record rimuovendo dati sensibili.
        
        Args:
            record: Record da anonimizzare
            
        Returns:
            Record anonimizzato
        """
        anonymized = record.copy()
        
        # Pattern per dati sensibili
        # Applica anonimizzazione centralizzata tramite RegexService
        for key, value in anonymized.items():
            if isinstance(value, str):
                anonymized[key] = self.regex_service.apply_patterns_by_category(value, 'anonymization')
        
        return anonymized
    
    def _convert_to_dict(self, obj: Any) -> Dict[str, Any]:
        """
        Converte un oggetto dataclass in dizionario.
        
        Args:
            obj: Oggetto da convertire
            
        Returns:
            Dizionario rappresentazione dell'oggetto
        """
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, '_asdict'):
            return obj._asdict()
        else:
            return dict(obj)
    
    def _generate_recommendations(self, parser_stats: List[ParserStatistics], 
                                issues_analysis: IssueAnalysis) -> List[str]:
        """
        Genera raccomandazioni basate sui risultati.
        
        Args:
            parser_stats: Statistiche dei parser
            issues_analysis: Analisi dei problemi
            
        Returns:
            Lista di raccomandazioni
        """
        recommendations = []
        
        # Raccomandazioni basate sui parser
        for stat in parser_stats:
            if stat.success_rate < 80.0:
                recommendations.append(f"Migliorare il parser {stat.parser_name} (success rate: {stat.success_rate:.1f}%)")
            
            if stat.avg_processing_time > 1.0:  # Più di 1 secondo
                recommendations.append(f"Ottimizzare performance del parser {stat.parser_name}")
        
        # Raccomandazioni basate sui problemi
        if issues_analysis.critical_issues > 0:
            recommendations.append(f"Risolvere {issues_analysis.critical_issues} problemi critici")
        
        if issues_analysis.total_issues > len(parser_stats) * 10:
            recommendations.append("Considerare una revisione completa del sistema di parsing")
        
        return recommendations
    
    def _save_report(self, report: Dict[str, Any], filename: str):
        """
        Salva il report su file.
        
        Args:
            report: Report da salvare
            filename: Nome del file
        """
        file_path = self.output_dir / filename
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Report salvato: {file_path}")
    
    def _print_summary(self, report: Dict[str, Any]):
        """
        Stampa un summary del report.
        
        Args:
            report: Report completo
        """
        print("\n" + "=" * 60)
        print("📊 REPORT COMPLETO GENERATO")
        print("=" * 60)
        
        general_stats = report['general_statistics']
        print(f"📄 Record processati: {report['total_records_processed']}")
        print(f"✅ Successi: {general_stats['successful_parses']}")
        print(f"❌ Fallimenti: {general_stats['failed_parses']}")
        print(f"📈 Success Rate: {general_stats['success_rate']:.1f}%")
        
        parser_stats = report['parser_statistics']
        print(f"🔧 Parser utilizzati: {len(parser_stats)}")
        
        template_analysis = report['template_analysis']
        print(f"📋 Template identificati: {len(template_analysis)}")
        
        anonymization_stats = report['anonymization_statistics']
        print(f"🔒 Record anonimizzati: {anonymization_stats['total_anonymized']}")
        
        issues_analysis = report['issues_analysis']
        print(f"⚠️  Problemi totali: {issues_analysis['total_issues']}")
        print(f"🚨 Problemi critici: {issues_analysis['critical_issues']}")
        
        recommendations = report['recommendations']
        if recommendations:
            print(f"\n💡 Raccomandazioni ({len(recommendations)}):")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        print(f"\n💾 Report salvato in: {self.output_dir}")
        print("=" * 60)
    
    def _generate_samples_json_file(self, parsed_results: List[Dict[str, Any]], max_content_length: int = 4096):
        """
        Genera un file JSON con un campione filtrato dei primi 3 record
        per ogni file sorgente, con controllo sulla lunghezza del contenuto.

        WHY: Utilizza un approccio map/filter/reduce per creare un output
        strutturato e pulito, ideale per un'analisi rapida e programmatica.
        Evita contenuti eccessivamente lunghi per mantenere la leggibilità.
        
        Args:
            parsed_results: Lista dei risultati parsati.
            max_content_length: Lunghezza massima per 'original_content'.
        """
        self.logger.info("📄 Generando file JSON di anteprima dei record...")

        # 1. Group by (Reduce-like): Raggruppa i record per file sorgente.
        records_by_file = defaultdict(list)
        for record in parsed_results:
            records_by_file[record.get('source_file', 'unknown_file')].append(record)

        final_samples = {}
        
        # 2. Filter & Map: Itera su ogni file, filtra i primi 3 record e mappali in un formato pulito.
        for source_file, records in records_by_file.items():
            # 2a. Filter/Slice: Prendi i primi 3 record
            samples = records[:3]
            
            # 2b. Map: Trasforma ogni record in un dizionario filtrato
            mapped_samples = []
            for r in samples:
                original_content = r.get('original_content', '')
                processing_errors = r.get('processing_errors', [])

                # Controlla la lunghezza del contenuto
                if len(original_content) > max_content_length:
                    content_to_display = "CONTENUTO_TROPPO_LUNGO_OMESSO"
                    if "Contenuto troppo lungo" not in processing_errors:
                         processing_errors.append(f"Contenuto troppo lungo (>{max_content_length} caratteri), omesso dall'anteprima.")
                else:
                    content_to_display = original_content

                mapped_samples.append({
                    "line_number": r.get('line_number'),
                    "success": r.get('success'),
                    "parser_name": r.get('parser_name'),
                    "original_content": content_to_display,
                    "parsed_data": r.get('parsed_data'),
                    "processing_errors": processing_errors
                })
            
            final_samples[source_file] = mapped_samples

        # Salva l'output JSON
        self._save_report(final_samples, "parsing_samples.json")
        self.logger.info(f"File JSON di anteprima generato: outputs/parsing_samples.json")

    def _save_as_csv(self, data: List[Dict[str, Any]], file_path: Path):
        """
        Salva i dati in formato CSV.
        
        Args:
            data: Dati da salvare
            file_path: Percorso del file CSV
        """
        if not data:
            return
        
        # Ottieni tutte le chiavi possibili
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())
        
        # Ordina le chiavi per consistenza
        sorted_keys = sorted(all_keys)
        
        with open(file_path, 'w', newline='') as f:
            # Header
            f.write(','.join(sorted_keys) + '\n')
            
            # Dati
            for item in data:
                row = []
                for key in sorted_keys:
                    value = item.get(key, '')
                    # Escape virgole e virgolette
                    if isinstance(value, str) and (',' in value or '"' in value):
                        escaped_value = value.replace('"', '""')
                        value = f'"{escaped_value}"'
                    row.append(str(value))
                f.write(','.join(row) + '\n')
    
    def _get_parser_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Ottiene la distribuzione dei parser.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Distribuzione parser -> conteggio
        """
        from collections import Counter
        parser_counter = Counter(r.get('parser_type', 'unknown') for r in results)
        return dict(parser_counter)
    
    def _generate_unified_files(self, parsed_results: List[Dict[str, Any]]):
        """
        Genera file JSON unificati utilizzando UnifiedLogGenerator.
        
        Args:
            parsed_results: Lista dei risultati parsati
        """
        self.logger.info("🔄 Generando file unificati con UnifiedLogGenerator...")
        
        # Converti i risultati in ParsedRecord
        parsed_records = []
        for result in parsed_results:
            if result.get('success', False):
                records_data = result.get('parsed_data', [])
                for record_data in records_data:
                    if not isinstance(record_data, dict):
                        continue
                        
                    original_content = record_data.get('original_content', 
                                                     record_data.get('raw_line', ''))
                    
                    if not original_content:
                        continue

                    record = ParsedRecord(
                        original_content=original_content,
                        parsed_data=record_data,
                        parser_name=result.get('detected_format', 'unknown'),
                        source_file=Path(result.get('file_path', 'unknown')),
                        line_number=record_data.get('line_number', 1)
                    )
                    parsed_records.append(record)
        
        # Genera i file unificati
        if parsed_records:
            self.unified_writer.write_unified_files(parsed_records, self.output_dir)
            self.logger.info("✅ File unificati generati con successo")
        else:
            self.logger.warning("⚠️ Nessun record valido per generare file unificati") 