from typing import List, Dict, Any
from pathlib import Path
from tqdm import tqdm

from ..parsing.interfaces import LogEntry, ParsedRecord
from ..parsing.parser_factory import create_parser_chain
from .log_reader import LogReader
from .presidio_service import PresidioService
from .drain3_service import Drain3Service

class LogProcessingService:
    """
    This service orchestrates the entire log processing pipeline, from
    reading files to producing a fully analyzed and structured output.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the service with the application configuration.

        Args:
            config: The application configuration dictionary.
        """
        self.config = config
        self.parser_chain = create_parser_chain(config)
        self.log_reader = LogReader(config)
        self.presidio_service = PresidioService(config)
        self.drain3_service = Drain3Service(config)

    def process_files(self, file_paths: List[str]) -> List[ParsedRecord]:
        """
        The main method that executes the unified processing pipeline.

        Args:
            file_paths: A list of string paths to the log files to process.

        Returns:
            A list of fully processed ParsedRecord objects.
        """
        print("--- Starting Unified Log Processing Pipeline ---")

        # === Phase 1: Parse & Anonymize (per-record) ===
        print("Phase 1: Parsing and AI-powered Anonymization...")
        all_records = self._phase1_parse_and_anonymize(file_paths)

        # === Phase 2: Template Mining (batch) ===
        print("\nPhase 2: Batch Template Mining with Drain3...")
        self._phase2_template_mining(all_records)

        # === Phase 3: Structured Output ===
        print("\nPhase 3: Assembling final structured output...")
        print(f"Processed a total of {len(all_records)} records.")

        print("\n--- Pipeline Finished ---")
        return all_records

    def _phase1_parse_and_anonymize(self, file_paths: List[str]) -> List[ParsedRecord]:
        """Handles parsing each line and running Presidio on it."""
        if not self.parser_chain:
            print("Error: Parser chain is not initialized. Cannot proceed.")
            return []

        all_records: List[ParsedRecord] = []

        with tqdm(total=len(file_paths), desc="Processing Files") as pbar_files:
            for file_path in file_paths:
                pbar_files.set_description(f"Processing {Path(file_path).name}")
                for line_num, line_content in self.log_reader.read_lines(file_path):
                    if not line_content:
                        continue

                    log_entry = LogEntry(
                        line_number=line_num,
                        content=line_content,
                        source_file=file_path
                    )

                    # Run the chain of responsibility for parsing
                    parsed_record = self.parser_chain.handle(log_entry)

                    if parsed_record:
                        # Handle the 'always_anonymize' feature for parsed fields
                        self._handle_always_anonymize(parsed_record)

                        # Run Presidio for PII detection and anonymization on the raw string
                        anonymized_record = self.presidio_service.anonymize_record(parsed_record)
                        all_records.append(anonymized_record)
                pbar_files.update(1)

        return all_records

    def _phase2_template_mining(self, records: List[ParsedRecord]):
        """Handles batch processing with Drain3 for both original and anonymized content."""
        if not records:
            print("  No records to process for template mining.")
            return

        # --- Process original content ---
        print("  - Mining templates from original content...")
        original_content = [rec.original_content for rec in records]
        original_results = self.drain3_service.process_batch(original_content, 'original')

        # --- Process anonymized content ---
        print("  - Mining templates from anonymized content...")
        anonymized_content = [rec.presidio_anonymized or "" for rec in records]
        anonymized_results = self.drain3_service.process_batch(anonymized_content, 'anonymized')

        # --- Merge results back into records ---
        print("  - Merging template results back into records...")
        for i, record in enumerate(records):
            if i < len(original_results):
                record.drain3_original = original_results[i]
            if i < len(anonymized_results):
                record.drain3_anonymized = anonymized_results[i]

    def _handle_always_anonymize(self, record: ParsedRecord):
        """
        Anonymizes specific fields within parsed_data based on the 'always_anonymize'
        list in the config. This uses Presidio to get semantic placeholders.

        This creates a separate `parsed_data_anonymized` dictionary, leaving
        the original `parsed_data` intact.

        Args:
            record: The ParsedRecord object to process.
        """
        always_anonymize_fields = self.config.get('drain3', {}).get('anonymization', {}).get('always_anonymize', [])

        # Start with a copy of the original parsed data.
        anonymized_data = record.parsed_data.copy()

        if not always_anonymize_fields:
            record.parsed_data_anonymized = anonymized_data
            return

        for field_name, value in anonymized_data.items():
            if field_name in always_anonymize_fields and isinstance(value, str) and value:
                # Use Presidio to analyze and anonymize the specific field value
                try:
                    analyzer_results = self.presidio_service.analyzer.analyze(text=value, language='en')

                    if analyzer_results:
                        # If entities are found, anonymize them semantically
                        anonymized_result = self.presidio_service.anonymizer.anonymize(
                            text=value,
                            analyzer_results=analyzer_results
                        )
                        anonymized_data[field_name] = anonymized_result.text
                    else:
                        # Fallback for values not recognized by Presidio
                        anonymized_data[field_name] = f"<{field_name.upper()}>"
                except Exception:
                    # In case of any error during value-specific anonymization, fallback
                    anonymized_data[field_name] = f"<{field_name.upper()}>"

        record.parsed_data_anonymized = anonymized_data
