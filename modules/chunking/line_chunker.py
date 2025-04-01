"""
Line chunker module for Shakespeare AI project.

This module provides functionality to chunk Shakespeare's text into full lines,
preserving comprehensive line metadata including POS tags, syllable counts, and word indexing.
Uses spaCy for tokenization and POS tagging.
"""
import re
import time
import os
import json
from typing import List, Dict, Any, Tuple, Optional, Set
from .base import ChunkBase
from modules.utils.logger import CustomLogger

# Check for spaCy availability
try:
    import spacy
    # Load a small English model for efficient processing
    # To install: pip install spacy && python -m spacy download en_core_web_sm
    try:
        nlp = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except OSError:
        # If the model isn't downloaded yet, we'll use a simple fallback
        SPACY_AVAILABLE = False
except ImportError:
    SPACY_AVAILABLE = False


class LineChunker(ChunkBase):
    """Chunker for processing Shakespeare's text into full lines.
    
    This chunker splits text into individual lines, handling act/scene markers
    and maintaining comprehensive metadata.
    """
    
    def __init__(self, logger: Optional[CustomLogger] = None):
        """Initialize the LineChunker."""
        super().__init__(chunk_type='line')
        self.logger = logger or CustomLogger("LineChunker")
        self.logger.info("Initializing LineChunker")
        
        if not SPACY_AVAILABLE:
            self.logger.warning("spaCy is not available - using fallback tokenization")
            self.logger.info("To install spaCy: pip install spacy && python -m spacy download en_core_web_sm")
        
        # Regular expressions for detecting structural elements
        self.act_pattern = re.compile(r'^ACT\s+([IVX]+)', re.IGNORECASE)
        
        # Updated scene pattern to handle both "SCENE I" and "SCENE PROLOGUE"
        self.scene_pattern = re.compile(r'^SCENE\s+((?:PROLOGUE|[IVX]+))', re.IGNORECASE)
        
        # New pattern for sonnets (lines with just a number)
        self.sonnet_number_pattern = re.compile(r'^(\d+)$')
        
        # Pattern to detect all-caps structural lines
        self.all_caps_pattern = re.compile(r'^[A-Z\s.,;:!?]+$')
        
        # List of Shakespeare's work titles for better title detection
        self.shakespeare_titles = {
            "THE SONNETS",
            "ALL'S WELL THAT ENDS WELL",
            "THE TRAGEDY OF ANTONY AND CLEOPATRA",
            "AS YOU LIKE IT",
            "THE COMEDY OF ERRORS",
            "THE TRAGEDY OF CORIOLANUS",
            "CYMBELINE",
            "THE TRAGEDY OF HAMLET, PRINCE OF DENMARK",
            "THE FIRST PART OF KING HENRY THE FOURTH",
            "THE SECOND PART OF KING HENRY THE FOURTH",
            "THE LIFE OF KING HENRY THE FIFTH",
            "THE FIRST PART OF HENRY THE SIXTH",
            "THE SECOND PART OF KING HENRY THE SIXTH",
            "THE THIRD PART OF KING HENRY THE SIXTH",
            "KING HENRY THE EIGHTH",
            "THE LIFE AND DEATH OF KING JOHN",
            "THE TRAGEDY OF JULIUS CAESAR",
            "THE TRAGEDY OF KING LEAR",
            "LOVE'S LABOUR'S LOST",
            "THE TRAGEDY OF MACBETH",
            "MEASURE FOR MEASURE",
            "THE MERCHANT OF VENICE",
            "THE MERRY WIVES OF WINDSOR",
            "A MIDSUMMER NIGHT'S DREAM",
            "MUCH ADO ABOUT NOTHING",
            "THE TRAGEDY OF OTHELLO, THE MOOR OF VENICE",
            "PERICLES, PRINCE OF TYRE",
            "KING RICHARD THE SECOND",
            "KING RICHARD THE THIRD",
            "THE TRAGEDY OF ROMEO AND JULIET",
            "THE TAMING OF THE SHREW",
            "THE TEMPEST",
            "THE LIFE OF TIMON OF ATHENS",
            "THE TRAGEDY OF TITUS ANDRONICUS",
            "TROILUS AND CRESSIDA",
            "TWELFTH NIGHT; OR, WHAT YOU WILL",
            "THE TWO GENTLEMEN OF VERONA",
            "THE TWO NOBLE KINSMEN",
            "THE WINTER'S TALE",
            "A LOVER'S COMPLAINT",
            "THE PASSIONATE PILGRIM",
            "THE PHOENIX AND THE TURTLE",
            "THE RAPE OF LUCRECE",
            "VENUS AND ADONIS"
        }
        
        self.logger.debug("Compiled regular expressions for text parsing")
        
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word using a rule-based approach."""
        word = word.lower()
        # Exception cases
        if len(word) <= 3:
            return 1
            
        # Remove trailing e's which are often silent
        if word.endswith('e'):
            word = word[:-1]
            
        # Count vowel groups
        syllables = len(re.findall(r'[aeiouy]+', word))
        
        # Ensure at least one syllable
        return max(1, syllables)
    
    def _process_line_with_spacy(self, line: str) -> Tuple[List[str], List[str], int]:
        """Process a line using spaCy for tokenization and POS tagging."""
        if not SPACY_AVAILABLE:
            # Fallback to simple tokenization
            words = line.split()
            return words, [""] * len(words), len(words)
            
        try:
            # Process the line with spaCy
            doc = nlp(line)
            
            # Extract words and POS tags
            words = [token.text for token in doc]
            pos_tags = [token.pos_ for token in doc]
            
            return words, pos_tags, len(words)
        except Exception as e:
            self.logger.error(f"Error processing with spaCy: {str(e)}")
            # Fallback to simple tokenization
            words = line.split()
            return words, [""] * len(words), len(words)
    
    def _detect_title(self, lines: List[str]) -> str:
        """Detect the title from the beginning of the text.
        
        Args:
            lines (List[str]): The text split into lines
            
        Returns:
            str: The detected title or "Unknown"
        """
        # Try to find a title from our list in the first few lines
        for i in range(min(10, len(lines))):
            line = lines[i].strip()
            if line in self.shakespeare_titles:
                self.logger.info(f"Detected title: {line}")
                return line
        
        # Fallback: try to use the first non-empty line
        for line in lines:
            if line.strip():
                self.logger.warning(f"Using first line as title: {line.strip()}")
                return line.strip()
                
        return "Unknown"
    
    def _is_structural_line(self, line: str) -> bool:
        """Detect if a line is a structural element (title, act, scene, etc.).
        
        Args:
            line (str): The line to check
            
        Returns:
            bool: True if it's a structural line, False otherwise
        """
        # Check if the line is an act, scene, or sonnet marker
        if (self.act_pattern.match(line) or 
            self.scene_pattern.match(line) or 
            self.sonnet_number_pattern.match(line)):
            return True
        
        # Check if the line is all caps (likely a structural element)
        if self.all_caps_pattern.match(line):
            return True
            
        return False
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split the play text into individual lines with comprehensive metadata.
        
        Args:
            text (str): The play text to process
            
        Returns:
            List[Dict[str, Any]]: List of line chunks with metadata including POS tags,
                                syllable counts, and word indexing
        """
        start_time = time.time()
        self.logger.info("Starting text chunking process")
        self.logger.debug(f"Input text length: {len(text)} characters")
        
        lines = text.strip().split('\n')
        self.logger.debug(f"Split text into {len(lines)} raw lines")
        
        # Detect the title from the beginning of the text
        title = self._detect_title(lines)
        
        chunks = []
        
        current_act = None
        current_scene = None
        line_index = 0  # Only incremented for spoken text lines
        
        for line_no, line in enumerate(lines):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            # Skip the title line
            if line == title:
                continue
            
            # Check for act markers
            act_match = self.act_pattern.match(line)
            if act_match:
                current_act = act_match.group(1)
                current_scene = None  # Reset scene when act changes
                self.logger.info(f"Detected Act {current_act}")
                continue
            
            # Check for scene markers with updated pattern to handle PROLOGUE
            scene_match = self.scene_pattern.match(line)
            if scene_match:
                scene_identifier = scene_match.group(1)
                # Check if the scene is a prologue or a regular scene
                if scene_identifier.upper() == "PROLOGUE":
                    current_scene = "PROLOGUE"
                else:
                    # Keep Roman numeral format as is
                    current_scene = scene_identifier
                self.logger.info(f"Detected Scene {current_scene} in Act {current_act}")
                continue
            
            # Check for sonnet numbers (single number on a line)
            sonnet_match = self.sonnet_number_pattern.match(line)
            if sonnet_match:
                current_act = sonnet_match.group(1)  # Use the sonnet number as the act
                current_scene = ""  # Empty scene for sonnets
                self.logger.info(f"Detected Sonnet {current_act}")
                continue
            
            # Skip other structural lines (all caps)
            if self._is_structural_line(line):
                self.logger.debug(f"Skipping structural line: {line}")
                continue
            
            # Process text line
            line_index += 1  # Increment line counter
            
            # Process the line with spaCy for accurate word tokenization and POS tagging
            words, pos_tags, word_count = self._process_line_with_spacy(line)
            
            # Calculate total syllables
            total_syllables = sum(self._count_syllables(word) for word in words)
            
            # Create the chunk with metadata
            chunk = {
                'chunk_id': f'line_{line_index}',
                'title': title,
                'text': line,
                'line': line_index,  # Line number among spoken text lines only
                'act': current_act,
                'scene': current_scene,
                'word_index': f"0,{word_count-1}",  # Each line starts at 0
                'syllables': total_syllables,
                'POS': pos_tags,
                'mood': 'neutral',  # Default mood - could be enhanced with sentiment analysis
                'word_count': word_count
            }
            chunks.append(chunk)
            self.logger.debug(
                f"Created chunk {chunk['chunk_id']}: "
                f"{len(line)} chars, {chunk['word_count']} words"
            )
        
        end_time = time.time()
        processing_time = end_time - start_time
        self.logger.info(
            f"Completed text chunking: {len(chunks)} chunks created "
            f"in {processing_time:.2f} seconds"
        )
        
        # Save the chunks to the instance variable
        self.chunks = chunks
        
        return chunks
    
    def get_lines_by_act_scene(self, act: str, scene: str) -> List[Dict[str, Any]]:
        """Get all lines from a specific act and scene.
        
        Args:
            act (str): The act number (e.g., 'I', 'V', or a sonnet number like '1')
            scene (str): The scene number (e.g., 'I', 'III', or empty for sonnets)
            
        Returns:
            List[Dict[str, Any]]: List of line chunks from the specified act and scene
        """
        self.logger.debug(f"Retrieving lines for Act {act}, Scene {scene}")
        
        if not hasattr(self, 'chunks') or not self.chunks:
            self.logger.warning("No chunks available. Process text first.")
            return []
            
        act_scene_lines = [
            chunk for chunk in self.chunks 
            if chunk.get('act') == act and chunk.get('scene') == scene
        ]
        self.logger.info(f"Found {len(act_scene_lines)} lines in Act {act}, Scene {scene}")
        return act_scene_lines

    def get_dialogue_exchange(self, start_index: int, max_lines: int = 10) -> List[Dict[str, Any]]:
        """Get a dialogue exchange starting from a specific line.
        
        Args:
            start_index (int): The starting line index (0-based)
            max_lines (int): Maximum number of lines to include
            
        Returns:
            List[Dict[str, Any]]: List of consecutive line chunks
        """
        self.logger.debug(
            f"Retrieving dialogue exchange from index {start_index}, "
            f"max {max_lines} lines"
        )
        
        if not hasattr(self, 'chunks') or not self.chunks:
            self.logger.warning("No chunks available. Process text first.")
            return []
        
        # Adjust for 0-based indexing    
        if start_index < 0 or start_index >= len(self.chunks):
            self.logger.warning(
                f"Invalid start_index {start_index} for chunks of length {len(self.chunks)}"
            )
            return []
        
        end_idx = min(start_index + max_lines, len(self.chunks))
        exchange = self.chunks[start_index:end_idx]
        self.logger.info(
            f"Retrieved {len(exchange)} lines of dialogue exchange"
        )
        return exchange
    
    def get_sonnet_lines(self, sonnet_number: str) -> List[Dict[str, Any]]:
        """Get all lines from a specific sonnet.
        
        Args:
            sonnet_number (str): The sonnet number (e.g., '1', '18', '116')
            
        Returns:
            List[Dict[str, Any]]: List of line chunks from the specified sonnet
        """
        self.logger.debug(f"Retrieving lines for Sonnet {sonnet_number}")
        
        if not hasattr(self, 'chunks') or not self.chunks:
            self.logger.warning("No chunks available. Process text first.")
            return []
            
        sonnet_lines = [
            chunk for chunk in self.chunks 
            if chunk.get('act') == sonnet_number and chunk.get('scene') == ""
        ]
        self.logger.info(f"Found {len(sonnet_lines)} lines in Sonnet {sonnet_number}")
        return sonnet_lines

    
