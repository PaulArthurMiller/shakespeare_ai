"""
Fragment chunker module for Shakespeare AI project.

This module provides functionality to chunk Shakespeare's text into small
fragments (3-6 words) based on Part-of-Speech patterns, which can be
used for fine-grained retrieval and composition.
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from .base import ChunkBase

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
    
    def __init__(self, min_words: int = 3, max_words: int = 6):
        """Initialize the FragmentChunker.
        
        Args:
            min_words (int): Minimum number of words in a fragment
            max_words (int): Maximum number of words in a fragment
        """
        super().__init__(chunk_type='fragment')
        self.min_words = min_words
        self.max_words = max_words
        
        if not NLTK_AVAILABLE:
            raise ImportError(
                "NLTK is required for FragmentChunker. "
                "Install it with: pip install nltk"
            )
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split the text into small fragments based on POS patterns.
        
        Args:
            text (str): The text to process
            
        Returns:
            List[Dict[str, Any]]: List of fragment chunks with metadata
        """
        # This method works best with lines or phrases as input
        lines = text.strip().split('\n')
        chunks = []
        
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Create fragments for this line
            line_fragments = self._create_fragments_from_text(line)
            
            # Add metadata and collect all fragments
            for frag_idx, fragment in enumerate(line_fragments):
                chunk = {
                    'chunk_id': f'fragment_{line_idx}_{frag_idx}',
                    'text': fragment['text'],
                    'parent_line_idx': line_idx,
                    'fragment_position': frag_idx,
                    'pos_tags': fragment['pos_tags'],
                    'total_fragments_in_line': len(line_fragments),
                    'char_length': len(fragment['text']),
                    'word_count': len(fragment['text'].split())
                }
                chunks.append(chunk)
        
        return chunks
    
    def chunk_from_phrase_chunks(self, phrase_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create fragment chunks from previously processed phrase chunks.
        
        Args:
            phrase_chunks (List[Dict[str, Any]]): List of phrase chunks from PhraseChunker
            
        Returns:
            List[Dict[str, Any]]: List of fragment chunks with metadata
        """
        chunks = []
        
        for phrase_chunk in phrase_chunks:
            phrase_text = phrase_chunk['text']
            phrase_id = phrase_chunk['chunk_id']
            parent_line_id = phrase_chunk.get('parent_line_id')
            
            # Create fragments for this phrase
            phrase_fragments = self._create_fragments_from_text(phrase_text)
            
            # Add metadata and collect all fragments
            for frag_idx, fragment in enumerate(phrase_fragments):
                chunk = {
                    'chunk_id': f'fragment_{phrase_id}_{frag_idx}',
                    'text': fragment['text'],
                    'parent_phrase_id': phrase_id,
                    'parent_line_id': parent_line_id,
                    'fragment_position': frag_idx,
                    'pos_tags': fragment['pos_tags'],
                    'total_fragments_in_phrase': len(phrase_fragments),
                    'char_length': len(fragment['text']),
                    'word_count': len(fragment['text'].split()),
                    # Copy metadata from parent phrase
                    'act': phrase_chunk.get('act'),
                    'scene': phrase_chunk.get('scene'),
                    'speaker': phrase_chunk.get('speaker'),
                }
                chunks.append(chunk)
        
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
        # Tokenize and tag the text
        tokens = word_tokenize(text)
        tagged_tokens = pos_tag(tokens)
        
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
        
        return fragments
    
    def get_fragments_by_pos_pattern(self, pattern: List[str]) -> List[Dict[str, Any]]:
        """Get fragments that match a specific POS pattern.
        
        Args:
            pattern (List[str]): List of POS tags to match (in order)
            
        Returns:
            List[Dict[str, Any]]: List of matching fragment chunks
        """
        matching_chunks = []
        
        for chunk in self.chunks:
            pos_tags = chunk.get('pos_tags', [])
            
            # Check if the pattern appears in the tags
            if len(pos_tags) >= len(pattern):
                for i in range(len(pos_tags) - len(pattern) + 1):
                    if pos_tags[i:i+len(pattern)] == pattern:
                        matching_chunks.append(chunk)
                        break
        
        return matching_chunks
    
    def get_fragments_by_parent(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get all fragments that belong to a specific parent phrase or line.
        
        Args:
            parent_id (str): The ID of the parent phrase or line
            
        Returns:
            List[Dict[str, Any]]: List of fragment chunks for the specified parent
        """
        return [
            chunk for chunk in self.chunks 
            if chunk.get('parent_phrase_id') == parent_id or 
            chunk.get('parent_line_id') == parent_id
        ]