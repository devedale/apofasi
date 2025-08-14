# === DESIGN COMMENT ===
# The PresidioService encapsulates all interactions with the Microsoft Presidio library.
# Its primary responsibilities are:
# 1.  Loading and interpreting the 'presidio' section of the global config.
# 2.  Correctly instantiating the AnalyzerEngine with all its recognizers.
# 3.  Correctly instantiating the AnonymizerEngine and preparing the operators for it.
# 4.  Providing a simple, high-level interface for anonymizing text.
# 5.  Providing a method to inspect the recognizer registry for the UI.
#
# This service-based approach decouples the web layer (or any other consumer) from the
# complexities of Presidio's configuration, adhering to the Single Responsibility Principle
# and improving the overall architecture of the application.

import logging
from typing import Dict, Any, List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine, OperatorConfig

# Configure logging for the service
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PresidioService:
    """
    A service to handle all Presidio-related operations, including PII analysis and anonymization.
    """
    def __init__(self, presidio_config: Dict[str, Any]):
        """
        Initializes the PresidioService with a given configuration.

        Args:
            presidio_config: A dictionary containing the 'presidio' section of the main config.
        """
        if not presidio_config or not presidio_config.get('enabled', False):
            logger.info("Presidio service is disabled in the configuration.")
            self.analyzer = None
            self.anonymizer = None
            self.operators = {}
            self.is_enabled = False
            return

        logger.info("Initializing PresidioService...")
        self.config = presidio_config
        self.is_enabled = True
        self.analyzer = self._create_analyzer()
        self.operators = self._get_operators()
        self.anonymizer = AnonymizerEngine()
        logger.info("PresidioService initialized successfully.")

    def _get_operators(self) -> Dict[str, OperatorConfig]:
        """
        Builds the dictionary of 'operators' that defines anonymization strategy.
        """
        operators = {}
        anonymizer_config = self.config.get('anonymizer', {})
        strategies = anonymizer_config.get('strategies', {})
        strategy_configs = anonymizer_config.get('strategy_config', {})

        for entity_name, strategy_name in strategies.items():
            params = strategy_configs.get(strategy_name, {})
            operators[entity_name.upper()] = OperatorConfig(strategy_name, params)

        ad_hoc_recognizers = self.config.get('analyzer', {}).get('ad_hoc_recognizers', [])
        for rec_conf in ad_hoc_recognizers:
            strategy_name = rec_conf.get("strategy")
            entity_name = rec_conf.get("name")
            if entity_name and strategy_name:
                params = strategy_configs.get(strategy_name, {})
                operators[entity_name.upper()] = OperatorConfig(strategy_name, params)

        logger.info(f"Created operators dictionary with {len(operators)} operators.")
        return operators

    def _create_analyzer(self) -> Optional[AnalyzerEngine]:
        """
        Creates and configures the Presidio AnalyzerEngine based on the loaded config.
        """
        try:
            analyzer_config = self.config.get('analyzer', {})
            languages = analyzer_config.get('languages', ['en'])

            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(languages=languages)

            ad_hoc_recognizers = analyzer_config.get('ad_hoc_recognizers', [])
            for rec_conf in ad_hoc_recognizers:
                if rec_conf.get("name") and rec_conf.get("regex"):
                    pattern = Pattern(name=rec_conf['name'], regex=rec_conf['regex'], score=float(rec_conf['score']))
                    ad_hoc_recognizer = PatternRecognizer(supported_entity=rec_conf['name'], patterns=[pattern])
                    registry.add_recognizer(ad_hoc_recognizer)

            confidence_threshold = analyzer_config.get('analysis', {}).get('confidence_threshold')

            return AnalyzerEngine(
                registry=registry,
                supported_languages=languages,
                default_score_threshold=confidence_threshold
            )
        except Exception as e:
            logger.error(f"Fatal error creating Presidio AnalyzerEngine: {e}", exc_info=True)
            return None

    def anonymize_text(self, text: str, **kwargs) -> str:
        """
        Anonymizes a given text string using the configured Presidio engines.
        """
        if not self.is_enabled or not self.analyzer or not self.anonymizer:
            return text

        try:
            analyzer_results = self.analyzer.analyze(text=text, **kwargs)
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators=self.operators
            )
            return anonymized_result.text
        except Exception as e:
            logger.error(f"Error during anonymization: {e}", exc_info=True)
            return text

    def get_recognizer_details(self) -> Dict[str, Any]:
        """
        Inspects the analyzer's registry and returns a detailed dictionary of
        all available recognizers and their entities for the UI.
        """
        if not self.is_enabled or not self.analyzer:
            return {}

        user_entities = self.config.get("analyzer", {}).get("entities", {})
        user_strategies = self.config.get("anonymizer", {}).get("strategies", {})
        language = self.config.get("analyzer", {}).get("languages", ["en"])[0]

        detailed_entities = {}
        try:
            default_recognizers = self.analyzer.get_recognizers(language=language)
            for rec in default_recognizers:
                entities = getattr(rec, 'supported_entities', [])
                if not entities:
                    continue

                for entity_name in entities:
                    is_enabled = user_entities.get(entity_name, True)
                    strategy = user_strategies.get(entity_name, "replace")
                    score = getattr(rec, 'default_score', 0.0)

                    detailed_entities[entity_name] = {
                        "enabled": is_enabled,
                        "strategy": strategy,
                        "score": score if isinstance(score, (int, float)) else 0.0,
                        "regex": "N/A (NLP or other logic)",
                        "is_regex_based": False
                    }

                    if isinstance(rec, PatternRecognizer):
                        detailed_entities[entity_name]["regex"] = "\\n".join(p.regex for p in rec.patterns)
                        detailed_entities[entity_name]["is_regex_based"] = True
        except Exception as e:
            logger.error(f"Error inspecting recognizers: {e}", exc_info=True)
            # Fallback to a simpler representation if inspection fails
            return user_entities

        return detailed_entities
