# modules/translator/types.py

from dataclasses import dataclass
from typing import Dict

@dataclass
class CandidateQuote:
    text: str
    reference: Dict[str, str]  # includes title, act, scene, line, word_index
    score: float
