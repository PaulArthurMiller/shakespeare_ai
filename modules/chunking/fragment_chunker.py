"""
Fragment chunker module for Shakespeare AI project.

This module provides functionality to chunk Shakespeare's text into small
fragments (3-8 words) based on semantic groupings, preserving metadata.
"""
import re
from typing import List, Dict, Any, Optional
from .base import ChunkBase
from modules.utils.logger import CustomLogger

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class FragmentChunker(ChunkBase):
    """Chunker for processing Shakespeare's text into semantic word fragments.

    This chunker creates 3-8 word fragments from each line using spaCy's syntactic parsing,
    preserving references to the parent line and avoiding overlap.
    """

    def __init__(self, min_words: int = 3, max_words: int = 8, logger: Optional[CustomLogger] = None):
        super().__init__(chunk_type='fragment')
        self.logger = logger or CustomLogger("FragmentChunker")
        self.logger.info("Initializing FragmentChunker")

        self.min_words = min_words
        self.max_words = max_words
        self.logger.debug(f"Set word limits: min={min_words}, max={max_words}")

        if not SPACY_AVAILABLE:
            self.logger.critical("spaCy is not available")
            raise ImportError(
                "spaCy is required for FragmentChunker. "
                "Install it with: pip install spacy && python -m spacy download en_core_web_sm"
            )

    def _count_syllables(self, word: str) -> int:
        word = word.lower()
        if len(word) <= 3:
            return 1
        if word.endswith('e'):
            word = word[:-1]
        vowels = re.findall(r'[aeiouy]+', word)
        return max(1, len(vowels))

    def chunk_from_line_chunks(self, line_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.logger.info("Starting fragment chunking from line chunks")
        self.logger.debug(f"Processing {len(line_chunks)} line chunks")
        chunks = []

        for line_chunk in line_chunks:
            line_text = line_chunk['text']
            line_id = line_chunk['chunk_id']
            pos_tags = line_chunk.get("POS", [])
            word_count = line_chunk.get("word_count")
            line_doc = nlp(line_text)
            tokens = [token for token in line_doc if not token.is_space]
            used_indices = set()
            fragment_idx = 0

            for token in tokens:
                subtree_tokens = list(token.subtree)
                if not subtree_tokens:
                    continue

                first_idx = token.i
                last_idx = subtree_tokens[-1].i
                length = last_idx - first_idx + 1

                if length < self.min_words or length > self.max_words:
                    continue

                if any(i in used_indices for i in range(first_idx, last_idx + 1)):
                    continue

                fragment_words = [t.text for t in subtree_tokens]
                fragment_text = " ".join(fragment_words)
                word_index_start = len([t for t in tokens if t.i < first_idx])
                word_index_end = word_index_start + len(fragment_words) - 1
                fragment_pos = pos_tags[word_index_start:word_index_end + 1]
                total_syllables = sum(self._count_syllables(w) for w in fragment_words if w.isalpha())

                chunk = {
                    "chunk_id": f"fragment_{line_id}_{fragment_idx}",
                    "title": line_chunk.get("title", "Unknown"),
                    "act": line_chunk.get("act"),
                    "scene": line_chunk.get("scene"),
                    "line": line_chunk.get("line"),
                    "text": fragment_text,
                    "word_index": f"{word_index_start},{word_index_end}",
                    "word_count": len(fragment_words),
                    "POS": fragment_pos,
                    "syllables": total_syllables,
                    "mood": line_chunk.get("mood", "neutral"),
                    "fragment_position": fragment_idx,
                    "total_fragments_in_line": None
                }
                chunks.append(chunk)
                used_indices.update(range(first_idx, last_idx + 1))
                fragment_idx += 1

        from collections import defaultdict
        line_to_count = defaultdict(int)
        for chunk in chunks:
            key = (chunk['title'], chunk['act'], chunk['scene'], chunk['line'])
            line_to_count[key] += 1
        for chunk in chunks:
            key = (chunk['title'], chunk['act'], chunk['scene'], chunk['line'])
            chunk['total_fragments_in_line'] = line_to_count[key]

        self.logger.info(f"Completed fragment chunking: created {len(chunks)} fragments")
        return chunks

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("Use chunk_from_line_chunks instead")
