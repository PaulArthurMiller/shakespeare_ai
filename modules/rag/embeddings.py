import os
import json
import openai
from typing import List, Dict, Any
from modules.utils.logger import CustomLogger

class EmbeddingGenerator:
    def __init__(self, model_name='text-embedding-3-large', logger=None):
        self.model_name = model_name
        self.logger = logger or CustomLogger("EmbeddingGenerator")
        self.logger.info(f"Using embedding model: {self.model_name}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        self.logger.debug(f"Embedding {len(texts)} texts")
        try:
            response = openai.embeddings.create(
                input=texts,
                model=self.model_name
            )
            embeddings = [item.embedding for item in response.data]
            return embeddings
        except Exception as e:
            self.logger.error(f"Error embedding texts: {e}")
            raise

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embed_texts(texts)
        for chunk, vector in zip(chunks, embeddings):
            chunk['embedding'] = vector
        self.logger.info(f"Embedded {len(chunks)} chunks with vectors")
        return chunks

    def save_embedded_chunks(self, chunks: List[Dict[str, Any]], output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2)
        self.logger.info(f"Saved embedded chunks to {output_path}")
