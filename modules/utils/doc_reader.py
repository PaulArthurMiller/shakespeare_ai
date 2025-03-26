import re
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
from modules.utils.logger import CustomLogger

@dataclass
class LineData:
    work: str
    act: Optional[int]
    scene: Optional[int]
    scene_line_number: int
    global_line_number: int
    speaker: Optional[str]
    text: str
    stage_direction: bool
    spoken: bool
    word_index_range: List[int]

class DocumentReader:
    def __init__(self, logger: Optional[CustomLogger] = None):
        self.logger = logger or CustomLogger("DocumentReader")
        self.play_title = None
        self.act = None
        self.scene = None
        self.scene_line_number = 0
        self.global_line_number = 0
        self.speaker_pattern = re.compile(r'^(\s{2,}|\t*)([A-Z][A-Za-z0-9\.\-]+)[:\.]\s{2}(.*)$')

    def read_file(self, file_path: str) -> List[LineData]:
        path = Path(file_path)
        if not path.exists():
            self.logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"No such file: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        parsed_lines = []
        current_speaker = None

        for i, raw_line in enumerate(lines):
            line = raw_line.rstrip('\n')

            # Skip copyright, dramatis personae, and blank lines
            if not line.strip() or line.strip().startswith("<<"):
                continue

            # Detect and set play title based on pattern: year followed by title and "by William Shakespeare"
            if self.play_title is None:
                if re.match(r'^\d{4}\s*$', line.strip()):
                    # Look ahead to find the title
                    for j in range(i+1, min(i+10, len(lines))):
                        next_line = lines[j].strip()
                        if next_line and re.search(r'by\s+William\s+Shakespeare', lines[j+1], re.IGNORECASE):
                            self.play_title = next_line.title()
                            self.logger.info(f"Detected play title: {self.play_title}")
                            break
                continue

            # Detect Act
            act_match = re.match(r'^ACT\s+([IVX]+)', line.strip(), re.IGNORECASE)
            if act_match:
                self.act = self._roman_to_int(act_match.group(1))
                self.scene = None
                self.scene_line_number = 0
                continue

            # Detect Scene
            scene_match = re.match(r'^SCENE\s+([IVX]+)', line.strip(), re.IGNORECASE)
            if scene_match:
                self.scene = self._roman_to_int(scene_match.group(1))
                self.scene_line_number = 0
                continue

            # Detect stage directions or entrances
            if line.strip().startswith("[") or re.match(r'^(Enter|Exit|Exeunt)', line.strip(), re.IGNORECASE):
                continue

            # Detect speaker line
            speaker_match = self.speaker_pattern.match(line)
            if speaker_match:
                current_speaker = speaker_match.group(2).upper()
                speech = speaker_match.group(3).strip()
                parsed_lines.append(self._create_line(current_speaker, speech))
                continue

            # Skip continuation lines
            if line.startswith("    "):
                continue

        return parsed_lines

    def _create_line(self, speaker: str, text: str) -> LineData:
        self.global_line_number += 1
        self.scene_line_number += 1
        words = text.split()
        word_index_range = [0, len(words)-1] if words else [0, 0]
        return LineData(
            work=self.play_title or "Unknown",
            act=self.act,
            scene=self.scene,
            scene_line_number=self.scene_line_number,
            global_line_number=self.global_line_number,
            speaker=speaker,
            text=text,
            stage_direction=False,
            spoken=True,
            word_index_range=word_index_range
        )

    def _roman_to_int(self, roman: str) -> int:
        roman_numerals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        result = 0
        prev = 0
        for char in reversed(roman.upper()):
            value = roman_numerals.get(char, 0)
            if value < prev:
                result -= value
            else:
                result += value
            prev = value
        return result
