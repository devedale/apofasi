from typing import Dict, Any, List

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import AnonymizerRequest, AnonymizerResult

from ..parsing.interfaces import ParsedRecord

class PresidioService:
    """
    A service to handle PII detection and anonymization using Microsoft Presidio.
    This class wraps the Presidio Analyzer and Anonymizer engines.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the PresidioService.

        Args:
            config: The application configuration, which should contain a
                    'presidio' section.
        """
        self.config = config.get('presidio', {})

        # 1. Create and configure the AnalyzerEngine
        self.analyzer = AnalyzerEngine()

        # 2. Create and configure the AnonymizerEngine
        self.anonymizer = AnonymizerEngine()

    def analyze(self, text: str, language: str = 'en') -> List[Dict[str, Any]]:
        """
        Analyzes a given text to find PII entities.

        Args:
            text: The text to analyze.
            language: The language of the text.

        Returns:
            A list of dictionaries, where each dictionary represents a found entity.
        """
        try:
            results = self.analyzer.analyze(text=text, language=language)
            return [res.to_dict() for res in results]
        except Exception as e:
            print(f"Error during Presidio analysis: {e}")
            return []

    def anonymize_record(self, record: ParsedRecord) -> ParsedRecord:
        """
        Analyzes and anonymizes the original content of a ParsedRecord.

        It updates the record with the anonymized content and metadata from Presidio.

        Args:
            record: The ParsedRecord to anonymize.

        Returns:
            The same ParsedRecord, mutated with the anonymization results.
        """
        if not self.config.get('enabled', False):
            return record

        try:
            # Analyze the text to find PII
            analyzer_results = self.analyzer.analyze(
                text=record.original_content,
                language=self.config.get('analyzer', {}).get('languages', ['en'])[0]
            )

            # Anonymize the text based on the analysis
            anonymized_result: AnonymizerResult = self.anonymizer.anonymize(
                text=record.original_content,
                analyzer_results=analyzer_results
            )

            # Update the record with the results
            record.presidio_anonymized = anonymized_result.text
            record.presidio_metadata = [res.to_dict() for res in analyzer_results]

        except Exception as e:
            print(f"Error during record anonymization for line {record.line_number}: {e}")
            # Ensure fields are not left in an indeterminate state
            record.presidio_anonymized = record.original_content # Fallback
            record.presidio_metadata = [{'error': str(e)}]

        return record
