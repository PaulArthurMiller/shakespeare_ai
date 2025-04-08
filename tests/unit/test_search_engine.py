import unittest
from unittest.mock import patch, MagicMock
from modules.rag.search_engine import ShakespeareSearchEngine

class TestSearchEngine(unittest.TestCase):

    @patch("modules.rag.search_engine.EmbeddingGenerator")
    @patch("modules.rag.search_engine.VectorStore")
    @patch("modules.rag.search_engine.PhraseChunker")
    @patch("modules.rag.search_engine.FragmentChunker")
    def test_search_line_calls_all_components_correctly(
        self, mock_fragment_chunker, mock_phrase_chunker, mock_vector_store, mock_embedder
    ):
        # Mocks
        embedder_instance = mock_embedder.return_value
        embedder_instance.embed_texts.return_value = [[0.1, 0.2]]

        # Phrase and fragment chunkers return 1 chunk each
        mock_phrase_chunker.return_value.chunk_from_line_chunks.return_value = [
            {"text": "phrase A", "chunk_id": "p1"}
        ]
        mock_fragment_chunker.return_value.chunk_from_line_chunks.return_value = [
            {"text": "frag B", "chunk_id": "f1"}
        ]

        # Vector stores always return this:
        mock_vector_store.return_value.collection.query.return_value = {
            "documents": ["mock doc"], "metadatas": ["meta"], "distances": [0.42]
        }

        # Instantiate engine
        engine = ShakespeareSearchEngine()

        # Run
        result = engine.search_line("To be or not to be", top_k=1)

        # Assert structure of output
        self.assertIn("original_line", result)
        self.assertIn("search_chunks", result)
        self.assertIn("line", result["search_chunks"])
        self.assertIn("phrases", result["search_chunks"])
        self.assertIn("fragments", result["search_chunks"])

        # Check that embedding and chunking were called correctly
        self.assertGreaterEqual(embedder_instance.embed_texts.call_count, 3)
        self.assertEqual(
            len(result["search_chunks"]["phrases"]),
            1,
            "Should return one result per phrase chunk"
        )
        self.assertEqual(
            len(result["search_chunks"]["fragments"]),
            1,
            "Should return one result per fragment chunk"
        )

if __name__ == "__main__":
    unittest.main()
