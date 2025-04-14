# modules/validation/validator.py

import os
import json
import re
import unicodedata
from typing import Dict, Any, List
from modules.utils.logger import CustomLogger

class Validator:
    def __init__(self, ground_truth_path: str = "data/processed_chunks/lines.json"):
        self.logger = CustomLogger("Validator")
        self.logger.info("Initializing Validator")
        self.ground_truth_path = ground_truth_path
        self.ground_truth = self._load_ground_truth()

    def _load_ground_truth(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.ground_truth_path):
            self.logger.error(f"Ground truth file not found: {self.ground_truth_path}")
            raise FileNotFoundError(f"Missing ground truth file at {self.ground_truth_path}")
        try:
            with open(self.ground_truth_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.logger.info(f"Loaded {len(data['chunks'])} ground truth lines")
            return data["chunks"]
        except Exception as e:
            self.logger.critical(f"Error loading ground truth: {e}")
            return []

    def _normalize_and_clean(self, text: str) -> str:
        """Normalize and remove punctuation for lexical comparison."""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"[^\w\s']", "", text)  # remove punctuation except apostrophes
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    def validate_line(self, assembled_line: str, reference_info: List[Dict[str, str]]) -> bool:
        """Validate that all references are legit and the combined source text matches the assembled line (ignoring punctuation)."""
        try:
            matched_texts = []

            for ref in reference_info:
                match = next(
                    (entry for entry in self.ground_truth
                     if entry.get("title") == ref.get("title") and
                        entry.get("act") == ref.get("act") and
                        entry.get("scene") == ref.get("scene") and
                        entry.get("line") == ref.get("line") and
                        entry.get("word_index") == ref.get("word_index")),
                    None
                )

                if not match:
                    self.logger.warning(f"No match found in ground truth for reference: {ref}")
                    return False

                matched_texts.append(match.get("text", "").strip())

            combined_text = " ".join(matched_texts).strip()

            if self._normalize_and_clean(combined_text) != self._normalize_and_clean(assembled_line):
                self.logger.warning("Normalized assembled line does not match normalized source reference text")
                self.logger.debug(f"Expected: '{self._normalize_and_clean(combined_text)}'")
                self.logger.debug(f"Got:      '{self._normalize_and_clean(assembled_line)}'")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating assembled line: {e}")
            return False
    
    def validate_usage(self, candidate: Dict[str, Any], usage_map) -> bool:
        try:
            reference_key = f"{candidate['title']}|{candidate['act']}|{candidate['scene']}|{candidate['line']}"
            word_range = candidate.get("word_index", "0,0")
            start_idx, end_idx = map(int, word_range.split(","))
            used = usage_map.was_used(reference_key, context=f"{start_idx}-{end_idx}")
            if used:
                self.logger.info(f"Candidate reuse rejected: {candidate['chunk_id']} overlaps used indices.")
            return not used
        except Exception as e:
            self.logger.error(f"Error validating usage for candidate {candidate.get('chunk_id')}: {e}")
            return False

    def log_validation_error(self, details: Dict[str, Any]) -> None:
        try:
            self.logger.error("Validation failed")
            for key, value in details.items():
                self.logger.error(f"  {key}: {value}")
        except Exception as e:
            self.logger.critical(f"Failed to log validation error: {e}")
