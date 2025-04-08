import unittest
from unittest.mock import patch, MagicMock
from modules.rag import main_rag_setup

class TestMainRagSetup(unittest.TestCase):

    @patch("modules.rag.main_rag_setup.VectorStore")
    @patch("modules.rag.main_rag_setup.EmbeddingGenerator")
    @patch("modules.rag.main_rag_setup.load_chunks")
    def test_embed_and_store_flow(
        self, mock_load_chunks, mock_embedder_cls, mock_vector_store_cls
    ):
        # Step 1: Set up dummy chunk data
        dummy_chunks = [{"text": "To be", "chunk_id": "chunk_001"}]
        dummy_embedded = [{"text": "To be", "chunk_id": "chunk_001", "embedding": [0.1, 0.2]}]

        # Step 2: Mock returns
        mock_load_chunks.return_value = dummy_chunks

        mock_embedder = MagicMock()
        mock_embedder.embed_chunks.return_value = dummy_embedded
        mock_embedder_cls.return_value = mock_embedder

        mock_store = MagicMock()
        mock_vector_store_cls.return_value = mock_store

        # Step 3: Run the function
        main_rag_setup.embed_and_store(
            chunk_type="test",
            input_path="fake_path.json",
            collection_name="test_collection",
            output_path=None  # skip file write for test
        )

        # Step 4: Assertions
        mock_load_chunks.assert_called_once_with("fake_path.json")
        mock_embedder.embed_chunks.assert_called_once_with(dummy_chunks)
        mock_store.add_documents.assert_called_once_with(dummy_embedded)

if __name__ == "__main__":
    unittest.main()
