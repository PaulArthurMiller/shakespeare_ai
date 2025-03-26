from modules.utils.logger import CustomLogger
import re
from typing import List, Dict, Optional
from pathlib import Path

class ShakespeareTextProcessor:
    """
    Processes Shakespearean texts into usable fragments for cento generation.
    Handles loading, cleaning, and segmenting of original Shakespeare texts.
    """

    def __init__(self, source_dir: Optional[str] = None):
        """
        Initialize the text processor.

        Args:
            source_dir (str, optional): Directory containing Shakespeare's texts
        """
        self.logger = CustomLogger(
            name="ShakespeareTextProcessor",
            log_level="INFO",
            log_file="logs/shakespeare_processor.log"
        )
        self.source_dir = Path(source_dir) if source_dir else None
        self.fragments: Dict[str, List[str]] = {}
        
    def load_text(self, play_path: str) -> str:
        """
        Load a Shakespeare play from a file.

        Args:
            play_path (str): Path to the play text file

        Returns:
            str: Raw text content of the play
        """
        try:
            with open(play_path, 'r', encoding='utf-8') as file:
                content = file.read()
                self.logger.info(f"Successfully loaded text from {play_path}")
                return content
        except Exception as e:
            self.logger.error(f"Failed to load text from {play_path}: {str(e)}")
            raise

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize the text.

        Args:
            text (str): Raw text to clean

        Returns:
            str: Cleaned text
        """
        # Remove stage directions [in brackets]
        text = re.sub(r'\[.*?\]', '', text)
        # Remove scene/act headers
        text = re.sub(r'ACT [IVX]+.*?\n|SCENE [IVX]+.*?\n', '', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        self.logger.debug("Text cleaning completed")
        return text

    def extract_fragments(self, text: str, play_name: str) -> None:
        """
        Extract usable fragments from the cleaned text.

        Args:
            text (str): Cleaned text to process
            play_name (str): Name of the play being processed
        """
        # Split into lines and filter empty ones
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        self.fragments[play_name] = lines
        self.logger.info(f"Extracted {len(lines)} fragments from {play_name}")

    def process_play(self, play_path: str, play_name: str) -> None:
        """
        Process a complete play through the pipeline.

        Args:
            play_path (str): Path to the play file
            play_name (str): Name of the play
        """
        try:
            raw_text = self.load_text(play_path)
            cleaned_text = self.clean_text(raw_text)
            self.extract_fragments(cleaned_text, play_name)
            self.logger.info(f"Successfully processed {play_name}")
        except Exception as e:
            self.logger.error(f"Failed to process {play_name}: {str(e)}")
            raise
