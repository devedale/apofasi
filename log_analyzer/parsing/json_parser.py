import json
from typing import Optional

from .interfaces import AbstractParser, LogEntry, ParsedRecord

class JSONParser(AbstractParser):
    """
    A concrete parser that handles JSON log entries.
    If a log entry is a valid JSON string, this parser will handle it.
    Otherwise, it passes the request to the next parser in the chain.
    """
    def handle(self, log_entry: LogEntry) -> Optional[ParsedRecord]:
        """
        Tries to parse the log entry content as JSON.

        Args:
            log_entry: The log entry to parse.

        Returns:
            A ParsedRecord if the content is valid JSON, otherwise the result
            from the next handler in the chain.
        """
        try:
            # Attempt to parse the log content as a JSON object
            parsed_json = json.loads(log_entry.content)

            if isinstance(parsed_json, dict):
                # Successfully parsed as a JSON object
                return ParsedRecord(
                    original_content=log_entry.content,
                    line_number=log_entry.line_number,
                    source_file=log_entry.source_file,
                    parser_name='JSONParser',
                    parsed_data=parsed_json
                )
            else:
                # The content is valid JSON, but not a JSON object (e.g., a number or a string).
                # This is not what we consider a structured log, so pass it on.
                return super().handle(log_entry)

        except json.JSONDecodeError:
            # The content is not valid JSON, pass to the next handler
            return super().handle(log_entry)