# If run as a standalone script, process input file and save as JSON
if __name__ == "__main__":
    # Set these paths directly in the script
    input_file = "data/processed_texts/complete_shakespeare_ready.txt"
    output_file = "data/processed_chunks/line_chunks.json"
    
    # Set up logger
    logger = CustomLogger("LineChunkerMain", log_level="INFO")
    
    try:
        # Create the chunker
        chunker = LineChunker(logger=logger)
        
        # Read the input file
        logger.info(f"Reading input file: {input_file}")
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()
        except FileNotFoundError:
            logger.critical(f"Input file not found: {input_file}")
            exit(1)
        except Exception as e:
            logger.critical(f"Error reading input file: {str(e)}")
            exit(1)
        
        # Process the text
        logger.info("Processing text...")
        chunks = chunker.chunk_text(text)
        logger.info(f"Generated {len(chunks)} chunks")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")
        
        # Save to JSON
        logger.info(f"Saving chunks to: {output_file}")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'chunk_type': 'line',
                    'chunks': chunks,
                    'total_chunks': len(chunks)
                }, f, indent=2)
            logger.info("Chunks saved successfully!")
            
            # Print summary
            acts_scenes = {}
            for chunk in chunks:
                act = chunk.get('act')
                scene = chunk.get('scene')
                key = f"Act {act}, Scene {scene}"
                acts_scenes[key] = acts_scenes.get(key, 0) + 1
            
            logger.info("Summary of chunks by Act/Scene:")
            for key, count in acts_scenes.items():
                logger.info(f"  {key}: {count} lines")
            
        except Exception as e:
            logger.critical(f"Error saving output file: {str(e)}")
            exit(1)
        
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        exit(1)