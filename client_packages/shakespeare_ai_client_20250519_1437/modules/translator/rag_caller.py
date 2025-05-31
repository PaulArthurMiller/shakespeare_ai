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

        # Log the structure of raw_results
        self.logger.debug(f"_extract_candidates for {level} - Input structure type: {type(raw_results)}")
        self.logger.debug(f"_extract_candidates for {level} - Input length: {len(raw_results)}")
        if raw_results:
            first_item = raw_results[0]
            self.logger.debug(f"_extract_candidates for {level} - First item type: {type(first_item)}")
            if isinstance(first_item, dict):
                self.logger.debug(f"_extract_candidates for {level} - First item keys: {list(first_item.keys())}")

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
        
        # ADD THIS: Detailed validation of the created CandidateQuote objects
        if candidates:
            for i, candidate in enumerate(candidates[:3]):  # Check first 3
                if not hasattr(candidate, "text") or not candidate.text:
                    self.logger.warning(f"Candidate {i} missing text attribute")
                if not hasattr(candidate, "reference") or not candidate.reference:
                    self.logger.warning(f"Candidate {i} missing reference attribute")
                elif not isinstance(candidate.reference, dict):
                    self.logger.warning(f"Candidate {i} reference is not a dict, type: {type(candidate.reference)}")
                else:
                    self.logger.debug(f"Candidate {i} reference keys: {list(candidate.reference.keys())}")
                if not hasattr(candidate, "score"):
                    self.logger.warning(f"Candidate {i} missing score attribute")
            
            # Log example of the first complete candidate
            if len(candidates) > 0:
                c = candidates[0]
                try:
                    self.logger.debug(f"First candidate example - text: '{c.text[:30]}...', " +
                                    f"score: {c.score}, " +
                                    f"reference keys: {list(c.reference.keys()) if isinstance(c.reference, dict) else 'not a dict'}")
                except Exception as e:
                    self.logger.warning(f"Error logging candidate: {e}")

        return candidates

    def hybrid_search(self, modern_line: str, top_k: int = 10) -> Dict[str, List[CandidateQuote]]:
        """
        Perform a hybrid search combining vector embeddings with keyword matching.
        """
        self.logger.info(f"Performing hybrid search for: '{modern_line}'")
        
        try:
            # Call the search engine's hybrid search method
            results = self.search_engine.hybrid_search(modern_line, top_k)
            
            # Log the structure of results for debugging
            self.logger.debug(f"Raw hybrid search results keys: {list(results.keys())}")
            if "search_chunks" in results:
                self.logger.debug(f"Search chunks keys: {list(results.get('search_chunks', {}).keys())}")
                # Log the structure of each search chunk type
                for chunk_type in ["line", "phrases", "fragments"]:
                    chunk_data = results.get("search_chunks", {}).get(chunk_type, None)
                    if chunk_data is not None:
                        if isinstance(chunk_data, list):
                            self.logger.debug(f"{chunk_type} is a list with {len(chunk_data)} items")
                            for i, item in enumerate(chunk_data[:2]):  # Log first 2 items max
                                self.logger.debug(f"{chunk_type}[{i}] keys: {list(item.keys()) if isinstance(item, dict) else 'not a dict'}")
                        elif isinstance(chunk_data, dict):
                            self.logger.debug(f"{chunk_type} is a dict with keys: {list(chunk_data.keys())}")
                        else:
                            self.logger.debug(f"{chunk_type} is type: {type(chunk_data)}")
            
            # Ensure we have a valid results structure before proceeding
            if not results or "search_chunks" not in results:
                self.logger.error("Invalid results structure from hybrid search")
                return {"line": [], "phrases": [], "fragments": []}
            
            search_chunks = results["search_chunks"]
            
            # Process each level, ensuring we always have lists
            processed_results = {
                "line": self._extract_candidates([search_chunks.get("line", {})], "line"),
                "phrases": [],
                "fragments": []
            }
            
            # Process phrases - handle both list and non-list formats
            phrases_chunks = search_chunks.get("phrases", [])
            if phrases_chunks:
                if isinstance(phrases_chunks, list):
                    for group in phrases_chunks:
                        candidates = self._extract_candidates([group], "phrases")
                        processed_results["phrases"].extend(candidates)
                else:
                    # If it's not a list, try processing it directly
                    candidates = self._extract_candidates([phrases_chunks], "phrases")
                    processed_results["phrases"].extend(candidates)
            
            # Process fragments - handle both list and non-list formats
            fragments_chunks = search_chunks.get("fragments", [])
            if fragments_chunks:
                if isinstance(fragments_chunks, list):
                    for group in fragments_chunks:
                        candidates = self._extract_candidates([group], "fragments")
                        processed_results["fragments"].extend(candidates)
                else:
                    # If it's not a list, try processing it directly
                    candidates = self._extract_candidates([fragments_chunks], "fragments")
                    processed_results["fragments"].extend(candidates)
            
            # Log the processed results for debugging
            total_candidates = (
                len(processed_results["line"]) +
                len(processed_results["phrases"]) +
                len(processed_results["fragments"])
            )
            
            self.logger.info(f"Hybrid search processed results: {len(processed_results['line'])} lines, "
                            f"{len(processed_results['phrases'])} phrases, "
                            f"{len(processed_results['fragments'])} fragments "
                            f"(total: {total_candidates})")
            
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Error in hybrid search: {e}")
            # Return empty results as fallback
            return {"line": [], "phrases": [], "fragments": []}
