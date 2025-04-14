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
            "line": self._extract_candidates(results["search_chunks"]["line"], "line"),
            "phrases": self._extract_candidates(results["search_chunks"]["phrases"], "phrases"),
            "fragments": self._extract_candidates(results["search_chunks"]["fragments"], "fragments"),
        }

    def _extract_candidates(self, raw_results: List[Dict[str, Any]], level: str) -> List[CandidateQuote]:
        candidates = []
        for result in raw_results:
            docs = result.get("documents", [])
            metas = result.get("metadatas", [])
            scores = result.get("distances", [])
            for doc, meta, score in zip(docs, metas, scores):
                candidates.append(CandidateQuote(
                    text=doc,
                    reference=meta,
                    score=score
                ))
        self.logger.debug(f"Extracted {len(candidates)} candidates from {level} level")
        return candidates
