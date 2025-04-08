import unittest
from unittest.mock import patch, MagicMock
from modules.rag.vector_store import VectorStore

class TestVectorStore(unittest.TestCase):

    @patch("modules.rag.vector_store.chromadb.PersistentClient")
    def test_initialization_sets_up_client_and_collection(self, mock_client):
        mock_instance = mock_client.return_value
        mock_collection = MagicMock()
        mock_instance.get_or_create_collection.return_value = mock_collection

        store = VectorStore(path="test/path", collection_name="test_collection")

        mock_client.assert_called_once()
        mock_instance.get_or_create_collection.assert_called_with(name="test_collection")
        self.assertEqual(store.collection, mock_collection)

    @patch("modules.rag.vector_store.chromadb.PersistentClient")
    def test_add_documents_sends_correct_data(self, mock_client):
        mock_collection = MagicMock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        store = VectorStore()
        chunks = [
            {"chunk_id": "c1", "text": "Hello world", "embedding": [0.1, 0.2], "title": "Macbeth", "act": "I"},
            {"chunk_id": "c2", "text": "To be or not", "embedding": [0.3, 0.4], "scene": "II", "line": 1},
        ]
        store.add_documents(chunks)

        self.assertEqual(mock_collection.add.call_count, 1)
        args = mock_collection.add.call_args[1]
        self.assertEqual(len(args["documents"]), 2)
        self.assertEqual(len(args["embeddings"]), 2)
        self.assertEqual(len(args["ids"]), 2)
        self.assertEqual(len(args["metadatas"]), 2)

    @patch("modules.rag.vector_store.chromadb.PersistentClient")
    def test_query_uses_embedding_function_and_queries_collection(self, mock_client):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"documents": ["result"]}
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        store = VectorStore()
        mock_embed_fn = MagicMock(return_value=[[0.5, 0.6]])

        results = store.query("test query", embedding_function=mock_embed_fn)

        mock_embed_fn.assert_called_once_with(["test query"])
        mock_collection.query.assert_called_once()
        self.assertIn("documents", results)

if __name__ == "__main__":
    unittest.main()
