import re
from typing import List, Optional
from pathlib import Path
from logger import CustomLogger


class DocumentReader:
    def __init__(self, logger: Optional[CustomLogger] = None):
        self.logger = logger or CustomLogger("DocumentReader")
        self.cleaned_lines: List[str] = []

    def read_file(self, file_path: str) -> List[str]:
        path = Path(file_path)
        if not path.exists():
            self.logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"No such file: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()
        self.logger.info(f"Read {len(raw_lines)} lines from {file_path}")

        self.cleaned_lines = self._clean_lines(raw_lines)
        self.logger.info(f"Cleaned down to {len(self.cleaned_lines)} lines")
        return self.cleaned_lines

    def _clean_lines(self, lines: List[str]) -> List[str]:
        cleaned_lines = []
        in_copyright_block = False
        stage_keywords = {"exit", "exeunt", "enter", "re-enter"}

        for i, line in enumerate(lines):
            original_line = line
            line = line.rstrip('\n')

            # Detect and remove copyright blocks
            if "<<" in line:
                in_copyright_block = True
                self.logger.debug(f"Line {i}: Removed copyright block start -> {original_line.strip()}")
                continue
            if ">>" in line:
                in_copyright_block = False
                self.logger.debug(f"Line {i}: Removed copyright block end -> {original_line.strip()}")
                continue
            if in_copyright_block:
                self.logger.debug(f"Line {i}: Removed line inside copyright block -> {original_line.strip()}")
                continue

            # Skip fully blank lines
            if not line.strip():
                self.logger.debug(f"Line {i}: Removed blank line")
                continue

            # Normalize whitespace and lowercase for detection
            normalized_line = line.strip().lower()

            # Check for stage directions based on keyword and placement
            for keyword in stage_keywords:
                if keyword in normalized_line:
                    index = normalized_line.find(keyword)
                    pre_keyword = normalized_line[:index]
                    if pre_keyword.strip() == "":
                        self.logger.debug(f"Line {i}: Removed stage direction (keyword: {keyword}) -> {original_line.strip()}")
                        break  # Do not append
            else:
                cleaned_lines.append(line.strip())

        return cleaned_lines


# Example usage block
if __name__ == "__main__":
    from pathlib import Path

    input_path = Path("data/raw_texts/working_complete_shakespeare.txt")
    output_path = Path("data/raw_texts/working_cleaned.txt")

    reader = DocumentReader()
    with open(input_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    cleaned = reader._clean_lines(raw_lines)

    with open(output_path, "w", encoding="utf-8") as f:
        for line in cleaned:
            f.write(line + "\n")

    print(f"✅ Cleaned file saved to: {output_path}")

