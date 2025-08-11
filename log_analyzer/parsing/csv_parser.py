import csv
from io import StringIO
from typing import Optional, List, Dict, Any

from .interfaces import AbstractParser, LogEntry, ParsedRecord

class CSVParser(AbstractParser):
    """
    A concrete parser that handles CSV log entries.
    This parser needs to be configured with a delimiter and a header.
    It's less of a general-purpose detector and more of a specific processor.
    """
    def __init__(self, delimiter: str = ',', header: Optional[List[str]] = None):
        self.delimiter = delimiter
        self.header = header

    def handle(self, log_entry: LogEntry) -> Optional[ParsedRecord]:
        """
        Tries to parse the log entry content as a CSV line.

        Args:
            log_entry: The log entry to parse.

        Returns:
            A ParsedRecord if the content can be parsed as a CSV line with
            the expected number of columns, otherwise the result from the
            next handler.
        """
        try:
            # Use StringIO to treat the string line as a file for the csv reader
            f = StringIO(log_entry.content)
            reader = csv.reader(f, delimiter=self.delimiter)

            # Read the single line from the "file"
            fields = next(reader)

            # If we have a header, we expect the number of fields to match
            if self.header:
                if len(fields) == len(self.header):
                    parsed_data = dict(zip(self.header, fields))
                    return ParsedRecord(
                        original_content=log_entry.content,
                        line_number=log_entry.line_number,
                        source_file=log_entry.source_file,
                        parser_name='CSVParser',
                        parsed_data=parsed_data
                    )
            # If no header is provided, we can still parse it with generic field names
            elif len(fields) > 1: # A simple heuristic: if there's more than one field
                parsed_data = {f"field_{i+1}": field for i, field in enumerate(fields)}
                return ParsedRecord(
                    original_content=log_entry.content,
                    line_number=log_entry.line_number,
                    source_file=log_entry.source_file,
                    parser_name='CSVParser',
                    parsed_data=parsed_data
                )

        except (csv.Error, StopIteration):
            # This indicates it's not a valid CSV line for the given delimiter
            # or it's an empty line. Pass to the next handler.
            return super().handle(log_entry)

        # If parsing was attempted but didn't meet criteria (e.g., field count mismatch),
        # pass to the next handler.
        return super().handle(log_entry)
