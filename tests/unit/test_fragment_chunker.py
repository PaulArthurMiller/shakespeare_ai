import unittest
from modules.chunking.fragment_chunker import FragmentChunker
from modules.utils.logger import CustomLogger

class TestFragmentChunker(unittest.TestCase):
    def setUp(self):
        self.logger = CustomLogger("TestFragmentChunker", log_level="DEBUG")
        self.chunker = FragmentChunker(min_words=2, max_words=6, logger=self.logger)

        self.line_chunks = [{
            "chunk_id": "chunk_001",
            "title": "Test Play",
            "act": "I",
            "scene": "I",
            "line": 1,
            "text": "The moon shines bright upon the path of fate.",
            "word_count": 9,
            "POS": ["DET", "NOUN", "VERB", "ADJ", "ADP", "DET", "NOUN", "ADP", "NOUN"],
            "mood": "neutral"
        }]

    def test_chunker_initialization(self):
        self.assertEqual(self.chunker.chunk_type, "fragment")
        self.logger.info("✅ Chunker initialized correctly")

    def test_fragment_output_structure(self):
        fragments = self.chunker.chunk_from_line_chunks(self.line_chunks)
        self.assertIsInstance(fragments, list)
        self.assertGreater(len(fragments), 0)
        for fragment in fragments:
            self.assertIn("chunk_id", fragment)
            self.assertIn("text", fragment)
            self.assertIn("syllables", fragment)
            self.assertIn("word_index", fragment)
            self.assertIn("POS", fragment)
            self.assertIn("fragment_position", fragment)
        self.logger.info("✅ Fragment structure validated")

    def test_fragment_text_validity(self):
        fragments = self.chunker.chunk_from_line_chunks(self.line_chunks)
        for frag in fragments:
            self.assertGreaterEqual(frag['word_count'], 2)
            self.assertLessEqual(frag['word_count'], 6)
            self.assertIsInstance(frag['text'], str)
            self.assertGreater(len(frag['text']), 0)
        self.logger.info("✅ Fragment text and word limits valid")

    def test_fragment_index_and_overlap(self):
        fragments = self.chunker.chunk_from_line_chunks(self.line_chunks)
        used = set()
        for frag in fragments:
            start, end = map(int, frag['word_index'].split(','))
            overlap = any(i in used for i in range(start, end + 1))
            self.assertFalse(overlap, f"Overlap detected in fragment: {frag['chunk_id']}")
            used.update(range(start, end + 1))
        self.logger.info("✅ No overlapping fragments detected")

    def test_fragment_position_and_counts(self):
        fragments = self.chunker.chunk_from_line_chunks(self.line_chunks)
        total_per_line = fragments[0]['total_fragments_in_line']
        positions = [frag['fragment_position'] for frag in fragments]
        self.assertEqual(len(positions), total_per_line)
        self.assertListEqual(sorted(positions), list(range(len(positions))))
        self.logger.info("✅ Fragment positions and counts consistent")

if __name__ == '__main__':
    unittest.main()
