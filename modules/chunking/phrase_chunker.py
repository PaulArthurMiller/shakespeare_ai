"""
Phrase chunker module for Shakespeare AI project.

This module provides functionality to chunk Shakespeare's text into phrases
based on punctuation breaks, preserving the relationship to parent lines.
"""
import re
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


class PhraseChunker(ChunkBase):
    """Chunker for processing Shakespeare's text into phrases.
    
    This chunker splits text based on punctuation breaks (periods, commas, etc.)
    and maintains the relationship to the original line.
    """
    
    def __init__(self, logger: Optional[CustomLogger] = None):
        """Initialize the PhraseChunker."""
        super().__init__(chunk_type='phrase')
        self.logger = logger or CustomLogger("PhraseChunker")
        self.logger.info("Initializing PhraseChunker")
        
        if not NLTK_AVAILABLE:
            self.logger.critical("NLTK is not available")
            raise ImportError(
                "NLTK is required for PhraseChunker. "
                "Install it with: pip install nltk"
            )
        
        # Pattern for splitting on major punctuation but keeping the punctuation
        self.phrase_pattern = re.compile(r'([.!?;:])')
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
        """Split the play text into phrases based on punctuation.
        
        Args:
            text (str): The play text to process
            
        Returns:
            List[Dict[str, Any]]: List of phrase chunks with metadata
        """
        self.logger.info("Starting text chunking process")
        self.logger.debug(f"Input text length: {len(text)} characters")
        
        # Extract title from first line
        title_match = self.title_pattern.match(text)
        title = title_match.group(1).strip() if title_match else "Unknown"
        
        # Initialize tracking variables
        current_act = None
        current_scene = None
        current_speaker = None
        word_index = 0  # Global word index counter
        
        # This method assumes we're working with the output of LineChunker
        # or at least text that has been pre-processed into lines
        lines = text.strip().split('\n')
        self.logger.debug(f"Split text into {len(lines)} raw lines")
        chunks = []
        
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Split the line into phrases based on punctuation
            # First, split on major breaks
            major_parts = self.phrase_pattern.split(line)
            
            # Recombine the punctuation with the preceding text
            phrases = []
            i = 0
            while i < len(major_parts):
                if i + 1 < len(major_parts) and re.match(self.phrase_pattern, major_parts[i + 1]):
                    phrases.append(major_parts[i] + major_parts[i + 1])
                    i += 2
                else:
                    if major_parts[i]:  # Only add non-empty parts
                        phrases.append(major_parts[i])
                    i += 1
            
            # Further split on commas
            final_phrases = []
            for phrase in phrases:
                comma_parts = phrase.split(',')
                for i, part in enumerate(comma_parts):
                    if i < len(comma_parts) - 1:
                        final_phrases.append(part.strip() + ',')
                    else:
                        final_phrases.append(part.strip())
            
            # Process the full line first to get total word positions
            full_line_words = word_tokenize(line)
            
            # Create chunks for each phrase
            for phrase_idx, phrase in enumerate(final_phrases):
                phrase = phrase.strip()
                if not phrase:
                    continue
                
                self.logger.debug(f"Processing phrase {phrase_idx + 1}/{len(final_phrases)} from line {line_idx}")
                # Process the phrase for POS and syllables
                phrase_words = word_tokenize(phrase)
                pos_tags = pos_tag(phrase_words)
                total_syllables = sum(self._count_syllables(word) for word in phrase_words)
                
                # Find where this phrase starts in the full line
                phrase_start = -1
                for i in range(len(full_line_words) - len(phrase_words) + 1):
                    if full_line_words[i:i+len(phrase_words)] == phrase_words:
                        phrase_start = i
                        break
                
                if phrase_start == -1:
                    self.logger.warning(f"Could not find phrase position in line: {phrase}")
                    continue
                
                # Create the chunk with comprehensive metadata
                chunk = {
                    'chunk_id': f'phrase_{line_idx}_{phrase_idx}',
                    'title': title,
                    'text': phrase,
                    'line': line_idx,
                    'act': current_act,
                    'scene': current_scene,
                    'word_index': f"{phrase_start},{phrase_start + len(phrase_words) - 1}",
                    'syllables': total_syllables,
                    'POS': [tag for _, tag in pos_tags],
                    'mood': 'neutral',  # Default mood - could be enhanced with sentiment analysis
                    'speaker': current_speaker,
                    'phrase_position': phrase_idx,
                    'total_phrases_in_line': len(final_phrases),
                    'ends_with_punctuation': bool(re.search(r'[.!?;:,]$', phrase))
                }
                chunks.append(chunk)
                self.logger.debug(
                    f"Created chunk {chunk['chunk_id']}: "
                    f"{len(phrase)} chars, {chunk['word_count']} words"
                )
        
        self.logger.info(f"Completed text chunking: created {len(chunks)} phrase chunks")
        return chunks
    
    def chunk_from_line_chunks(self, line_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create phrase chunks from previously processed line chunks.
        
        Args:
            line_chunks (List[Dict[str, Any]]): List of line chunks from LineChunker
            
        Returns:
            List[Dict[str, Any]]: List of phrase chunks with metadata
        """
        self.logger.info("Starting phrase chunking from line chunks")
        self.logger.debug(f"Processing {len(line_chunks)} line chunks")
        chunks = []
        word_index = 0  # Global word index counter
        
        for line_chunk in line_chunks:
            line_text = line_chunk['text']
            line_id = line_chunk['chunk_id']
            
            # Split into phrases using the same logic as chunk_text
            major_parts = self.phrase_pattern.split(line_text)
            
            # Recombine the punctuation with the preceding text
            phrases = []
            i = 0
            while i < len(major_parts):
                if i + 1 < len(major_parts) and re.match(self.phrase_pattern, major_parts[i + 1]):
                    phrases.append(major_parts[i] + major_parts[i + 1])
                    i += 2
                else:
                    if major_parts[i]:  # Only add non-empty parts
                        phrases.append(major_parts[i])
                    i += 1
            
            # Further split on commas
            final_phrases = []
            for phrase in phrases:
                comma_parts = phrase.split(',')
                for i, part in enumerate(comma_parts):
                    if i < len(comma_parts) - 1:
                        final_phrases.append(part.strip() + ',')
                    else:
                        final_phrases.append(part.strip())
            
            # Process the full line first to get total word positions
            full_line_words = word_tokenize(line_chunk['text'])
            
            # Create chunks for each phrase
            for phrase_idx, phrase in enumerate(final_phrases):
                phrase = phrase.strip()
                if not phrase:
                    continue
                
                # Process the phrase for POS and syllables
                phrase_words = word_tokenize(phrase)
                pos_tags = pos_tag(phrase_words)
                total_syllables = sum(self._count_syllables(word) for word in phrase_words)
                
                # Find where this phrase starts in the full line
                phrase_start = -1
                for i in range(len(full_line_words) - len(phrase_words) + 1):
                    if full_line_words[i:i+len(phrase_words)] == phrase_words:
                        phrase_start = i
                        break
                
                if phrase_start == -1:
                    self.logger.warning(f"Could not find phrase position in line: {phrase}")
                    continue
                
                chunk = {
                    'chunk_id': f'phrase_{line_id}_{phrase_idx}',
                    'title': line_chunk.get('title', 'Unknown'),
                    'text': phrase,
                    'line': line_chunk.get('line'),
                    'act': line_chunk.get('act'),
                    'scene': line_chunk.get('scene'),
                    'word_index': f"{phrase_start},{phrase_start + len(phrase_words) - 1}",
                    'syllables': total_syllables,
                    'POS': [tag for _, tag in pos_tags],
                    'mood': line_chunk.get('mood', 'neutral'),
                    'speaker': line_chunk.get('speaker'),
                    'phrase_position': phrase_idx,
                    'total_phrases_in_line': len(final_phrases),
                    'ends_with_punctuation': bool(re.search(r'[.!?;:,]$', phrase))
                }
                chunks.append(chunk)
                self.logger.debug(
                    f"Created phrase chunk {chunk['chunk_id']} from line {line_id}: "
                    f"{len(phrase)} chars, {chunk['word_count']} words"
                )
        
        self.logger.info(f"Completed phrase chunking: created {len(chunks)} chunks from line chunks")
        return chunks
    
    def get_phrases_by_parent_line(self, parent_line_id: str) -> List[Dict[str, Any]]:
        """Get all phrases that belong to a specific parent line.
        
        Args:
            parent_line_id (str): The ID of the parent line
            
        Returns:
            List[Dict[str, Any]]: List of phrase chunks for the specified parent line
        """
        self.logger.debug(f"Retrieving phrases for parent line: {parent_line_id}")
        phrases = [
            chunk for chunk in self.chunks 
            if chunk.get('parent_line_id') == parent_line_id
        ]
        self.logger.info(f"Found {len(phrases)} phrases for parent line {parent_line_id}")
        return phrases
    
    def get_phrases_with_punctuation(self, punctuation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get phrases that end with specific punctuation or all punctuated phrases.
        
        Args:
            punctuation_type (Optional[str]): Specific punctuation mark to filter by (e.g., '.', '!', '?', ';', ':').
                                            If None, returns all phrases ending with any punctuation.
            
        Returns:
            List[Dict[str, Any]]: List of phrase chunks with the specified punctuation
            
        Examples:
            >>> chunker.get_phrases_with_punctuation('.')  # Get all phrases ending with periods
            >>> chunker.get_phrases_with_punctuation('!')  # Get all exclamatory phrases
            >>> chunker.get_phrases_with_punctuation()     # Get all punctuated phrases
        """
        valid_punct = {'.', '!', '?', ';', ':', ','}
        
        if punctuation_type and punctuation_type not in valid_punct:
            self.logger.warning(
                f"Invalid punctuation type '{punctuation_type}'. "
                f"Valid types are: {', '.join(sorted(valid_punct))}"
            )
            return []
            
        self.logger.debug(
            f"Retrieving phrases with punctuation: "
            f"{'any' if punctuation_type is None else punctuation_type}"
        )
        
        try:
            if punctuation_type:
                phrases = [
                    chunk for chunk in self.chunks 
                    if chunk.get('text', '').strip().endswith(punctuation_type)
                ]
                self.logger.info(
                    f"Found {len(phrases)} phrases ending with '{punctuation_type}'"
                )
            else:
                phrases = [
                    chunk for chunk in self.chunks 
                    if chunk.get('ends_with_punctuation', False)
                ]
                self.logger.info(f"Found {len(phrases)} phrases with punctuation")
            
            return phrases
            
        except Exception as e:
            self.logger.error(f"Error retrieving punctuated phrases: {str(e)}")
            return []
