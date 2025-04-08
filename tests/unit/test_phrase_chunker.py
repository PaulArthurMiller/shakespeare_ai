import unittest
from modules.chunking.phrase_chunker import PhraseChunker
from modules.utils.logger import CustomLogger

class TestPhraseChunker(unittest.TestCase):
    def setUp(self):
        self.logger = CustomLogger("TestPhraseChunker", log_level="DEBUG")
        self.chunker = PhraseChunker(logger=self.logger)

        # Simulate a typical line chunk
        self.line_chunks = [{
            "chunk_id": "chunk_001",
            "title": "Test Play",
            "act": "I",
            "scene": "I",
            "line": 1,
            "text": "Hark! Who goes there, friend or foe?",
            "word_count": 8,
            "POS": ["INTJ", "PRON", "VERB", "ADV", "CCONJ", "NOUN"],
            "mood": "neutral"
        }]

    def test_chunker_initialization(self):
        self.assertEqual(self.chunker.chunk_type, "phrase")
        self.logger.info("✅ Chunker initialized correctly")

    def test_phrase_chunking_structure(self):
        chunks = self.chunker.chunk_from_line_chunks(self.line_chunks)
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIn("chunk_id", chunk)
            self.assertIn("text", chunk)
            self.assertIn("word_count", chunk)
            self.assertIn("POS", chunk)
            self.assertIn("syllables", chunk)
        self.logger.info("✅ Chunk structure validated")

    def test_phrase_chunking_accuracy(self):
        chunks = self.chunker.chunk_from_line_chunks(self.line_chunks)
        phrases = [chunk["text"] for chunk in chunks]
        self.logger.debug(f"Generated phrases: {phrases}")
        expected_phrases = ["Hark!", "Who goes there,", "friend or foe?"]
        for phrase in expected_phrases:
            self.assertIn(phrase, phrases)
        self.logger.info("✅ Phrase text accuracy checked")

    def test_word_index_bounds(self):
        chunks = self.chunker.chunk_from_line_chunks(self.line_chunks)
        for chunk in chunks:
            start, end = map(int, chunk["word_index"].split(","))
            self.assertGreaterEqual(start, 0)
            self.assertGreaterEqual(end, start)
            self.assertLessEqual(end, chunk["word_count"] + start)
        self.logger.info("✅ Word index boundaries are valid")

    def test_total_phrases_count(self):
        chunks = self.chunker.chunk_from_line_chunks(self.line_chunks)
        expected_count = chunks[0]['total_phrases_in_line']
        for chunk in chunks:
            self.assertEqual(chunk['total_phrases_in_line'], expected_count)
        self.logger.info("✅ Total phrases per line consistent")

if __name__ == '__main__':
    unittest.main()
