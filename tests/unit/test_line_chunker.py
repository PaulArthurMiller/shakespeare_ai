import unittest
from modules.chunking.line_chunker import LineChunker
from modules.utils.logger import CustomLogger


class TestLineChunker(unittest.TestCase):
    """Unit tests for the LineChunker class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.logger = CustomLogger("TestLineChunker")
        self.chunker = LineChunker(logger=self.logger)
        
        # Sample play text
        self.play_text = """
THE TRAGEDY OF ROMEO AND JULIET

Characters in the Play
ESCALUS, Prince of Verona
PARIS, a young nobleman
MONTAGUE, head of a Verona family
LADY MONTAGUE, his wife

ACT I
SCENE I. Verona. A public place.

Enter SAMPSON and GREGORY, of the house of Capulet, armed with swords and bucklers

SAMPSON.
Gregory, on my word, we'll not carry coals.

GREGORY.
No, for then we should be colliers.

SAMPSON.
I mean, an we be in choler, we'll draw.

GREGORY.
Ay, while you live, draw your neck out of collar.
"""

        # Sample sonnet text
        self.sonnet_text = """
THE SONNETS

1

From fairest creatures we desire increase,
That thereby beauty's rose might never die,
But as the riper should by time decease,
His tender heir might bear his memory:

2

