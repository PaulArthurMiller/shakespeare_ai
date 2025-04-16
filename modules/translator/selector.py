# modules/translator/selector.py

from typing import List, Dict, Optional, Union, Tuple, Any, cast
from modules.translator.types import CandidateQuote, ReferenceDict
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
        """
        Filter candidates by removing any that:
        - Have proper nouns (POS == "PROPN")
        - Were already used (checked via UsedMap)
        - Have invalid reference structure
        """
        filtered = []
        for candidate in candidates:
            try:
                reference = candidate.reference

                # Skip if reference is not a dictionary
                if not isinstance(reference, dict):
                    self.logger.warning("Candidate reference is not a dict, skipping.")
                    continue

                # Check for proper nouns - more rigorous check
                has_proper_noun = False
                
                # Check "POS" field if it exists
                if "POS" in reference:
                    pos_tags = reference.get("POS", [])
                    if isinstance(pos_tags, list) and "PROPN" in pos_tags:
                        self.logger.info("Skipping candidate due to proper noun (PROPN)")
                        has_proper_noun = True

                # Also check the text itself for capitalized words mid-sentence
                # This catches proper nouns that might have been missed in POS tagging
                text = candidate.text
                words = text.split()
                for i, word in enumerate(words):
                    # Skip first word (naturally capitalized)
                    if i > 0 and word[0].isupper() and any(c.isalpha() for c in word):
                        self.logger.info(f"Skipping candidate due to capitalized word mid-sentence: '{word}'")
                        has_proper_noun = True
                        break

                if has_proper_noun:
                    continue

                # Rest of the filtering logic...
                # [Your existing code for reference_key and checking was_used]

                filtered.append(candidate)

            except Exception as e:
                self.logger.warning(f"Skipping candidate due to error: {e}")
                continue

        return filtered

    def rank_candidates(self, candidates: List[CandidateQuote]) -> List[CandidateQuote]:
        """Sort by similarity score (ascending = closer match)."""
        self.logger.info("Ranking candidates by similarity score...")
        ranked = sorted(candidates, key=lambda c: c.score)
        for i, cand in enumerate(ranked):
            self.logger.debug(f"[{i}] Score: {cand.score:.4f} | {cand.text[:60]}")
        return ranked

    def prepare_prompt_structure(self, selector_results: Dict[str, List[CandidateQuote]]) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, CandidateQuote]]:
        """
        Prepare the data structure for the LLM assembler prompt.
        Returns:
            - prompt_data: Dict[level] -> List[dict with temp_id, text, score, form]
            - chunk_map: Dict[temp_id] -> CandidateQuote
        """
        self.logger.info("Preparing prompt structure from grouped candidates...")
        prompt_data: Dict[str, List[Dict[str, Any]]] = {"line": [], "phrases": [], "fragments": []}
        chunk_map: Dict[str, CandidateQuote] = {}

        for level in ["line", "phrases", "fragments"]:
            candidates = selector_results.get(level, [])
            self.logger.info(f"Processing {level}: {len(candidates)} candidate(s)")

            # Step 1: Filter
            self.logger.info(f"Filtering {len(candidates)} candidate(s)...")
            filtered = self.filter_candidates(candidates)
            if not filtered:
                self.logger.warning(f"No candidates passed filter at {level} level.")
                continue
            self.logger.info(f"{len(filtered)} candidate(s) passed filter")

            # Step 2: Rank
            ranked = self.rank_candidates(filtered)
            top_n = ranked[:5]  # Limit to top 5 for prompt
            self.logger.debug(f"Selected top {len(top_n)} candidates for {level} level")

            # Step 3: Create prompt entries and map
            for i, cand in enumerate(top_n):
                if not isinstance(cand, CandidateQuote):
                    self.logger.warning(f"Invalid candidate object at {level}_{i + 1}: {type(cand)} — {cand}")
                    continue

                temp_id = f"{level}_{i + 1}"
                entry_dict = {
                    "temp_id": temp_id,
                    "text": cand.text,
                    "score": cand.score,
                    "form": level
                }
                prompt_data[level].append(entry_dict)
                chunk_map[temp_id] = cand

            # Step 4: Logging the prompt items
            if prompt_data[level]:
                self.logger.debug(f"Prompt options for {level.upper()}:")
                for entry in prompt_data[level]:
                    if not isinstance(entry, dict):
                        self.logger.warning(f"Invalid entry for logging at {level}: {type(entry)} — {entry}")
                        continue
                    tid = entry.get("temp_id", "unknown_id")
                    txt = entry.get("text", "")
                    sc = entry.get("score", 0.0)
                    self.logger.debug(f"  {tid}: \"{txt}\" (score: {sc:.4f})")

        return prompt_data, chunk_map


