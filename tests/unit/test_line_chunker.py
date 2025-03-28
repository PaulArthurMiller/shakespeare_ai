import unittest
from modules.chunking.line_chunker import LineChunker
from modules.utils.logger import CustomLogger


class TestLineChunker(unittest.TestCase):
    """Unit tests for the LineChunker class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.logger = CustomLogger("TestLineChunker")
        self.chunker = LineChunker(logger=self.logger)
        
        # Sample text that includes various Shakespeare-style elements
        self.test_text = """
ACT I
SCENE I. A hall in DUKE SOLINUS'S palace.

AEGEON.
Proceed, Solinus, to procure my fall,
And by the doom of death end woes and all.

DUKE SOLINUS.
Merchant of Syracuse, plead no more;
I am not partial to infringe our laws.
The enmity and discord which of late
Sprung from the rancorous outrage of your duke
To merchants, our well-dealing countrymen.

AEGEON.
Yet this my comfort: when your words are done,
My woes end likewise with the evening sun.
"""

    def test_initialization(self):
        """Test proper initialization of LineChunker."""
        self.assertEqual(self.chunker.chunk_type, 'line')
        self.assertIsNotNone(self.chunker.logger)
        self.assertEqual(len(self.chunker.chunks), 0)

    def test_chunk_text_basic(self):
        """Test basic text chunking functionality."""
        chunks = self.chunker.chunk_text(self.test_text)
        
        # Verify we got the expected number of dialogue lines
        self.assertEqual(len(chunks), 7)  # Number of actual dialogue lines
        
        # Verify basic structure of chunks
        for chunk in chunks:
            self.assertIn('chunk_id', chunk)
            self.assertIn('text', chunk)
            self.assertIn('line_number', chunk)
            self.assertIn('act', chunk)
            self.assertIn('scene', chunk)
            self.assertIn('speaker', chunk)
            self.assertIn('char_length', chunk)
            self.assertIn('word_count', chunk)

    def test_act_scene_detection(self):
        """Test correct detection of act and scene information."""
        chunks = self.chunker.chunk_text(self.test_text)
        
        # All chunks should be from Act I, Scene I
        for chunk in chunks:
            self.assertEqual(chunk['act'], 'I')
            self.assertEqual(chunk['scene'], 'I')

    def test_speaker_detection(self):
        """Test correct detection of speakers."""
        chunks = self.chunker.chunk_text(self.test_text)
        
        # Verify specific speakers are correctly identified
        aegeon_lines = [chunk for chunk in chunks if chunk['speaker'] == 'AEGEON']
        solinus_lines = [chunk for chunk in chunks if chunk['speaker'] == 'DUKE SOLINUS']
        
        self.assertTrue(len(aegeon_lines) >= 2)
        self.assertTrue(len(solinus_lines) >= 1)

    def test_get_speaker_lines(self):
        """Test retrieving lines for a specific speaker."""
        self.chunker.chunk_text(self.test_text)
        
        aegeon_lines = self.chunker.get_speaker_lines('AEGEON')
        self.assertTrue(len(aegeon_lines) >= 2)
        
        for line in aegeon_lines:
            self.assertEqual(line['speaker'], 'AEGEON')

    def test_get_lines_by_act_scene(self):
        """Test retrieving lines from a specific act and scene."""
        self.chunker.chunk_text(self.test_text)
        
        act1_scene1_lines = self.chunker.get_lines_by_act_scene('I', 'I')
        self.assertEqual(len(act1_scene1_lines), 7)  # All lines in our test text
        
        # Test with non-existent act/scene
        empty_lines = self.chunker.get_lines_by_act_scene('II', 'I')
        self.assertEqual(len(empty_lines), 0)

    def test_get_dialogue_exchange(self):
        """Test retrieving a dialogue exchange."""
        self.chunker.chunk_text(self.test_text)
        
        # Get first 3 lines of dialogue
        exchange = self.chunker.get_dialogue_exchange(0, 3)
        self.assertEqual(len(exchange), 3)
        
        # Test with invalid start index
        invalid_exchange = self.chunker.get_dialogue_exchange(100, 3)
        self.assertEqual(len(invalid_exchange), 0)

    def test_empty_text(self):
        """Test handling of empty text."""
        chunks = self.chunker.chunk_text("")
        self.assertEqual(len(chunks), 0)

    def test_metadata_consistency(self):
        """Test consistency of metadata across chunks."""
        chunks = self.chunker.chunk_text(self.test_text)
        
        for chunk in chunks:
            # Verify word count matches actual words in text
            self.assertEqual(
                chunk['word_count'],
                len(chunk['text'].split())
            )
            
            # Verify character length matches actual text length
            self.assertEqual(
                chunk['char_length'],
                len(chunk['text'])
            )

    def test_line_continuity(self):
        """Test that line numbers are continuous and unique."""
        chunks = self.chunker.chunk_text(self.test_text)
        
        line_numbers = [chunk['line_number'] for chunk in chunks]
        self.assertEqual(
            len(line_numbers),
            len(set(line_numbers)),
            "Line numbers should be unique"
        )
        
        # Verify line numbers are in ascending order
        self.assertEqual(
            line_numbers,
            sorted(line_numbers),
            "Line numbers should be in ascending order"
        )


if __name__ == '__main__':
    unittest.main()
