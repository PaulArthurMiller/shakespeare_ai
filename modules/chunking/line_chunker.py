"""
Line chunker module for Shakespeare AI project.

This module provides functionality to chunk Shakespeare's text into full lines,
preserving speaker information and comprehensive line metadata including POS tags,
syllable counts, and word indexing.
"""
import re
import time
from typing import List, Dict, Any, Tuple, Optional
from .base import ChunkBase
from modules.utils.logger import CustomLogger

try:
    import nltk
    from nltk import pos_tag, word_tokenize
    from nltk.corpus import cmudict
    NLTK_AVAILABLE = True
    # Initialize CMU dictionary for syllable counting
    d = cmudict.dict()
except ImportError:
    NLTK_AVAILABLE = False


class LineChunker(ChunkBase):
    """Chunker for processing Shakespeare's text into full lines.
    
    This chunker splits text into individual lines, handling speaker labels and
    maintaining act/scene structure information.
    """
    
    def __init__(self, logger: Optional[CustomLogger] = None):
        """Initialize the LineChunker."""
        super().__init__(chunk_type='line')
        self.logger = logger or CustomLogger("LineChunker")
        self.logger.info("Initializing LineChunker")
        
        if not NLTK_AVAILABLE:
            self.logger.critical("NLTK is not available")
            raise ImportError(
                "NLTK is required for LineChunker. "
                "Install it with: pip install nltk"
            )
        
        # Regular expressions for detecting structural elements
        self.act_pattern = re.compile(r'^ACT\s+([IVX]+)', re.IGNORECASE)
        self.scene_pattern = re.compile(r'^SCENE\s+([IVX]+)', re.IGNORECASE)
        self.speaker_pattern = re.compile(r'^([A-Z][A-Z\s]+)\.(.*?)$')
        self.title_pattern = re.compile(r'^(.*?)\n', re.MULTILINE)
        self.logger.debug("Compiled regular expressions for text parsing")
        
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word using CMU dictionary."""
        word = word.lower()
        try:
            return max([len([y for y in x if y[-1].isdigit()]) for x in d[word]])
        except KeyError:
            # Fallback: rough estimate based on vowel groups
            return len(re.findall(r'[aeiouy]+', word))
    
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
        
        # Extract title from first line
        title_match = self.title_pattern.match(text)
        title = title_match.group(1).strip() if title_match else "Unknown"
        
        lines = text.strip().split('\n')
        self.logger.debug(f"Split text into {len(lines)} raw lines")
        chunks = []
        
        current_act = None
        current_scene = None
        current_speaker = None
        line_index = 0
        word_index = 0  # Global word index counter
        
        for line_no, line in enumerate(lines):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            # Check for act markers
            act_match = self.act_pattern.match(line)
            if act_match:
                current_act = act_match.group(1)
                current_scene = None  # Reset scene when act changes
                self.logger.info(f"Detected Act {current_act}")
                continue
            
            # Check for scene markers
            scene_match = self.scene_pattern.match(line)
            if scene_match:
                current_scene = scene_match.group(1)
                self.logger.info(f"Detected Scene {current_scene} in Act {current_act}")
                continue
            
            # Skip stage directions and empty lines
            if line.startswith('(') or line.startswith('['):
                continue
                
            # Check for speaker and dialogue
            speaker_match = self.speaker_pattern.match(line)
            if speaker_match:
                current_speaker = speaker_match.group(1).strip()
                dialogue = speaker_match.group(2).strip()
                if dialogue:  # Only add if there's actual dialogue
                    self.logger.debug(f"Speaker detected: {current_speaker}")
                    # Increment line index only for dialogue lines
                    line_index += 1
                    # Process the dialogue for POS and syllables
                    words = word_tokenize(dialogue)
                    pos_tags = pos_tag(words)
                    
                    # Calculate word index range
                    start_index = word_index
                    word_index += len(words)
                    
                    # Calculate total syllables
                    total_syllables = sum(self._count_syllables(word) for word in words)
                    
                    # Create the chunk with comprehensive metadata
                    chunk = {
                        'chunk_id': f'line_{line_index}',
                        'title': title,
                        'text': dialogue,
                        'line': line_index,  # Use dialogue line numbering
                        'act': current_act,
                        'scene': current_scene,
                        'word_index': f"{start_index},{word_index-1}",
                        'syllables': total_syllables,
                        'POS': [tag for _, tag in pos_tags],
                        'mood': 'neutral',  # Default mood - could be enhanced with sentiment analysis
                        'speaker': current_speaker
                    }
                    chunks.append(chunk)
                    self.logger.debug(
                        f"Created chunk {chunk['chunk_id']}: "
                        f"{len(dialogue)} chars, {chunk['word_count']} words"
                    )
            elif current_speaker and line.strip():  # Continued dialogue
                self.logger.debug(f"Continued dialogue from {current_speaker}")
                line_index += 1
                
                # Process the dialogue for POS and syllables
                words = word_tokenize(line.strip())
                pos_tags = pos_tag(words)
                total_syllables = sum(self._count_syllables(word) for word in words)
                
                # Calculate word index range
                start_index = word_index
                word_index += len(words)
                
                chunk = {
                    'chunk_id': f'line_{line_index}',
                    'title': title,
                    'text': line.strip(),
                    'line': line_index,
                    'act': current_act,
                    'scene': current_scene,
                    'word_index': f"{start_index},{word_index-1}",
                    'syllables': total_syllables,
                    'POS': [tag for _, tag in pos_tags],
                    'mood': 'neutral',
                    'speaker': current_speaker
                }
                chunks.append(chunk)
                self.logger.debug(
                    f"Created chunk {chunk['chunk_id']}: "
                    f"{len(dialogue)} chars, {chunk['word_count']} words"
                )
        
        end_time = time.time()
        processing_time = end_time - start_time
        self.logger.info(
            f"Completed text chunking: {len(chunks)} chunks created "
            f"in {processing_time:.2f} seconds"
        )
        return chunks
    
    def get_speaker_lines(self, speaker: str) -> List[Dict[str, Any]]:
        """Get all lines for a specific speaker.
        
        Args:
            speaker (str): The speaker name to filter by
            
        Returns:
            List[Dict[str, Any]]: List of line chunks for the specified speaker
        """
        self.logger.debug(f"Retrieving lines for speaker: {speaker}")
        speaker_lines = [chunk for chunk in self.chunks if chunk.get('speaker') == speaker]
        self.logger.info(f"Found {len(speaker_lines)} lines for speaker {speaker}")
        return speaker_lines
    
    def get_lines_by_act_scene(self, act: str, scene: str) -> List[Dict[str, Any]]:
        """Get all lines from a specific act and scene.
        
        Args:
            act (str): The act number (e.g., 'I', 'V')
            scene (str): The scene number (e.g., 'I', 'III')
            
        Returns:
            List[Dict[str, Any]]: List of line chunks from the specified act and scene
        """
        self.logger.debug(f"Retrieving lines for Act {act}, Scene {scene}")
        # Store chunks in instance variable if not already done
        if not hasattr(self, 'chunks'):
            self.chunks = []
            
        act_scene_lines = [
            chunk for chunk in self.chunks 
            if chunk.get('act') == act and chunk.get('scene') == scene
        ]
        self.logger.info(f"Found {len(act_scene_lines)} lines in Act {act}, Scene {scene}")
        return act_scene_lines
    
    def get_dialogue_exchange(self, start_index: int, max_lines: int = 10) -> List[Dict[str, Any]]:
        """Get a dialogue exchange starting from a specific line.
        
        Args:
            start_index (int): The starting line index (1-based)
            max_lines (int): Maximum number of lines to include
            
        Returns:
            List[Dict[str, Any]]: List of consecutive line chunks
        """
        self.logger.debug(
            f"Retrieving dialogue exchange from index {start_index}, "
            f"max {max_lines} lines"
        )
        
        # Convert 1-based start_index to 0-based for internal use
        start_idx = start_index - 1
        
        # Store chunks in instance variable if not already done
        if not hasattr(self, 'chunks'):
            self.chunks = []
            
        if not self.chunks or start_idx < 0 or start_idx >= len(self.chunks):
            self.logger.warning(
                f"Invalid start_index {start_index} for chunks of length {len(self.chunks)}"
            )
            return []
        
        end_idx = min(start_idx + max_lines, len(self.chunks))
        exchange = self.chunks[start_idx:end_idx]
        self.logger.info(
            f"Retrieved {len(exchange)} lines of dialogue exchange"
        )
        return exchange
