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
    
    def hybrid_search(self, modern_line: str, top_k=5):
        """
        Perform a hybrid search combining vector similarity with keyword matching.
        This provides more diverse results when standard vector search yields insufficient options.
        
        Args:
            modern_line: The modern text line to find Shakespeare quotes for
            top_k: Number of results to return per search method
            
        Returns:
            Dictionary with search results from different approaches
        """
        self.logger.info(f"Performing hybrid search for: '{modern_line}'")
        
        result = {
            "original_line": modern_line,
            "search_method": "hybrid",
            "search_chunks": {
                "line": [],
                "phrases": [],
                "fragments": []
            }
        }
        
        # First get regular vector search results
        vector_results = self.search_line(modern_line, top_k)
        
        # Extract the vector search results for each level
        for level in ["line", "phrases", "fragments"]:
            # Copy vector search results to our result dict
            if level in vector_results["search_chunks"]:
                result["search_chunks"][level] = vector_results["search_chunks"][level]
        
        # Now add keyword-based search results
        import re
        from collections import Counter
        
        # Extract significant words from the modern line
        words = re.findall(r'\b\w{3,}\b', modern_line.lower())
        
        # Define stopwords to filter out common words
        stopwords = {
            'the', 'and', 'that', 'have', 'for', 'not', 'with', 'you', 'this', 'but',
            'his', 'from', 'they', 'will', 'would', 'what', 'all', 'were', 'when',
            'there', 'their', 'your', 'been', 'one', 'who', 'very', 'had', 'was', 'are',
            'she', 'her', 'him', 'has', 'our', 'them', 'its', 'about', 'can', 'out'
        }
        
        # Filter out stopwords and get the most relevant keywords
        keywords = [w for w in words if w not in stopwords]
        
        # Take the 3 most common keywords (if available)
        if keywords:
            keyword_freq = Counter(keywords)
            top_keywords = [kw for kw, _ in keyword_freq.most_common(3)]
            
            self.logger.info(f"Extracted keywords for search: {top_keywords}")
            
            # For each keyword, search each collection
            for keyword in top_keywords:
                keyword_embedding = self.embedder.embed_texts([keyword])[0]
                
                for level in ["line", "phrases", "fragments"]:
                    collection = self.vector_stores[level].collection
                    
                    # Search using the keyword embedding
                    keyword_results = collection.query(
                        query_embeddings=[keyword_embedding],
                        n_results=3,  # Fewer per keyword to avoid overwhelming
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    # Add these results to our result dictionary
                    if level == "line":
                        # Line results are directly added
                        result["search_chunks"][level] = keyword_results
                    else:
                        # Phrases and fragments results are appended
                        result["search_chunks"][level].append(keyword_results)
        
        # Log the number of results we found
        total_line_results = len(result["search_chunks"]["line"].get("documents", []))
        total_phrase_results = sum(len(r.get("documents", [])) for r in result["search_chunks"]["phrases"])
        total_fragment_results = sum(len(r.get("documents", [])) for r in result["search_chunks"]["fragments"])
        
        self.logger.info(f"Hybrid search results: {total_line_results} lines, {total_phrase_results} phrases, {total_fragment_results} fragments")
        
        return result
