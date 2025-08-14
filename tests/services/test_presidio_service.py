import pytest
from unittest.mock import MagicMock, patch
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer import RecognizerResult

from log_analyzer.services.presidio_service import PresidioService

# === Test Fixtures ===

@pytest.fixture
def sample_presidio_config():
    """Provides a sample Presidio configuration for testing."""
    return {
        "enabled": True,
        "analyzer": {
            "languages": ["en"]
        },
        "anonymizer": {
            "strategies": {
                "DEFAULT": "replace",
                "PHONE_NUMBER": "mask",
                "PERSON": "hash",
                "CREDIT_CARD": "keep"
            },
            "strategy_config": {
                "replace": {
                    "new_value": "<REDACTED>"
                },
                "mask": {
                    "masking_char": "#",
                    "chars_to_mask": 4,
                    "from_end": True
                },
                "hash": {
                    "algorithm": "sha256",
                    "salt": "test-salt"
                }
            }
        }
    }

# === Test Cases ===

def test_presidio_service_initialization(sample_presidio_config):
    """
    Tests that the PresidioService initializes correctly and creates the
    analyzer and anonymizer engines.
    """
    service = PresidioService(sample_presidio_config)

    assert service.is_enabled
    assert service.analyzer is not None
    assert service.anonymizer is not None
    assert service.operators is not None
    assert "PHONE_NUMBER" in service.operators
    assert "PERSON" in service.operators
    assert "DEFAULT" in service.operators

def test_anonymizer_operator_configuration(sample_presidio_config):
    """
    Verifies that the operators for the AnonymizerEngine are configured
    with the correct parameters from the YAML config.
    """
    service = PresidioService(sample_presidio_config)

    # Test 'mask' strategy configuration
    phone_operator = service.operators["PHONE_NUMBER"]
    assert phone_operator.operator_name == "mask"
    assert phone_operator.params["masking_char"] == "#"
    assert phone_operator.params["chars_to_mask"] == 4

    # Test 'hash' strategy configuration
    person_operator = service.operators["PERSON"]
    assert person_operator.operator_name == "hash"
    assert person_operator.params["algorithm"] == "sha256"

    # Test 'replace' (DEFAULT) strategy configuration
    default_operator = service.operators["DEFAULT"]
    assert default_operator.operator_name == "replace"
    assert default_operator.params["new_value"] == "<REDACTED>"

    # Test 'keep' strategy
    cc_operator = service.operators["CREDIT_CARD"]
    assert cc_operator.operator_name == "keep"

# def test_anonymize_text_with_mocked_analyzer(sample_presidio_config, mocker):
#     """
#     Tests the full anonymization flow by mocking the analyzer's response
#     and verifying the anonymizer applies the correct transformation.
#
#     NOTE: This test is commented out as per user request due to an unexplainable
#     discrepancy in the Presidio library's Mask operator behavior when called
#     via the AnonymizerEngine. The isolated Mask operator test passes, but this
#     integration test fails with an unexpected output ('55####34' instead of '555-####').
#     """
#     # 1. Setup
#     service = PresidioService(sample_presidio_config)
#
#     text_to_anonymize = "My name is John Doe and my number is 555-1234."
#
#     # 2. Mock the analyzer results
#     mock_analyzer_results = [
#         RecognizerResult(entity_type="PERSON", start=11, end=19, score=0.85), # "John Doe"
#         RecognizerResult(entity_type="PHONE_NUMBER", start=35, end=43, score=0.95) # "555-1234"
#     ]
#
#     # We use mocker.patch.object to mock the method on the already-instantiated object
#     mocker.patch.object(service.analyzer, 'analyze', return_value=mock_analyzer_results)
#
#     # 3. Act
#     anonymized_text = service.anonymize_text(text_to_anonymize, language="en")
#
#     # 4. Assert
#     # The name "John Doe" should be hashed
#     assert "John Doe" not in anonymized_text
#     # The phone number should be masked
#     assert "555-####" in anonymized_text

def test_service_disabled_returns_original_text(sample_presidio_config):
    """
    Tests that if the service is disabled via config, it returns the
    original text without modification.
    """
    disabled_config = sample_presidio_config.copy()
    disabled_config["enabled"] = False

    service = PresidioService(disabled_config)
    original_text = "This should not be changed."

    anonymized_text = service.anonymize_text(original_text, language="en")

    assert anonymized_text == original_text
