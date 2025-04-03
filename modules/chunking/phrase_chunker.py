"""
Phrase chunker module for Shakespeare AI project.

This module provides functionality to chunk Shakespeare's text into phrases
based on punctuation breaks, preserving the relationship to parent lines.
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


class PhraseChunker(ChunkBase):
    """Chunker for processing Shakespeare's text into phrases.

    This chunker splits text based on punctuation breaks (periods, commas, etc.)
    and maintains the relationship to the original line.
    """

    def __init__(self, logger: Optional[CustomLogger] = None):
        super().__init__(chunk_type='phrase')
        self.logger = logger or CustomLogger("PhraseChunker")
        self.logger.info("Initializing PhraseChunker")

        if not SPACY_AVAILABLE:
            self.logger.critical("spaCy is not available")
            raise ImportError(
                "spaCy is required for PhraseChunker. "
                "Install it with: pip install spacy && python -m spacy download en_core_web_sm"
            )

        self.phrase_pattern = re.compile(r'([.!?;:])')
        self.logger.debug("Compiled regular expressions for text parsing")

    def _count_syllables(self, word: str) -> int:
        word = word.lower()
        if len(word) <= 3:
            return 1
        if word.endswith('e'):
            word = word[:-1]
        vowels = re.findall(r'[aeiouy]+', word)
        return max(1, len(vowels))

    def chunk_from_line_chunks(self, line_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.logger.info("Starting phrase chunking from line chunks")
        self.logger.debug(f"Processing {len(line_chunks)} line chunks")
        chunks = []

        for line_chunk in line_chunks:
            line_text = line_chunk['text']
            line_id = line_chunk['chunk_id']
            word_count = line_chunk.get("word_count")
            pos_tags = line_chunk.get("POS", [])

            major_parts = self.phrase_pattern.split(line_text)
            phrases = []
            i = 0
            while i < len(major_parts):
                if i + 1 < len(major_parts) and re.match(self.phrase_pattern, major_parts[i + 1]):
                    phrases.append(major_parts[i] + major_parts[i + 1])
                    i += 2
                else:
                    if major_parts[i]:
                        phrases.append(major_parts[i])
                    i += 1

            final_phrases = []
            for phrase in phrases:
                comma_parts = phrase.split(',')
                for i, part in enumerate(comma_parts):
                    if i < len(comma_parts) - 1:
                        final_phrases.append(part.strip() + ',')
                    else:
                        final_phrases.append(part.strip())

            line_doc = nlp(line_text)
            full_line_words = [token.text for token in line_doc if not token.is_space]

            for phrase_idx, phrase in enumerate(final_phrases):
                phrase = phrase.strip()
                if not phrase:
                    continue

                phrase_doc = nlp(phrase)
                phrase_words = [token.text for token in phrase_doc if not token.is_space]

                phrase_start = -1
                for i in range(len(full_line_words) - len(phrase_words) + 1):
                    if full_line_words[i:i+len(phrase_words)] == phrase_words:
                        phrase_start = i
                        break

                if phrase_start == -1:
                    self.logger.warning(f"Could not find phrase position in line: {phrase}")
                    continue

                phrase_pos_tags = pos_tags[phrase_start: phrase_start + len(phrase_words)]
                total_syllables = sum(self._count_syllables(word) for word in phrase_words if word.isalpha())

                chunk = {
                    "chunk_id": f"phrase_{line_id}_{phrase_idx}",
                    "title": line_chunk.get("title", "Unknown"),
                    "act": line_chunk.get("act"),
                    "scene": line_chunk.get("scene"),
                    "line": line_chunk.get("line"),
                    "text": phrase,
                    "word_index": f"{phrase_start},{phrase_start + len(phrase_words) - 1}",
                    "word_count": len(phrase_words),
                    "POS": phrase_pos_tags,
                    "syllables": total_syllables,
                    "mood": line_chunk.get("mood", "neutral"),
                    "phrase_position": phrase_idx,
                    "total_phrases_in_line": len(final_phrases),
                    "ends_with_punctuation": bool(re.search(r'[.!?;:,]$', phrase))
                }
                chunks.append(chunk)
                self.logger.debug(
                    f"Created phrase chunk {chunk['chunk_id']} from line {line_id}: "
                    f"{len(phrase)} chars, {len(phrase_words)} words"
                )

        self.logger.info(f"Completed phrase chunking: created {len(chunks)} chunks from line chunks")
        return chunks

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("Use chunk_from_line_chunks instead")