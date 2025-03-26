from modules.utils.logger import CustomLogger
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

def extract_speaker(line: str) -> tuple[str, str]:
    """
    Extract speaker name and their dialogue from a line.
    
    Args:
        line (str): A line of text potentially containing speaker and dialogue
        
    Returns:
        tuple[str, str]: (speaker name, dialogue text) or ('', original line) if no speaker
    """
    speaker_match = re.match(r'^([A-Z][A-Z\s]+)\.(.+)$', line)
    if speaker_match:
        speaker = speaker_match.group(1).strip()
        dialogue = speaker_match.group(2).strip()
        return speaker, dialogue
    return '', line.strip()

def split_acts(text: str) -> dict[int, str]:
    """
    Split play text into acts.
    
    Args:
        text (str): Full play text
        
    Returns:
        dict[int, str]: Dictionary mapping act numbers to act content
    """
    acts = {}
    current_act = 0
    current_content = []
    
    for line in text.split('\n'):
        act_match = re.match(r'^ACT\s+([IVX]+)', line)
        if act_match:
            if current_act > 0:
                acts[current_act] = '\n'.join(current_content)
            current_act = _roman_to_int(act_match.group(1))
            current_content = []
        else:
            current_content.append(line)
    
    if current_content:
        acts[current_act] = '\n'.join(current_content)
    
    return acts

def _roman_to_int(roman: str) -> int:
    """
    Convert Roman numeral to integer.
    
    Args:
        roman (str): Roman numeral string
        
    Returns:
        int: Integer value
    """
    roman_values = {
        'I': 1, 'V': 5, 'X': 10,
        'L': 50, 'C': 100, 'D': 500, 'M': 1000
    }
    
    total = 0
    prev_value = 0
    
    for char in reversed(roman.upper()):
        curr_value = roman_values[char]
        if curr_value >= prev_value:
            total += curr_value
        else:
            total -= curr_value
        prev_value = curr_value
        
    return total

def read_shakespeare_text(file_path: str) -> str:
    """
    Read and validate a Shakespeare text file.
    
    Args:
        file_path (str): Path to the Shakespeare text file
        
    Returns:
        str: Content of the text file
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file is empty
        UnicodeDecodeError: If the file encoding is not UTF-8
    """
    logger = CustomLogger(
        name="ShakespeareReader",
        log_level="INFO",
        log_file="logs/shakespeare_reader.log"
    )
    
    try:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"No such file: {file_path}")
            
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        if not content.strip():
            logger.error(f"Empty file: {file_path}")
            raise ValueError(f"File is empty: {file_path}")
            
        logger.info(f"Successfully read {len(content)} characters from {file_path}")
        return content
        
    except UnicodeDecodeError as e:
        logger.error(f"File encoding error in {file_path}: {str(e)}")
        raise UnicodeDecodeError(
            e.encoding,
            e.object,
            e.start,
            e.end,
            f"File must be UTF-8 encoded: {file_path}"
        )
    except Exception as e:
        logger.error(f"Unexpected error reading {file_path}: {str(e)}")
        raise

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
        - Processes speakers and dialogue separately

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
        
        # Split into acts first if needed
        acts = split_acts(text) if self.config.remove_scene_headers else {0: text}
        
        cleaned_lines = []
        speakers = set()
        
        for act_num, act_content in acts.items():
            for line in act_content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Remove stage directions if configured
                if self.config.remove_stage_directions:
                    line = re.sub(r'\[.*?\]', '', line)
                
                # Extract and process speaker/dialogue
                speaker, dialogue = extract_speaker(line)
                if speaker:
                    speakers.add(speaker)
                    if self.config.preserve_character_names:
                        cleaned_lines.append(f"{speaker}. {dialogue}")
                    else:
                        cleaned_lines.append(dialogue)
                else:
                    # Skip scene headers if configured
                    if self.config.remove_scene_headers and re.match(r'SCENE [IVX]+', line):
                        continue
                    cleaned_lines.append(line)
        
        # Join and normalize
        text = ' '.join(cleaned_lines)
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        
        self.logger.debug(
            f"Text cleaning completed with config: {vars(self.config)}\n"
            f"Found {len(speakers)} unique speakers"
        )
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
