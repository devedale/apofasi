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
from ...domain.interfaces.centralized_regex_service import CentralizedRegexService


class ReportingService:
    """
    Servizio per generare reportistiche e statistiche dettagliate.
    
    WHY: Utilizza analizzatori specializzati per mantenere il codice
    modulare e testabile, seguendo il principio di Single Responsibility.
    """
    
    def __init__(self, output_dir: Path, logger: Optional[LoggerService] = None, 
                 config: Optional[Dict[str, Any]] = None, 
                 centralized_regex_service: Optional[CentralizedRegexService] = None):
        """
        Inizializza il servizio di reporting.
        
        Args:
            output_dir: Directory di output
            logger: Servizio logger opzionale
            config: Configurazione opzionale
            centralized_regex_service: Servizio regex centralizzato opzionale
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Inizializza servizi
        self.logger = logger or LoggerService()
        self.timestamp_normalizer = TimestampNormalizationService()
        self.unified_service = UnifiedLogService()
        self.drain3_analyzer = Drain3Analyzer()
        self.config = config or {}
        self.centralized_regex_service = centralized_regex_service
        
        # WHY: Cache globale per configurazioni costose - caricata una sola volta
        from ...core.services.config_cache import ConfigCache
        self._config_cache = ConfigCache()
        self._cached_always_fields = self._config_cache.get_always_anonymize_fields()
        
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
        
        # WHY: Usa centralized_regex_service se disponibile, altrimenti fallback a RegexService
        if centralized_regex_service:
            self.regex_service = centralized_regex_service
        else:
            # Fallback per compatibilità
            from ...core.services.regex_service import RegexService
            self.regex_service = RegexService(config)
    
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
        come Excel, Python, R, etc. Ottimizzato per grandi dataset con processing batch globale.
        
        DESIGN: Processing batch globale che:
        1. Analizza tutto il dataset per identificare pattern
        2. Raggruppa record simili per processing ottimizzato
        3. Applica operazioni in batch per massimizzare efficienza
        4. Gestisce file con header simili per riutilizzo cache
        
        Args:
            parsed_results: Lista dei risultati parsati
        """
        self.logger.info("📊 Generando file di dati puri...")

        total_items = len(parsed_results)
        print(f"🔄 Processando COMPLETO del dataset: {total_items} record per file di dati puri...")
        
        # 1. ANALISI COMPLETA DEL DATASET
        print("📊 Analizzando struttura del dataset per ottimizzazione...")
        dataset_analysis = self._analyze_dataset_for_batch_processing(parsed_results)
        print(f"   📁 File totali: {dataset_analysis['total_files']}")
        print(f"   🔗 Gruppi di similarità: {dataset_analysis['similarity_groups']}")
        print(f"   📝 Record con contenuto: {dataset_analysis['records_with_content']}")
        
        # 2. PROCESSING BATCH GLOBALE OTTIMIZZATO
        print("🚀 Avviando processing batch globale del dataset...")
        
        if total_items > 10000:  # Per dataset grandi usa processing batch globale
            print("🚀 Dataset grande rilevato, usando processing batch globale ottimizzato...")
            enriched_results = self._process_dataset_in_global_batches(parsed_results, dataset_analysis)
        else:
            # Per dataset piccoli usa il metodo originale
            print("📦 Dataset piccolo, usando processing sequenziale...")
            enriched_results = self._process_records_sequentially(parsed_results)

        # 3. SALVATAGGIO OTTIMIZZATO
        print(f"💾 Salvando {len(enriched_results)} record processati...")
        
        # File JSON con tutti i dati (incluso messaggio anonimizzato)
        json_file = self.output_dir / "parsed_data.json"
        print(f"💾 Salvando JSON in {json_file}...")
        with open(json_file, 'w') as f:
            json.dump(enriched_results, f, indent=2)
        
        # File CSV per analisi
        csv_file = self.output_dir / "parsed_data.csv"
        print(f"💾 Salvando CSV in {csv_file}...")
        self._save_as_csv(enriched_results, csv_file)
        
        # File di statistiche
        stats_file = self.output_dir / "statistics_summary.json"
        stats_data = {
            "total_records": len(enriched_results),
            "successful_parses": sum(1 for r in enriched_results if r.get('success', False)),
            "failed_parses": sum(1 for r in enriched_results if not r.get('success', False)),
            "parser_distribution": self._get_parser_distribution(enriched_results),
            "batch_processing_stats": dataset_analysis,
            "generated_at": datetime.now().isoformat()
        }
        with open(stats_file, 'w') as f:
            json.dump(stats_data, f, indent=2)
        
        self.logger.info(f"File generati: {json_file}, {csv_file}, {stats_file}")
        print(f"🎉 Processing batch globale completato: {len(enriched_results)} record salvati")
    
    def _analyze_dataset_for_batch_processing(self, parsed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analizza il dataset completo per ottimizzare il processing batch.
        
        WHY: Identifica pattern e similarità per raggruppare record simili
        e massimizzare l'efficienza del processing batch.
        
        Returns:
            Analisi del dataset per ottimizzazione
        """
        # Analisi file
        total_files = len(set(r.get('source_file', 'unknown') for r in parsed_results))
        
        # Analisi contenuto
        records_with_content = sum(1 for r in parsed_results if r.get('original_content') and r.get('original_content').strip())
        
        # Analisi parser
        parser_distribution = {}
        for record in parsed_results:
            parser = record.get('parser_name', 'unknown')
            parser_distribution[parser] = parser_distribution.get(parser, 0) + 1
        
        # Analisi estensioni file
        file_extensions = set()
        for record in parsed_results:
            source_file = record.get('source_file', '')
            if source_file:
                file_extensions.add(Path(source_file).suffix.lower())
        
        # Stima gruppi di similarità
        similarity_groups = len(file_extensions) + 1  # +1 per file senza estensione
        
        return {
            'total_files': total_files,
            'similarity_groups': similarity_groups,
            'records_with_content': records_with_content,
            'file_extensions': list(file_extensions),
            'parser_distribution': parser_distribution,
            'total_records': len(parsed_results)
        }
    
    def _process_dataset_in_global_batches(self, parsed_results: List[Dict[str, Any]], dataset_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processa tutto il dataset in batch globali ottimizzati.
        
        WHY: Processing batch globale che raggruppa record simili per
        massimizzare l'efficienza e ridurre operazioni ripetute.
        
        Args:
            parsed_results: Lista dei risultati parsati
            dataset_analysis: Analisi del dataset per ottimizzazione
            
        Returns:
            Lista dei record processati
        """
        print("🔗 Creando batch globali ottimizzati...")
        
        # 1. RAGGRUPPAMENTO PER SIMILARITÀ
        # Raggruppa per estensione file e parser per ottimizzare cache
        grouped_records = self._group_records_by_similarity(parsed_results)
        
        # 2. CREAZIONE BATCH OTTIMIZZATI
        processing_batches = self._create_global_processing_batches(grouped_records)
        
        print(f"🎯 Creati {len(processing_batches)} batch globali ottimizzati")
        
        # 3. PROCESSING BATCH GLOBALE
        enriched_results = []
        total_batches = len(processing_batches)
        
        for batch_id, batch in enumerate(processing_batches, 1):
            batch_size = len(batch['records'])
            print(f"🔄 Processing batch globale {batch_id}/{total_batches}: {batch_size} record da {len(batch['files'])} file simili...")
            
            # Processa il batch globale
            batch_results = self._process_global_batch(batch)
            enriched_results.extend(batch_results)
            
            print(f"✅ Batch globale {batch_id} completato: {len(batch_results)} record processati")
        
        return enriched_results
    
    def _group_records_by_similarity(self, parsed_results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Raggruppa record per similarità per ottimizzare il processing.
        
        WHY: Raggruppa record simili per condividere cache e operazioni.
        
        Returns:
            Dizionario gruppo -> lista record
        """
        grouped = {}
        
        for record in parsed_results:
            # Crea chiave di raggruppamento basata su estensione e parser
            source_file = record.get('source_file', 'unknown')
            parser = record.get('parser_name', 'unknown')
            
            if source_file:
                file_ext = Path(source_file).suffix.lower()
                group_key = f"{file_ext}_{parser}"
            else:
                group_key = f"no_ext_{parser}"
            
            if group_key not in grouped:
                grouped[group_key] = []
            grouped[group_key].append(record)
        
        return grouped
    
    def _create_global_processing_batches(self, grouped_records: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Crea batch di processing globali ottimizzati.
        
        WHY: Crea batch che massimizzano l'efficienza del processing.
        Batch size dinamico basato sulla dimensione del dataset.
        
        Returns:
            Lista di batch di processing
        """
        processing_batches = []
        
        # CALCOLO BATCH SIZE DINAMICO E OTTIMIZZATO
        total_records = sum(len(records) for records in grouped_records.values())
        
        # WHY: Batch size ottimale basato sulla dimensione del dataset
        # Configurazione dinamica con possibilità di override
        optimal_batch_size = self._calculate_optimal_batch_size(total_records)
        
        print(f"🎯 Batch size ottimale calcolato: {optimal_batch_size} record per batch")
        print(f"📊 Dataset totale: {total_records} record, {len(grouped_records)} gruppi")
        
        for group_key, records in grouped_records.items():
            # Crea batch per questo gruppo usando batch size ottimale
            total_batches = (len(records) + optimal_batch_size - 1) // optimal_batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * optimal_batch_size
                end_idx = min(start_idx + optimal_batch_size, len(records))
                batch_records = records[start_idx:end_idx]
                
                # Estrai file unici nel batch
                files = set(r.get('source_file', 'unknown') for r in batch_records)
                
                batch = {
                    'group_key': group_key,
                    'batch_num': batch_num + 1,
                    'total_batches': total_batches,
                    'files': list(files),
                    'records': batch_records,
                    'size': len(batch_records),
                    'batch_size_used': optimal_batch_size
                }
                processing_batches.append(batch)
        
        return processing_batches
    
    def _calculate_optimal_batch_size(self, total_records: int) -> int:
        """
        Calcola il batch size ottimale basato sulla dimensione del dataset.
        
        WHY: Batch size dinamico che si adatta alla dimensione del dataset
        per massimizzare l'efficienza del processing.
        
        Args:
            total_records: Numero totale di record nel dataset
            
        Returns:
            Batch size ottimale
        """
        # WHY: Batch size ottimale basato sulla dimensione del dataset
        if total_records > 100000:  # Dataset molto grande
            optimal_batch_size = 10000  # Batch più grandi per efficienza
        elif total_records > 50000:  # Dataset grande
            optimal_batch_size = 8000   # Batch medi-grandi
        elif total_records > 20000:  # Dataset medio
            optimal_batch_size = 6000   # Batch medi
        else:  # Dataset piccolo
            optimal_batch_size = 4000   # Batch piccoli per flessibilità
        
        # Override da configurazione se disponibile
        if self.config and 'batch_processing' in self.config:
            config_batch_size = self.config['batch_processing'].get('optimal_batch_size')
            if config_batch_size and isinstance(config_batch_size, int):
                optimal_batch_size = config_batch_size
                print(f"⚙️ Batch size override da configurazione: {optimal_batch_size}")
        
        # Validazione e limiti di sicurezza
        optimal_batch_size = max(1000, min(optimal_batch_size, 20000))  # Min 1000, Max 20000
        
        return optimal_batch_size
    
    def _process_global_batch(self, batch: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processa un batch globale ottimizzato.
        
        Args:
            batch: Batch da processare
            
        Returns:
            Lista dei record processati
        """
        batch_results = []
        
        for record in batch['records']:
            try:
                # Normalizza il record usando il metodo ottimizzato
                normalized_record = self._normalize_output_record(record)
                batch_results.append(normalized_record)
            except Exception as e:
                # Record di errore
                error_record = record.copy()
                error_record['error'] = str(e)
                error_record['success'] = False
                batch_results.append(error_record)
        
        return batch_results
    
    def _process_records_in_batches(self, parsed_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processa i record in batch per ottimizzare le performance su grandi dataset.
        
        WHY: Evita il loop record-per-record inefficiente, processando in chunk
        per ridurre il tempo di elaborazione da minuti a secondi.
        
        Args:
            parsed_results: Lista dei risultati parsati
            
        Returns:
            Lista dei record processati
        """
        batch_size = 5000  # Processa 5000 record alla volta
        total_batches = (len(parsed_results) + batch_size - 1) // batch_size
        enriched_results = []
        
        print(f"📦 Processing in {total_batches} batch di {batch_size} record...")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(parsed_results))
            batch = parsed_results[start_idx:end_idx]
            
            print(f"🔄 Processando batch {batch_num + 1}/{total_batches} (record {start_idx}-{end_idx})...")
            
            # Processa il batch
            batch_results = self._process_batch(batch)
            enriched_results.extend(batch_results)
            
            print(f"✅ Batch {batch_num + 1} completato: {len(batch_results)} record processati")
        
        return enriched_results
    
    def _process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processa un singolo batch di record.
        
        Args:
            batch: Lista di record da processare
            
        Returns:
            Lista dei record processati
        """
        batch_results = []
        
        for item in batch:
            if not isinstance(item, dict):
                continue
            try:
                normalized = self._normalize_output_record(item)
                batch_results.append(normalized)
            except Exception as e:
                # Aggiungi record fallback per non perdere dati
                batch_results.append({
                    'error': f"Errore nel processamento: {e}",
                    'original_item': str(item)[:200]  # Primi 200 caratteri
                })
        
        return batch_results
    
    def _process_records_sequentially(self, parsed_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processa i record sequenzialmente (metodo originale per dataset piccoli).
        
        Args:
            parsed_results: Lista dei risultati parsati
            
        Returns:
            Lista dei record processati
        """
        enriched_results = []
        total_items = len(parsed_results)
        
        for i, item in enumerate(parsed_results):
            if i % 1000 == 0:  # Log ogni 1000 record
                print(f"📊 Processato {i}/{total_items} record...")
                
            if not isinstance(item, dict):
                continue
            try:
                normalized = self._normalize_output_record(item)
                enriched_results.append(normalized)
            except Exception as e:
                print(f"⚠️ Errore nel processare record {i}: {e}")
                # Aggiungi record fallback per non perdere dati
                enriched_results.append({
                    'error': f"Errore nel processamento: {e}",
                    'original_item': str(item)[:200]  # Primi 200 caratteri
                })
        
        return enriched_results

    def _anonymize_content(self, content: str) -> str:
        """
        Anonimizza il contenuto usando il servizio regex disponibile.
        
        WHY: Gestisce sia CentralizedRegexService che RegexService legacy
        per mantenere compatibilità durante la transizione.
        """
        try:
            if hasattr(self.regex_service, 'anonymize_content'):
                # CentralizedRegexService
                return self.regex_service.anonymize_content(content)
            elif hasattr(self.regex_service, 'apply_patterns_by_category'):
                # RegexService legacy
                return self.regex_service.apply_patterns_by_category(content, 'anonymization')
            else:
                # Fallback: nessuna anonimizzazione
                return content
        except Exception as e:
            print(f"⚠️ Errore nell'anonimizzazione: {e}")
            return content

    def _normalize_output_record(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rende l'output parsed_data.json più leggibile e coerente.
        
        WHY: Ottimizzato per evitare operazioni costose ripetute su grandi dataset.
        Usa configurazioni già cacheate e riutilizza risultati regex già elaborati.
        """
        # WHY: Riutilizza risultati regex già elaborati se disponibili
        if 'anonymized_message' in item:
            # Usa il messaggio già anonimizzato dal parsing precedente
            original = str(item.get('original_content', item.get('raw_line', '')))
            # 🚨 CORREZIONE: Usa SOLO drain3_anonymized.template come punto di verità
            # WHY: Evita confusione e ridondanza - un solo campo anonimizzato corretto
            if 'parsed_data' in item and 'drain3_anonymized' in item['parsed_data']:
                anonymized = item['parsed_data']['drain3_anonymized'].get('template', original)
            else:
                anonymized = item['anonymized_message']
        elif 'anonymized_template' in item:
            # Usa il template già anonimizzato
            original = str(item.get('original_content', item.get('raw_line', '')))
            anonymized = item['anonymized_template']
        else:
            # Fallback: anonimizza ora
            original = str(item.get('original_content', item.get('raw_line', '')))
            anonymized = self._anonymize_content(original)
        
        # 🚨 CORREZIONE: Rimuovo la logica complessa di always_anonymize
        # WHY: drain3_anonymized.template è già corretto e coerente
        # Non serve applicare always_anonymize qui perché è già fatto nel template
        
        # 🧹 PULIZIA: Rimuovo campi ridondanti dai parsed_data
        if 'parsed_data' in item and item['parsed_data']:
            parsed_data_clean = item['parsed_data'].copy()
            
            # Rimuovo campi duplicati e ridondanti
            fields_to_remove = [
                'template',  # Duplicato di drain3_original.template
                'anonymized_message',  # Ridondante con drain3_anonymized.template
                'drain3_cluster_id',  # Ridondante con drain3_original.cluster_id
                'drain3_template',    # Ridondante con drain3_original.template
            ]
            
            for field in fields_to_remove:
                if field in parsed_data_clean:
                    del parsed_data_clean[field]
            
            # Mantengo solo i campi essenziali
            item['parsed_data'] = parsed_data_clean

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
        # 🚨 CORREZIONE: Usa SOLO drain3_anonymized.template come punto di verità
        # WHY: Evita confusione e ridondanza - un solo campo anonimizzato corretto
        if 'parsed_data' in item and 'drain3_anonymized' in item['parsed_data']:
            out['anonymized_message'] = item['parsed_data']['drain3_anonymized'].get('template', anonymized)
        else:
            out['anonymized_message'] = anonymized

        # IMPORTANTE: Aggiungi i parsed_data direttamente per visibilità
        if 'parsed_data' in item and item['parsed_data']:
            out['parsed_data'] = item['parsed_data']

        # 🆕 AGGIUNGI DATI PRESIDIO se disponibili
        if 'presidio_anonymization' in item and item['presidio_anonymization']:
            out['presidio_anonymization'] = item['presidio_anonymization']

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