When forty winters shall beseige thy brow,
And dig deep trenches in thy beauty's field,
Thy youth's proud livery, so gazed on now,
Will be a tatter'd weed, of small worth held:
"""

    def test_initialization(self):
        """Test proper initialization of LineChunker."""
        self.assertEqual(self.chunker.chunk_type, 'line')
        self.assertIsNotNone(self.chunker.logger)
        self.assertEqual(len(self.chunker.chunks), 0)

    def test_chunk_play_basic(self):
        """Test basic text chunking functionality with a play."""
        chunks = self.chunker.chunk_text(self.play_text)
        
        # Verify we got some chunks
        self.assertTrue(len(chunks) > 0, "Should have extracted at least some lines")
        
        # Verify title detection
        self.assertEqual(chunks[0]['title'], "THE TRAGEDY OF ROMEO AND JULIET")
        
        # Verify all required fields are present in each chunk
        required_fields = {
            'chunk_id', 'title', 'text', 'line', 'act', 'scene',
            'word_index', 'syllables', 'POS', 'mood', 'word_count'
        }
        
        for chunk in chunks:
            for field in required_fields:
                self.assertIn(field, chunk, f"Missing required field: {field}")
            
            # Verify word_index format
            self.assertRegex(chunk['word_index'], r'^\d+,\d+$', 
                           "word_index should be in format 'start,end'")
            
            # Verify POS is a list
            self.assertIsInstance(chunk['POS'], list,
                                "POS should be a list of tags")

    def test_act_scene_detection(self):
        """Test correct detection of act and scene information."""
        chunks = self.chunker.chunk_text(self.play_text)
        
        # Verify we have chunks
        self.assertTrue(len(chunks) > 0, "Should have at least one chunk")
        
        # Find chunks with Act I, Scene I information
        act1_scene1_chunks = [chunk for chunk in chunks if chunk['act'] == 'I' and chunk['scene'] == 'I']
        
        # Verify we found chunks with the correct act and scene
        self.assertTrue(len(act1_scene1_chunks) > 0, "Should have chunks from Act I, Scene I")

    def test_sonnet_detection(self):
        """Test correct detection of sonnets."""
        chunks = self.chunker.chunk_text(self.sonnet_text)
        
        # Verify we got chunks
        self.assertTrue(len(chunks) > 0, "Should have extracted at least some lines")
        
        # Verify title detection
        self.assertEqual(chunks[0]['title'], "THE SONNETS")
        
        # Find sonnet 1 lines
        sonnet1_lines = [chunk for chunk in chunks if chunk['act'] == '1']
        self.assertTrue(len(sonnet1_lines) > 0, "Should have lines for sonnet 1")
        
        # Find sonnet 2 lines
        sonnet2_lines = [chunk for chunk in chunks if chunk['act'] == '2']
        self.assertTrue(len(sonnet2_lines) > 0, "Should have lines for sonnet 2")
        
        # Verify each sonnet line has an empty scene field
        for chunk in sonnet1_lines + sonnet2_lines:
            self.assertEqual(chunk['scene'], "", "Sonnets should have empty scene field")

    def test_get_lines_by_act_scene(self):
        """Test retrieving lines from a specific act and scene."""
        self.chunker.chunk_text(self.play_text)
        
        act1_scene1_lines = self.chunker.get_lines_by_act_scene('I', 'I')
        self.assertTrue(len(act1_scene1_lines) > 0, "Should find lines in Act I, Scene I")
        
        # Test with non-existent act/scene
        empty_lines = self.chunker.get_lines_by_act_scene('II', 'I')
        self.assertEqual(len(empty_lines), 0)

    def test_get_sonnet_lines(self):
        """Test retrieving lines from a specific sonnet."""
        self.chunker.chunk_text(self.sonnet_text)
        
        # Get lines for sonnet 1
        sonnet1_lines = self.chunker.get_sonnet_lines('1')
        self.assertTrue(len(sonnet1_lines) > 0, "Should find lines in Sonnet 1")
        
        # Get lines for sonnet 2
        sonnet2_lines = self.chunker.get_sonnet_lines('2')
        self.assertTrue(len(sonnet2_lines) > 0, "Should find lines in Sonnet 2")
        
        # Test with non-existent sonnet
        empty_lines = self.chunker.get_sonnet_lines('999')
        self.assertEqual(len(empty_lines), 0)

    def test_get_dialogue_exchange(self):
        """Test retrieving a dialogue exchange."""
        chunks = self.chunker.chunk_text(self.play_text)
        if len(chunks) == 0:
            self.skipTest("Not enough chunks to test dialogue exchange")
            
        # Get first 3 lines of dialogue (or fewer if less are available)
        max_lines = 3
        exchange = self.chunker.get_dialogue_exchange(0, max_lines)
        self.assertTrue(0 < len(exchange) <= max_lines, 
                       f"Should return up to {max_lines} lines starting from index 0")
        
        # Test with invalid start index
        invalid_exchange = self.chunker.get_dialogue_exchange(100, 3)
        self.assertEqual(len(invalid_exchange), 0)

    def test_empty_text(self):
        """Test handling of empty text."""
        chunks = self.chunker.chunk_text("")
        self.assertEqual(len(chunks), 0)

    def test_metadata_consistency(self):
        """Test consistency of metadata across chunks."""
        chunks = self.chunker.chunk_text(self.play_text)
        
        for chunk in chunks:
            # Verify word indices are valid
            start, end = map(int, chunk['word_index'].split(','))
            
            # Verify word_count is consistent with word_index
            self.assertEqual(
                end - start + 1,
                chunk['word_count'],
                "Word index range should match word_count"
            )
            
            # Verify syllable count is reasonable (if there are words)
            if chunk['word_count'] > 0:
                self.assertGreater(
                    chunk['syllables'],
                    0,
                    "Syllable count should be positive for non-empty text"
                )
                self.assertLess(
                    chunk['syllables'],
                    chunk['word_count'] * 8,  # Allowing up to 8 syllables per word for complexity
                    "Syllable count seems unreasonably high"
                )
            
            # Verify POS tags length matches word count using the same tokenizer
            self.assertEqual(
                len(chunk['POS']),
                chunk['word_count'],
                "Number of POS tags should match word count"
            )

    def test_line_indexing(self):
        """Test that line indexes are properly incremented."""
        chunks = self.chunker.chunk_text(self.play_text)
        
        if not chunks:
            self.skipTest("No chunks to test line indexing")
            
        line_numbers = [chunk['line'] for chunk in chunks]
        
        # Verify line numbers are unique
        self.assertEqual(
            len(line_numbers),
            len(set(line_numbers)),
            "Line numbers should be unique"
        )
        
        # Verify line numbers are sequential
        sorted_lines = sorted(line_numbers)
        for i in range(len(sorted_lines) - 1):
            self.assertEqual(
                sorted_lines[i] + 1,
                sorted_lines[i + 1],
                "Line numbers should be sequential"
            )


if __name__ == '__main__':
    unittest.main()