from typing import Dict, Any, List
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import AnonymizerRequest, AnonymizerResult, OperatorConfig
from presidio_analyzer.recognizer_result import RecognizerResult
from presidio_analyzer.ad_hoc_recognizer import AdHocRecognizer


from ..parsing.interfaces import ParsedRecord

class PresidioService:
    """
    A service to handle PII detection and anonymization using Microsoft Presidio.
    This class wraps the Presidio Analyzer and Anonymizer engines.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the PresidioService, dynamically configuring the engines
        based on the provided configuration.
        """
        self.config = config.get('presidio', {})

        # --- Create and configure the AnalyzerEngine ---
        registry = RecognizerRegistry()

        # 1. Add ad-hoc regex recognizers from config
        ad_hoc_recognizers = self.config.get('analyzer', {}).get('ad_hoc_recognizers', [])
        for rec_conf in ad_hoc_recognizers:
            registry.add_recognizer(
                AdHocRecognizer(
                    supported_entity=rec_conf["name"],
                    patterns=[rec_conf["regex"]],
                )
            )

        # 2. Add default recognizers
        registry.load_predefined_recognizers()

        # TODO: Add logic to load multiple spacy models based on config

        self.analyzer = AnalyzerEngine(registry=registry)

        # --- Create and configure the AnonymizerEngine ---
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

            # Build the anonymizers dictionary from the config
            conf_strategies = self.config.get('anonymizer', {}).get('strategies', {})
            anonymizers_config = {
                entity: OperatorConfig(operator_name, conf_strategies.get(entity, {}))
                for entity, operator_name in conf_strategies.items()
            }

            # Anonymize the text based on the analysis and configured strategies
            anonymized_result: AnonymizerResult = self.anonymizer.anonymize(
                text=record.original_content,
                analyzer_results=analyzer_results,
                anonymizers=anonymizers_config
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
