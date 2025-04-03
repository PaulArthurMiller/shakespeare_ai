from modules.rag.embeddings import EmbeddingGenerator
from modules.rag.vector_store import VectorStore
from modules.chunking.phrase_chunker import PhraseChunker
from modules.chunking.fragment_chunker import FragmentChunker
from modules.utils.logger import CustomLogger

class ShakespeareSearchEngine:
    def __init__(self, logger=None):
        self.logger = logger or CustomLogger("SearchEngine")
        self.embedder = EmbeddingGenerator(logger=self.logger)
        self.vector_stores = {
            "lines": VectorStore(collection_name="lines", logger=self.logger),
            "phrases": VectorStore(collection_name="phrases", logger=self.logger),
            "fragments": VectorStore(collection_name="fragments", logger=self.logger),
        }
        self.phrase_chunker = PhraseChunker(logger=self.logger)
        self.fragment_chunker = FragmentChunker(logger=self.logger)

    def search_line(self, modern_line: str, top_k=3):
        result = {
            "original_line": modern_line,
            "search_chunks": {
                "line": [],
                "phrases": [],
                "fragments": []
            }
        }

        # 1. Line-level embedding
        line_embedding = self.embedder.embed_texts([modern_line])[0]
        result["search_chunks"]["line"] = self.vector_stores["lines"].collection.query(
            query_embeddings=[line_embedding], n_results=top_k, include=["documents", "metadatas", "distances"]
        )

        # 2. Phrase-level chunking & search
        line_dict = {"text": modern_line, "chunk_id": "input_line"}
        phrase_chunks = self.phrase_chunker.chunk_from_line_chunks([line_dict])
        for chunk in phrase_chunks:
            emb = self.embedder.embed_texts([chunk["text"]])[0]
            search_result = self.vector_stores["phrases"].collection.query(
                query_embeddings=[emb], n_results=top_k, include=["documents", "metadatas", "distances"]
            )
            result["search_chunks"]["phrases"].append(search_result)

        # 3. Fragment-level chunking & search
        fragment_chunks = self.fragment_chunker.chunk_from_line_chunks([line_dict])
        for chunk in fragment_chunks:
            emb = self.embedder.embed_texts([chunk["text"]])[0]
            search_result = self.vector_stores["fragments"].collection.query(
                query_embeddings=[emb], n_results=top_k, include=["documents", "metadatas", "distances"]
            )
            result["search_chunks"]["fragments"].append(search_result)

        return result
