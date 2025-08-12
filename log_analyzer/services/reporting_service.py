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

    def generate_logppt_reports(self, records: List[ParsedRecord]):
        """
        Generates two CSV files in a format compatible with LogPPT: one with
        original data and one with anonymized data.
        """
        # Generate the report for the original data
        self._generate_logppt_csv(records, 'original')

        # Generate the report for the anonymized data
        self._generate_logppt_csv(records, 'anonymized')

    def _generate_logppt_csv(self, records: List[ParsedRecord], version: str):
        """
        A helper method to generate a single LogPPT-compatible CSV file.

        Args:
            records: A list of ParsedRecord objects.
            version: The version to generate ('original' or 'anonymized').
        """
        if not records:
            return

        output_file = self.output_dir / f"logppt_{version}.csv"

        # --- Dynamically determine the header ---
        # Start with fixed columns
        fixed_start_cols = ['LineId']
        fixed_end_cols = ['Content', 'EventId', 'EventTemplate']

        # Find all unique parsed field keys from all records
        parsed_field_keys = set()
        for record in records:
            if record.parsed_data:
                parsed_field_keys.update(record.parsed_data.keys())

        # Sort for consistent column order
        sorted_parsed_keys = sorted(list(parsed_field_keys))

        # Final header
        header = fixed_start_cols + sorted_parsed_keys + fixed_end_cols

        # --- Write data to CSV ---
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for i, record in enumerate(records):
                row = [i + 1] # LineId

                # Add parsed field values, using empty string if a key is missing
                for key in sorted_parsed_keys:
                    row.append(record.parsed_data.get(key, ''))

                # Add the final fixed columns based on the version
                if version == 'original':
                    content = record.original_content
                    event_id = f"E{record.drain3_original.get('cluster_id', -1)}"
                    template = record.drain3_original.get('template', '<NO_TEMPLATE>')
                else: # anonymized
                    content = record.presidio_anonymized or record.original_content
                    event_id = f"E{record.drain3_anonymized.get('cluster_id', -1)}"
                    template = record.drain3_anonymized.get('template', '<NO_TEMPLATE>')

                row.extend([content, event_id, template])
                writer.writerow(row)

        print(f"LogPPT ({version}) report saved to: {output_file}")
