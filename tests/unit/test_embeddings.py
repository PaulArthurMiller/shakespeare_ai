import unittest
from unittest.mock import patch, MagicMock
from modules.rag.embeddings import EmbeddingGenerator
import os
import json

class TestEmbeddingGenerator(unittest.TestCase):

    def setUp(self):
        self.embedder = EmbeddingGenerator(model_name='test-model')

    @patch("openai.embeddings.create")
    def test_embed_texts_returns_vectors(self, mock_create):
        mock_create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3]) for _ in range(2)]
        )
        texts = ["To be or not to be", "That is the question"]
        vectors = self.embedder.embed_texts(texts)

        self.assertEqual(len(vectors), 2)
        self.assertTrue(all(isinstance(vec, list) for vec in vectors))
        self.assertTrue(all(isinstance(val, float) for val in vectors[0]))

    @patch("openai.embeddings.create")
    def test_embed_chunks_adds_embedding(self, mock_create):
        mock_create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2]) for _ in range(2)]
        )
        chunks = [{"text": "Line one"}, {"text": "Line two"}]
        result = self.embedder.embed_chunks(chunks)

        self.assertEqual(len(result), 2)
        self.assertIn("embedding", result[0])
        self.assertEqual(len(result[0]["embedding"]), 2)

    def test_save_embedded_chunks_creates_file(self):
        chunks = [{"text": "Sample", "embedding": [0.1, 0.2]}]
        output_path = "temp/test_embedded.json"
        self.embedder.save_embedded_chunks(chunks, output_path)

        self.assertTrue(os.path.exists(output_path))
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data[0]["text"], "Sample")
            self.assertIn("embedding", data[0])

        os.remove(output_path)
        os.rmdir("temp")

if __name__ == '__main__':
    unittest.main()
