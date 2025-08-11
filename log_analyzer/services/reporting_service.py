import json
import csv
from pathlib import Path
from typing import List
from ..parsing.interfaces import ParsedRecord

class ReportingService:
    """
    A service for generating output reports from processed log records.
    """
    def __init__(self, output_dir: str):
        """
        Initializes the service with the output directory.

        Args:
            output_dir: The path to the directory where reports will be saved.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_json_report(self, records: List[ParsedRecord]):
        """
        Saves the list of fully processed records as a single JSON file.

        Args:
            records: A list of ParsedRecord objects.
        """
        output_file = self.output_dir / "full_structured_output.json"

        # Convert Pydantic models to dictionaries for JSON serialization
        records_as_dicts = [record.model_dump() for record in records]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(records_as_dicts, f, indent=2)
        print(f"Full JSON report saved to: {output_file}")

    def generate_logppt_report(self, records: List[ParsedRecord]):
        """
        Generates a CSV file in a format compatible with LogPPT for training.
        The format is assumed to be: 'LineId, AnonymizedTemplate, OriginalLog'

        Args:
            records: A list of ParsedRecord objects.
        """
        output_file = self.output_dir / "logppt_training_data.csv"

        header = ['LineId', 'EventTemplate', 'OriginalLog']

        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for i, record in enumerate(records):
                # Use the anonymized template from Drain3 as the EventTemplate
                template = record.drain3_anonymized.get('template', '<NO_TEMPLATE>')

                row = [
                    i + 1,  # LineId
                    template, # EventTemplate
                    record.original_content # OriginalLog
                ]
                writer.writerow(row)

        print(f"LogPPT training CSV saved to: {output_file}")
