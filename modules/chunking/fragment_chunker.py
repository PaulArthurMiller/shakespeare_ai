"""
Fragment chunker module for Shakespeare AI project.

This module provides functionality to chunk Shakespeare's text into small
fragments (3-6 words) based on Part-of-Speech patterns, which can be
used for fine-grained retrieval and composition.
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from .base import ChunkBase
from modules.utils.logger import CustomLogger

# This module will need NLTK for POS tagging
# Make sure to install it with: pip install nltk
# And download required data with:
# import nltk
# nltk.download('punkt')
# nltk.download('averaged_perceptron_tagger')
try:
    import nltk
    from nltk import pos_tag, word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


class FragmentChunker(ChunkBase):
    """Chunker for processing Shakespeare's text into small word fragments.
    
    This chunker creates 3-6 word fragments based on POS patterns,
    maintaining relationships to parent phrases and lines.
    """
    
    def __init__(self, min_words: int = 3, max_words: int = 6, logger: Optional[CustomLogger] = None):
        """Initialize the FragmentChunker.
        
        Args:
            min_words (int): Minimum number of words in a fragment
            max_words (int): Maximum number of words in a fragment
            logger (Optional[CustomLogger]): Logger instance for this chunker
        """
        super().__init__(chunk_type='fragment')
        self.logger = logger or CustomLogger("FragmentChunker")
        self.logger.info("Initializing FragmentChunker")
        
        self.min_words = min_words
        self.max_words = max_words
        self.logger.debug(f"Set word limits: min={min_words}, max={max_words}")
        
        if not NLTK_AVAILABLE:
            self.logger.critical("NLTK is not available")
            raise ImportError(
                "NLTK is required for FragmentChunker. "
                "Install it with: pip install nltk"
            )
            
        # Initialize CMU dictionary for syllable counting
        try:
            from nltk.corpus import cmudict
            self.d = cmudict.dict()
        except ImportError:
            self.logger.warning("CMU Dictionary not available - using fallback syllable counting")
            self.d = None
            
        self.title_pattern = re.compile(r'^(.*?)\n', re.MULTILINE)
        self.logger.debug("NLTK availability confirmed")
        
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word using CMU dictionary."""
        word = word.lower()
        try:
            if self.d:
                return max([len([y for y in x if y[-1].isdigit()]) for x in self.d[word]])
        except KeyError:
            pass
        # Fallback: rough estimate based on vowel groups
        return len(re.findall(r'[aeiouy]+', word))
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split the text into small fragments based on POS patterns.
        
        Args:
            text (str): The text to process
            
        Returns:
            List[Dict[str, Any]]: List of fragment chunks with metadata
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
        
        # This method works best with lines or phrases as input
        lines = text.strip().split('\n')
        self.logger.debug(f"Split text into {len(lines)} raw lines")
        chunks = []
        
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Create fragments for this line
            line_fragments = self._create_fragments_from_text(line)
            
            # Add metadata and collect all fragments
            for frag_idx, fragment in enumerate(line_fragments):
                # Calculate word indices for this fragment within the line
                line_words = word_tokenize(line)
                fragment_words = word_tokenize(fragment['text'])
                fragment_start = -1
                
                # Find where this fragment starts in the full line
                for i in range(len(line_words) - len(fragment_words) + 1):
                    if line_words[i:i+len(fragment_words)] == fragment_words:
                        fragment_start = i
                        break
                
                if fragment_start == -1:
                    self.logger.warning(f"Could not find fragment position in line: {fragment['text']}")
                    continue
                
                # Calculate syllables
                total_syllables = sum(self._count_syllables(word) for word in fragment_words)
                
                chunk = {
                    'chunk_id': f'fragment_{line_idx}_{frag_idx}',
                    'title': title,
                    'text': fragment['text'],
                    'line': line_idx,
                    'act': current_act,
                    'scene': current_scene,
                    'word_index': f"{fragment_start},{fragment_start + len(fragment_words) - 1}",
                    'syllables': total_syllables,
                    'POS': fragment['pos_tags'],
                    'mood': 'neutral',
                    'speaker': current_speaker,
                    'fragment_position': frag_idx,
                    'total_fragments_in_line': len(line_fragments)
                }
                chunks.append(chunk)
                self.logger.debug(
                    f"Created chunk {chunk['chunk_id']}: "
                    f"{len(chunk['text'])} chars, {chunk['word_count']} words"
                )
        
        self.logger.info(f"Completed text chunking: created {len(chunks)} fragment chunks")
        return chunks
    
    def chunk_from_phrase_chunks(self, phrase_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create fragment chunks from previously processed phrase chunks.
        
        Args:
            phrase_chunks (List[Dict[str, Any]]): List of phrase chunks from PhraseChunker
            
        Returns:
            List[Dict[str, Any]]: List of fragment chunks with metadata
        """
        self.logger.info("Starting fragment chunking from phrase chunks")
        self.logger.debug(f"Processing {len(phrase_chunks)} phrase chunks")
        chunks = []
        
        for phrase_chunk in phrase_chunks:
            phrase_text = phrase_chunk['text']
            phrase_id = phrase_chunk['chunk_id']
            parent_line_id = phrase_chunk.get('parent_line_id')
            
            # Create fragments for this phrase
            phrase_fragments = self._create_fragments_from_text(phrase_text)
            
            # Add metadata and collect all fragments
            for frag_idx, fragment in enumerate(phrase_fragments):
                # Calculate word indices for this fragment within the phrase
                phrase_words = word_tokenize(phrase_text)
                fragment_words = word_tokenize(fragment['text'])
                fragment_start = -1
                
                # Find where this fragment starts in the full phrase
                for i in range(len(phrase_words) - len(fragment_words) + 1):
                    if phrase_words[i:i+len(fragment_words)] == fragment_words:
                        fragment_start = i
                        break
                
                if fragment_start == -1:
                    self.logger.warning(f"Could not find fragment position in phrase: {fragment['text']}")
                    continue
                
                # Calculate syllables
                total_syllables = sum(self._count_syllables(word) for word in fragment_words)
                
                chunk = {
                    'chunk_id': f'fragment_{phrase_id}_{frag_idx}',
                    'title': phrase_chunk.get('title', 'Unknown'),
                    'text': fragment['text'],
                    'line': phrase_chunk.get('line'),
                    'act': phrase_chunk.get('act'),
                    'scene': phrase_chunk.get('scene'),
                    'word_index': f"{fragment_start},{fragment_start + len(fragment_words) - 1}",
                    'syllables': total_syllables,
                    'POS': fragment['pos_tags'],
                    'mood': phrase_chunk.get('mood', 'neutral'),
                    'speaker': phrase_chunk.get('speaker'),
                    'fragment_position': frag_idx,
                    'total_fragments_in_phrase': len(phrase_fragments)
                }
                chunks.append(chunk)
                self.logger.debug(
                    f"Created fragment chunk {chunk['chunk_id']} from phrase {phrase_id}: "
                    f"{len(chunk['text'])} chars, {chunk['word_count']} words"
                )
        
        self.logger.info(f"Completed fragment chunking: created {len(chunks)} chunks from phrases")
        return chunks
    
    def _create_fragments_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Create natural fragments from text based on POS patterns.
        
        This method uses POS tagging to identify linguistically coherent
        fragments of 3-6 words.
        
        Args:
            text (str): The text to fragment
            
        Returns:
            List[Dict[str, Any]]: List of fragment dictionaries with text and POS tags
        """
        self.logger.debug(f"Creating fragments from text: {len(text)} characters")
        
        # Tokenize and tag the text
        try:
            tokens = word_tokenize(text)
            tagged_tokens = pos_tag(tokens)
            self.logger.debug(f"Tagged {len(tokens)} tokens with POS tags")
        except Exception as e:
            self.logger.error(f"Error during tokenization/tagging: {str(e)}")
            return []
        
        fragments = []
        current_fragment = []
        current_tags = []
        
        # Define POS patterns that should not be broken
        # e.g., don't separate adjectives from their nouns
        noun_modifiers = ['JJ', 'JJR', 'JJS']  # Adjectives
        noun_tags = ['NN', 'NNS', 'NNP', 'NNPS']  # Nouns
        verb_modifiers = ['RB', 'RBR', 'RBS']  # Adverbs
        verb_tags = ['VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ']  # Verbs
        
        i = 0
        while i < len(tagged_tokens):
            word, tag = tagged_tokens[i]
            
            # Add the current token to the fragment
            current_fragment.append(word)
            current_tags.append(tag)
            
            # Check if we should create a fragment break
            create_break = False
            
            # If we've reached max words, create a break
            if len(current_fragment) >= self.max_words:
                create_break = True
            
            # If we've reached min words and found a good breaking point
            elif len(current_fragment) >= self.min_words:
                # Don't break if this is a noun modifier and next is a noun
                if (i < len(tagged_tokens) - 1 and 
                    tag in noun_modifiers and 
                    tagged_tokens[i+1][1] in noun_tags):
                    create_break = False
                # Don't break if this is an adverb and next is a verb
                elif (i < len(tagged_tokens) - 1 and 
                      tag in verb_modifiers and 
                      tagged_tokens[i+1][1] in verb_tags):
                    create_break = False
                # Good breaking points: after punctuation, at conjunctions, after nouns
                elif (word in ',.:;!?' or 
                      tag in ['CC'] or  # Coordinating conjunction
                      tag in noun_tags):
                    create_break = True
            
            # Create a fragment if conditions are met
            if create_break or i == len(tagged_tokens) - 1:
                if current_fragment:
                    fragment_text = ' '.join(current_fragment)
                    fragments.append({
                        'text': fragment_text,
                        'pos_tags': current_tags.copy()
                    })
                    current_fragment = []
                    current_tags = []
            
            i += 1
        
        # If there's anything left, add it as a fragment
        if current_fragment:
            fragment_text = ' '.join(current_fragment)
            fragments.append({
                'text': fragment_text,
                'pos_tags': current_tags.copy()
            })
        
        self.logger.debug(f"Created {len(fragments)} fragments from text")
        return fragments
    
    def get_fragments_by_pos_pattern(self, pattern: List[str]) -> List[Dict[str, Any]]:
        """Get fragments that match a specific POS pattern.
        
        Args:
            pattern (List[str]): List of POS tags to match (in order)
            
        Returns:
            List[Dict[str, Any]]: List of matching fragment chunks
        """
        self.logger.debug(f"Searching for fragments matching POS pattern: {pattern}")
        matching_chunks = []
        
        for chunk in self.chunks:
            pos_tags = chunk.get('pos_tags', [])
            
            # Check if the pattern appears in the tags
            if len(pos_tags) >= len(pattern):
                for i in range(len(pos_tags) - len(pattern) + 1):
                    if pos_tags[i:i+len(pattern)] == pattern:
                        matching_chunks.append(chunk)
                        break
        
        self.logger.info(f"Found {len(matching_chunks)} fragments matching POS pattern")
        return matching_chunks
    
    def get_fragments_by_parent(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get all fragments that belong to a specific parent phrase or line.
        
        Args:
            parent_id (str): The ID of the parent phrase or line
            
        Returns:
            List[Dict[str, Any]]: List of fragment chunks for the specified parent
        """
        self.logger.debug(f"Retrieving fragments for parent ID: {parent_id}")
        fragments = [
            chunk for chunk in self.chunks 
            if chunk.get('parent_phrase_id') == parent_id or 
            chunk.get('parent_line_id') == parent_id
        ]
        self.logger.info(f"Found {len(fragments)} fragments for parent {parent_id}")
        return fragments
