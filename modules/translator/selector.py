# modules/translator/selector.py

from typing import List, Dict, Optional, Union
from modules.translator.types import CandidateQuote
from modules.validation.validator import Validator
from modules.rag.used_map import UsedMap
from modules.utils.logger import CustomLogger


class Selector:
    def __init__(
        self,
        used_map: UsedMap,
        validator: Optional[Validator] = None,
        logger: Optional[CustomLogger] = None
    ):
        self.logger = logger or CustomLogger("Selector")
        self.used_map = used_map
        self.validator = validator or Validator()

    def filter_candidates(self, candidates: List[CandidateQuote]) -> List[CandidateQuote]:
        """Remove candidates that violate usage constraints or fail validation."""
        self.logger.info(f"Filtering {len(candidates)} candidate(s)...")
        filtered = []

        for cand in candidates:
            ref = cand.reference
            ref_key = f"{ref['title']}|{ref['act']}|{ref['scene']}|{ref['line']}"
            index_range = ref.get("word_index", "")

            # Check usage
            if self.used_map.was_used(ref_key, index_range):
                self.logger.debug(f"Filtered (used): {cand.text[:50]}...")
                continue

            # Check ground truth validation
            if not self.validator.validate_line(cand.text, [ref]):
                self.logger.debug(f"Filtered (invalid): {cand.text[:50]}...")
                continue

            filtered.append(cand)

        self.logger.info(f"{len(filtered)} candidate(s) passed filter")
        return filtered

    def rank_candidates(self, candidates: List[CandidateQuote]) -> List[CandidateQuote]:
        """Sort by similarity score (ascending = closer match)."""
        self.logger.info("Ranking candidates by similarity score...")
        ranked = sorted(candidates, key=lambda c: c.score)
        for i, cand in enumerate(ranked):
            self.logger.debug(f"[{i}] Score: {cand.score:.4f} | {cand.text[:60]}")
        return ranked

    def prepare_prompt_structure(
        self,
        grouped_candidates: Dict[str, List[CandidateQuote]],
        top_k: int = 3
    ) -> Dict[str, List[Dict[str, Union[str, float]]]]:
        """
        Format grouped candidates for the Assembler LLM prompt.
        Returns a dict like:
            {
                "line": [{"text": "...", "score": 0.17}, ...],
                "phrases": [...],
                "fragments": [...]
            }
        """
        prompt_data: Dict[str, List[Dict[str, Union[str, float]]]] = {}
        self.logger.info("Preparing prompt structure from grouped candidates...")

        for level, candidates in grouped_candidates.items():
            self.logger.info(f"Processing {level}: {len(candidates)} candidate(s)")
            ranked = self.rank_candidates(self.filter_candidates(candidates))
            prompt_data[level] = [
                {"text": c.text, "score": c.score}
                for c in ranked[:top_k]
            ]

        return prompt_data
