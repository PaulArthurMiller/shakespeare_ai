# modules/translator/rag_caller.py

from typing import List, Dict, Any, Optional
from modules.rag.search_engine import ShakespeareSearchEngine
from modules.translator.types import CandidateQuote
from modules.utils.logger import CustomLogger

class RagCaller:
    def __init__(self, logger: Optional[CustomLogger] = None):
        self.logger = logger or CustomLogger("RagCaller")
        self.search_engine = ShakespeareSearchEngine(logger=self.logger)

    def retrieve_by_line(self, modern_line: str, top_k: int = 5) -> List[CandidateQuote]:
        results = self.search_engine.search_line(modern_line, top_k)
        return self._extract_candidates(results["search_chunks"]["line"], level="line")

    def retrieve_by_phrase(self, modern_line: str, top_k: int = 5) -> List[CandidateQuote]:
        results = self.search_engine.search_line(modern_line, top_k)
        flat_phrase_hits = results["search_chunks"]["phrases"]
        return self._extract_candidates(flat_phrase_hits, level="phrases")

    def retrieve_by_fragment(self, modern_line: str, top_k: int = 5) -> List[CandidateQuote]:
        results = self.search_engine.search_line(modern_line, top_k)
        flat_fragment_hits = results["search_chunks"]["fragments"]
        return self._extract_candidates(flat_fragment_hits, level="fragments")

    def retrieve_all(self, modern_line: str, top_k: int = 5) -> Dict[str, List[CandidateQuote]]:
        results = self.search_engine.search_line(modern_line, top_k)

        return {
            "line": self._extract_candidates([results["search_chunks"]["line"]], "line"),
            "phrases": [
                candidate
                for group in results["search_chunks"]["phrases"]
                for candidate in self._extract_candidates([group], "phrases")
            ],
            "fragments": [
                candidate
                for group in results["search_chunks"]["fragments"]
                for candidate in self._extract_candidates([group], "fragments")
            ],
        }

    def _extract_candidates(self, raw_results: List[Dict[str, Any]], level: str) -> List[CandidateQuote]:
        candidates = []
        for result in raw_results:
            docs = result.get("documents", [])
            metas = result.get("metadatas", [])
            scores = result.get("distances", [])
            
            # Guard against empty results
            if not docs or not metas or not scores:
                self.logger.warning(f"Empty data in result for {level} level")
                continue
            
            # Handle the case where docs is a list of strings and metas is a list of lists
            if isinstance(docs, list) and len(docs) > 0:
                # In your case, it appears the first level is also a list
                if isinstance(docs[0], list) and isinstance(metas[0], list):
                    self.logger.debug(f"Processing nested list structure in {level} level")
                    
                    # For each document in the list
                    for i, (doc_list, meta_list, score_list) in enumerate(zip(docs, metas, scores)):
                        # For each potential document text option
                        for j, doc_text in enumerate(doc_list):
                            # Get corresponding metadata if available
                            if j < len(meta_list) and isinstance(meta_list[j], dict):
                                meta_dict = meta_list[j]
                                # Get corresponding score if available
                                if j < len(score_list):
                                    # Handle different score types
                                    if isinstance(score_list[j], (int, float)):
                                        score_val = float(score_list[j])
                                    else:
                                        # Default score if not a number
                                        score_val = 1.0
                                else:
                                    score_val = 1.0
                                
                                candidates.append(CandidateQuote(
                                    text=str(doc_text),
                                    reference=meta_dict,
                                    score=score_val
                                ))
                                self.logger.debug(f"Added candidate from nested structure: level={level}, item={i}-{j}, score={score_val}")
                
                # Handle the case where each doc is a string but metas is a list of dictionaries
                elif all(isinstance(d, str) for d in docs) and all(isinstance(m, list) for m in metas):
                    self.logger.debug(f"Processing flat document list with metadata lists in {level} level")
                    
                    for i, (doc_text, meta_list, score_entry) in enumerate(zip(docs, metas, scores)):
                        # For each metadata dictionary in the list
                        for j, meta_dict in enumerate(meta_list):
                            if isinstance(meta_dict, dict):
                                # Process score value safely
                                if isinstance(score_entry, list) and j < len(score_entry):
                                    # Handle different score types
                                    if isinstance(score_entry[j], (int, float)):
                                        score_val = float(score_entry[j])
                                    else:
                                        # Default score if not a number
                                        score_val = 1.0
                                elif isinstance(score_entry, (int, float)):
                                    score_val = float(score_entry)
                                else:
                                    score_val = 1.0
                                
                                candidates.append(CandidateQuote(
                                    text=str(doc_text),
                                    reference=meta_dict,
                                    score=score_val
                                ))
                                self.logger.debug(f"Added candidate from flat document with metadata list: level={level}, doc={i}, meta={j}")
        
        self.logger.info(f"Extracted {len(candidates)} candidates from {level} level")
        return candidates

    def hybrid_search(self, modern_line: str, top_k: int = 10) -> Dict[str, List[CandidateQuote]]:
        """
        Perform a hybrid search combining vector embeddings with keyword matching.
        
        Args:
            modern_line: The modern text line to find Shakespearean quotes for
            top_k: Number of results to return per search method
            
        Returns:
            Dictionary with candidate quotes from different levels
        """
        self.logger.info(f"Performing hybrid search for: '{modern_line}'")
        
        # Call the search engine's hybrid search method
        results = self.search_engine.hybrid_search(modern_line, top_k)
        
        # Process the results into CandidateQuote objects, similar to retrieve_all
        return {
            "line": self._extract_candidates([results["search_chunks"]["line"]], "line"),
            "phrases": [
                candidate
                for group in results["search_chunks"]["phrases"]
                for candidate in self._extract_candidates([group], "phrases")
            ],
            "fragments": [
                candidate
                for group in results["search_chunks"]["fragments"]
                for candidate in self._extract_candidates([group], "fragments")
            ],
        }
