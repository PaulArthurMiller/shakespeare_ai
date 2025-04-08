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
        # Skip if it's punctuation or doesn't contain at least one letter
        if not any(c.isalpha() for c in word):
            return 0

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

        # Force max_words to 6
        self.max_words = 6

        for line_chunk in line_chunks:
            line_text = line_chunk['text']
            line_id = line_chunk['chunk_id']
            pos_tags = line_chunk.get("POS", [])
            word_count = line_chunk.get("word_count")

            # Build clean list of original word tokens from line_chunk text using spaCy
            line_doc = nlp(line_text)
            line_tokens = [token for token in line_doc if not token.is_space and not token.is_punct]
            token_words = [token.text for token in line_tokens]

            used_indices = set()
            fragment_idx = 0

            # --- Primary Strategy: Use spaCy subtrees ---
            for token in line_doc:
                subtree_tokens = list(token.subtree)
                word_tokens = [t for t in subtree_tokens if not t.is_space and not t.is_punct]
                if len(word_tokens) < self.min_words or len(word_tokens) > self.max_words:
                    continue

                word_texts = [t.text for t in word_tokens]
                try:
                    for i in range(len(token_words) - len(word_texts) + 1):
                        if token_words[i:i+len(word_texts)] == word_texts:
                            word_index_start = i
                            word_index_end = i + len(word_texts) - 1
                            if any(idx in used_indices for idx in range(word_index_start, word_index_end + 1)):
                                raise ValueError("Overlapping fragment indices")
                            break
                    else:
                        raise ValueError("Fragment words not aligned")
                except ValueError:
                    continue

                fragment_text = " ".join(word_texts).strip()
                fragment_pos = [t.pos_ for t in word_tokens]
                total_syllables = sum(self._count_syllables(t.text) for t in word_tokens if t.text.isalpha())

                self.logger.debug(f"[SUBTREE] Fragment {fragment_idx}: '{fragment_text}' [words: {word_index_start}-{word_index_end}]")

                chunk = {
                    "chunk_id": f"fragment_{line_id}_{fragment_idx}",
                    "title": line_chunk.get("title", "Unknown"),
                    "act": line_chunk.get("act"),
                    "scene": line_chunk.get("scene"),
                    "line": line_chunk.get("line"),
                    "text": fragment_text,
                    "word_index": f"{word_index_start},{word_index_end}",
                    "word_count": len(word_tokens),
                    "POS": fragment_pos,
                    "syllables": total_syllables,
                    "mood": line_chunk.get("mood", "neutral"),
                    "fragment_position": fragment_idx,
                    "total_fragments_in_line": None
                }
                chunks.append(chunk)
                used_indices.update(range(word_index_start, word_index_end + 1))
                fragment_idx += 1

            # --- Fallback Strategy: Sliding window with no overlap ---
            if fragment_idx == 0:
                i = 0
                while i <= len(line_tokens) - self.min_words:
                    for window_size in range(self.max_words, self.min_words - 1, -1):
                        end = i + window_size
                        if end > len(line_tokens):
                            continue

                        if any(idx in used_indices for idx in range(i, end)):
                            continue

                        window_tokens = line_tokens[i:end]
                        fragment_words = [t.text for t in window_tokens]
                        fragment_text = " ".join(fragment_words).strip()
                        fragment_pos = [t.pos_ for t in window_tokens]
                        total_syllables = sum(self._count_syllables(t.text) for t in window_tokens if t.text.isalpha())

                        self.logger.debug(f"[FALLBACK] Fragment {fragment_idx}: '{fragment_text}' [words: {i}-{end - 1}]")

                        chunk = {
                            "chunk_id": f"fragment_{line_id}_{fragment_idx}",
                            "title": line_chunk.get("title", "Unknown"),
                            "act": line_chunk.get("act"),
                            "scene": line_chunk.get("scene"),
                            "line": line_chunk.get("line"),
                            "text": fragment_text,
                            "word_index": f"{i},{end - 1}",
                            "word_count": len(window_tokens),
                            "POS": fragment_pos,
                            "syllables": total_syllables,
                            "mood": line_chunk.get("mood", "neutral"),
                            "fragment_position": fragment_idx,
                            "total_fragments_in_line": None
                        }
                        chunks.append(chunk)
                        used_indices.update(range(i, end))
                        fragment_idx += 1
                        break  # break after first valid window at position i
                    i += 1

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
