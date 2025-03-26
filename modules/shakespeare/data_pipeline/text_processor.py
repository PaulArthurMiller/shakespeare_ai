from modules.utils.logger import CustomLogger
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ProcessingConfig:
    """Configuration for text processing parameters."""
    min_fragment_length: int = 20
    max_fragment_length: int = 200
    remove_stage_directions: bool = True
    remove_scene_headers: bool = True
    preserve_character_names: bool = True

class ShakespeareTextProcessor:
    """
    Processes Shakespearean texts into usable fragments for cento generation.
    
    This class serves as the initial data processing pipeline for the Shakespeare
    Cento Generator. It handles the loading, cleaning, and segmentation of original
    Shakespeare texts into meaningful fragments that can be used by downstream
    components for play generation.

    Key Features:
        - Configurable text processing parameters
        - Robust error handling with detailed logging
        - Preservation of text structure and character names
        - Fragment extraction with metadata
    """

    def __init__(self, source_dir: Optional[str] = None, config: Optional[ProcessingConfig] = None):
        """
        Initialize the text processor with optional configuration.

        Args:
            source_dir (str, optional): Directory containing Shakespeare's texts
            config (ProcessingConfig, optional): Processing configuration parameters
        """
        self.logger = CustomLogger(
            name="ShakespeareTextProcessor",
            log_level="INFO",
            log_file="logs/shakespeare_processor.log"
        )
        self.source_dir = Path(source_dir) if source_dir else None
        self.config = config or ProcessingConfig()
        self.fragments: Dict[str, List[Tuple[str, dict]]] = {}
        
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
        Clean and normalize the text according to configuration settings.

        Performs the following operations based on config:
        - Removes stage directions if configured
        - Removes scene/act headers if configured
        - Preserves character names if configured
        - Normalizes whitespace and punctuation

        Args:
            text (str): Raw text to clean

        Returns:
            str: Cleaned and normalized text

        Raises:
            ValueError: If text is empty or invalid
        """
        if not text or not text.strip():
            raise ValueError("Empty or invalid text provided")

        self.logger.debug("Starting text cleaning process")
        
        if self.config.remove_stage_directions:
            text = re.sub(r'\[.*?\]', '', text)
            
        if self.config.remove_scene_headers:
            text = re.sub(r'ACT [IVX]+.*?\n|SCENE [IVX]+.*?\n', '', text)
            
        if self.config.preserve_character_names:
            # Store character names for preservation
            character_names = set(re.findall(r'^([A-Z]{2,})\.\s', text, re.MULTILINE))
            
        # Normalize whitespace and punctuation
        text = ' '.join(text.split())
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        
        self.logger.debug(f"Text cleaning completed with config: {vars(self.config)}")
        return text

    def extract_fragments(self, text: str, play_name: str) -> None:
        """
        Extract usable fragments from the cleaned text with metadata.

        Fragments are extracted based on configuration parameters and include
        metadata about their source, length, and any special characteristics.

        Args:
            text (str): Cleaned text to process
            play_name (str): Name of the play being processed

        Returns:
            None: Stores fragments in self.fragments dictionary

        Raises:
            ValueError: If text is empty or invalid
        """
        if not text or not text.strip():
            raise ValueError("Empty or invalid text provided for fragment extraction")

        fragments = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check fragment length constraints
            if (len(line) >= self.config.min_fragment_length and 
                len(line) <= self.config.max_fragment_length):
                
                # Create metadata for the fragment
                metadata = {
                    'length': len(line),
                    'line_number': i + 1,
                    'contains_dialog': bool(re.search(r'["""'']', line)),
                    'source_play': play_name
                }
                
                fragments.append((line, metadata))

        self.fragments[play_name] = fragments
        self.logger.info(
            f"Extracted {len(fragments)} fragments from {play_name} "
            f"(min_length={self.config.min_fragment_length}, "
            f"max_length={self.config.max_fragment_length})"
        )

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
