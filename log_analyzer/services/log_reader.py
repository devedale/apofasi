from typing import Iterator, Tuple, Dict, Any
import chardet

class LogReader:
    """A service for reading log files with robust encoding detection."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the log reader.

        Args:
            config: The application configuration.
        """
        self.config = config

    def read_lines(self, file_path: str) -> Iterator[Tuple[int, str]]:
        """
        Reads a file and yields each line with its line number.
        It attempts to detect the file's encoding.

        Args:
            file_path: The path to the log file.

        Yields:
            A tuple containing the line number (1-indexed) and the line content.
        """
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read(32 * 1024) # Read first 32KB to detect encoding
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

            # Read and yield lines with the detected encoding
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    yield i, line.strip()

        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            return
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return
