# modules/cleaning/structure_cleaner.py

import re
from pathlib import Path
from typing import List, Optional
from logger import CustomLogger

class StructureCleaner:
    def __init__(self, logger: Optional[CustomLogger] = None):
        self.logger = logger or CustomLogger("StructureCleaner", log_level="DEBUG", log_file="logs/cleaning_pass.log")

    def clean_structure(self, input_path: str, output_path: str) -> None:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        title = None
        year_index = None
        title_index = None
        author_index = None
        start_index = None
        scene_label = None

        # Step 1: Find year, title, and author
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r'^\d{4}$', stripped):
                year_index = i
                self.logger.debug(f"Found year line at {i}: {stripped}")
                continue
            if year_index is not None and not title and stripped and not stripped.lower().startswith("by"):
                title = stripped.title()
                title_index = i
                self.logger.info(f"Detected play title: {title}")
                continue
            if title_index is not None and 'william shakespeare' in stripped.lower():
                author_index = i
                self.logger.debug(f"Author line found at {i}: {stripped}")
                break

        if not title:
            self.logger.warning("No play title found; aborting clean.")
            return

        # Step 2: Find Act I Scene I or Prologue
        if author_index is not None:
            for i in range(author_index + 1, len(lines)):
                line = lines[i].strip()
                next_line = lines[i+1].strip().lower() if i + 1 < len(lines) else ""

                act_scene_match = re.search(r'\bact\b.*\bscene\b.*(i|1)', line, re.IGNORECASE)
                prologue_match = re.match(r'prologue', line, re.IGNORECASE) and next_line.startswith("chor")

                if act_scene_match:
                    start_index = i
                    scene_label = "Scene: 1"
                    self.logger.info(f"Found Act I Scene I line at {i}: {line}")
                    break
                elif prologue_match:
                    start_index = i
                    scene_label = "Scene: Prologue"
                    self.logger.info(f"Found Prologue at line {i}")
                    break
        else:
            self.logger.warning("Author line not found. Skipping title and scene identification.")

        if start_index is None:
            self.logger.warning("Could not find starting scene marker; aborting clean.")
            return

        # Step 3: Replace everything before start_index with title and scene markers
        cleaned_lines: List[str] = []
        cleaned_lines.append(f"Title: {title}")
        if scene_label is not None:
            cleaned_lines.append(scene_label)
        else:
            self.logger.warning("Scene label was not identified; skipping scene marker insertion.")
        cleaned_lines.append("")  # spacer

        # Append from start_index onward
        cleaned_lines.extend([line.rstrip('\n') for line in lines[start_index:]])

        # Step 4: Write cleaned output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(cleaned_lines))

        self.logger.info(f"Cleaned structure written to {output_path}")

# Example usage:
if __name__ == "__main__":
    cleaner = StructureCleaner()
    cleaner.clean_structure(
        input_path="data/raw_texts/working_cleaned.txt",
        output_path="data/raw_texts/working_cleaned2.txt"
    )
