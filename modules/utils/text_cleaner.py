"""
Shakespeare Text Cleaner

This script cleans Shakespeare's text files for processing by LineChunker.
It follows a progressive approach to:
1. Mark titles
2. Mark acts and scenes
3. Remove stage directions in brackets
4. Process the marked text to keep only relevant content

Usage:
    python shakespeare_cleaner.py input.txt output.txt
"""

import re
import sys
import os
from typing import List, Dict, Any, Optional, Match, Pattern

# Import the custom logger from the project library
from logger import CustomLogger

# List of Shakespeare titles for identification
SHAKESPEARE_TITLES = {
    "THE SONNETS",
    "ALL'S WELL THAT ENDS WELL",
    "THE TRAGEDY OF ANTONY AND CLEOPATRA",
    "AS YOU LIKE IT",
    "THE COMEDY OF ERRORS",
    "THE TRAGEDY OF CORIOLANUS",
    "CYMBELINE",
    "THE TRAGEDY OF HAMLET, PRINCE OF DENMARK",
    "THE FIRST PART OF KING HENRY THE FOURTH",
    "THE SECOND PART OF KING HENRY THE FOURTH",
    "THE LIFE OF KING HENRY THE FIFTH",
    "THE FIRST PART OF HENRY THE SIXTH",
    "THE SECOND PART OF KING HENRY THE SIXTH",
    "THE THIRD PART OF KING HENRY THE SIXTH",
    "KING HENRY THE EIGHTH",
    "THE LIFE AND DEATH OF KING JOHN",
    "THE TRAGEDY OF JULIUS CAESAR",
    "THE TRAGEDY OF KING LEAR",
    "LOVE'S LABOUR'S LOST",
    "THE TRAGEDY OF MACBETH",
    "MEASURE FOR MEASURE",
    "THE MERCHANT OF VENICE",
    "THE MERRY WIVES OF WINDSOR",
    "A MIDSUMMER NIGHT'S DREAM",
    "MUCH ADO ABOUT NOTHING",
    "THE TRAGEDY OF OTHELLO, THE MOOR OF VENICE",
    "PERICLES, PRINCE OF TYRE",
    "KING RICHARD THE SECOND",
    "KING RICHARD THE THIRD",
    "THE TRAGEDY OF ROMEO AND JULIET",
    "THE TAMING OF THE SHREW",
    "THE TEMPEST",
    "THE LIFE OF TIMON OF ATHENS",
    "THE TRAGEDY OF TITUS ANDRONICUS",
    "TROILUS AND CRESSIDA",
    "TWELFTH NIGHT; OR, WHAT YOU WILL",
    "THE TWO GENTLEMEN OF VERONA",
    "THE TWO NOBLE KINSMEN",
    "THE WINTER'S TALE",
    "A LOVER'S COMPLAINT",
    "THE PASSIONATE PILGRIM",
    "THE PHOENIX AND THE TURTLE",
    "THE RAPE OF LUCRECE",
    "VENUS AND ADONIS"
}

# Markers that we'll use to tag lines we want to keep
TITLE_MARKER = "kEEp_TITLE"
ACT_MARKER = "kEEp_ACT"
SCENE_MARKER = "kEEp_SCENE"

class ShakespeareTextCleaner:
    """
    A class to clean Shakespeare's text for processing by LineChunker.
    """
    
    def __init__(self, logger: Optional[CustomLogger] = None):
        """
        Initialize the text cleaner.
        
        Args:
            logger: Optional custom logger instance
        """
        self.logger = logger or CustomLogger("ShakespeareTextCleaner")
        self.logger.info("Initializing Shakespeare Text Cleaner")
        
        # Compile regex patterns once for efficiency
        self.act_pattern: Pattern[str] = re.compile(r'^ACT\s+([IVX]+)$', re.IGNORECASE)
        self.scene_pattern: Pattern[str] = re.compile(r'^(?:SCENE|PROLOGUE)\s+([IVX]+)$', re.IGNORECASE)
        self.bracketed_content_pattern: Pattern[str] = re.compile(r'\[.*?\]')
        self.character_name_pattern: Pattern[str] = re.compile(r'^[A-Z][A-Z\s]+\.$')
        
        # Add pattern for sonnet numbers (just a digit or digits on a line by itself)
        self.sonnet_number_pattern: Pattern[str] = re.compile(r'^\s*(\d+)\s*$')
    
    def read_file(self, filepath: str) -> str:
        """
        Read the content of a file.
        
        Args:
            filepath: Path to the file to read
            
        Returns:
            The content of the file
            
        Raises:
            FileNotFoundError: If the file does not exist
        """
        self.logger.info(f"Reading file: {filepath}")
        if not os.path.exists(filepath):
            self.logger.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"File not found: {filepath}")
            
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                self.logger.debug(f"Successfully read {len(content)} characters")
                return content
        except Exception as e:
            self.logger.error(f"Error reading file {filepath}: {str(e)}")
            raise

    def write_file(self, filepath: str, content: str) -> None:
        """
        Write content to a file.
        
        Args:
            filepath: Path to the file to write
            content: Content to write
            
        Raises:
            IOError: If the file cannot be written
        """
        self.logger.info(f"Writing to file: {filepath}")
        try:
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(content)
                self.logger.debug(f"Successfully wrote {len(content)} characters")
        except Exception as e:
            self.logger.error(f"Error writing to file {filepath}: {str(e)}")
            raise

    def mark_title(self, text: str) -> str:
        """
        Find and mark all titles of plays and collections in the text.
        
        Args:
            text: The input text
            
        Returns:
            The text with all titles marked
        """
        self.logger.info("Marking all titles in text")
        lines = text.split('\n')
        marked_count = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped in SHAKESPEARE_TITLES:
                self.logger.info(f"Found title: {line_stripped}")
                lines[i] = f"{line} {TITLE_MARKER}"
                marked_count += 1
        
        if marked_count == 0:
            self.logger.warning("No titles found in the text")
        else:
            self.logger.info(f"Marked {marked_count} titles in the text")
            
        return '\n'.join(lines)

    def mark_act_scene_headers(self, text: str) -> str:
        """
        Mark act and scene headers in the text.
        
        Args:
            text: The input text
            
        Returns:
            The text with act and scene headers marked
        """
        self.logger.info("Marking act and scene headers")
        lines = text.split('\n')
        marked_lines = []
        
        # Handle the sonnets differently
        in_sonnets = False
        in_other_play = False
        current_play = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            original_line = lines[i]
            
            # Check if this is a title line
            if TITLE_MARKER in original_line:
                if "THE SONNETS" in line.upper():
                    self.logger.info("Found THE SONNETS title - entering sonnets mode")
                    in_sonnets = True
                    in_other_play = False
                    current_play = "THE SONNETS"
                else:
                    self.logger.info(f"Found other play title: {line} - exiting sonnets mode if active")
                    in_sonnets = False
                    in_other_play = True
                    current_play = line.replace(TITLE_MARKER, "").strip()
                
                # Add the title line
                marked_lines.append(original_line)
                
                # For sonnets, add the ACT I after the title
                if in_sonnets:
                    # Add a blank line and then ACT I header
                    marked_lines.append("")
                    marked_lines.append(f"ACT I {ACT_MARKER}")
                
                i += 1
                continue
            
            # Handle sonnets - check if this is a sonnet number
            if in_sonnets:
                sonnet_match = self.sonnet_number_pattern.match(line)
                if sonnet_match and line:
                    sonnet_number = sonnet_match.group(1)
                    self.logger.debug(f"Found sonnet number: {sonnet_number}")
                    # Replace the line with a scene marker for this sonnet number
                    marked_lines.append(f"SCENE {sonnet_number} {SCENE_MARKER}")
                    i += 1
                    continue
            
            # For other plays, look for act and scene headers
            if in_other_play:
                # Check if it's an act header
                act_match = self.act_pattern.match(line)
                if act_match:
                    # Check if it has blank lines before and after
                    if (i > 0 and i < len(lines) - 1 and
                        not lines[i-1].strip()):
                        self.logger.debug(f"Found act header: '{line}'")
                        marked_lines.append(f"{original_line} {ACT_MARKER}")
                        i += 1
                        continue
                
                # Check if it's a scene header
                scene_match = self.scene_pattern.match(line)
                if scene_match:
                    # Check if it has blank lines before
                    if i > 0 and not lines[i-1].strip():
                        self.logger.debug(f"Found scene header: '{line}'")
                        marked_lines.append(f"{original_line} {SCENE_MARKER}")
                        i += 1
                        continue
            
            # If we didn't match any special patterns, just add the line as is
            marked_lines.append(original_line)
            i += 1
        
        # Count how many markers were added
        act_markers = sum(1 for line in marked_lines if ACT_MARKER in line)
        scene_markers = sum(1 for line in marked_lines if SCENE_MARKER in line)
        title_markers = sum(1 for line in marked_lines if TITLE_MARKER in line)
        
        self.logger.info(f"Marked {title_markers} titles, {act_markers} act headers, and {scene_markers} scene headers")
        
        return '\n'.join(marked_lines)

    def remove_bracketed_content(self, text: str) -> str:
        """
        Remove stage directions enclosed in square brackets.
        
        Args:
            text: The input text
            
        Returns:
            The text with bracketed content removed
        """
        self.logger.info("Removing bracketed content")
        
        # Count bracketed sections before removal
        original_count = text.count('[')
        
        # Remove content between square brackets (common for stage directions)
        cleaned_text = self.bracketed_content_pattern.sub('', text)
        
        # Count remaining bracketed sections after removal
        remaining_count = cleaned_text.count('[')
        removed_count = original_count - remaining_count
        
        self.logger.debug(f"Removed {removed_count} bracketed sections")
        return cleaned_text

    def process_marked_text(self, text: str) -> str:
        """
        Process the marked text to keep only relevant lines.
        
        Args:
            text: The marked text
            
        Returns:
            The cleaned text with only the relevant lines
        """
        self.logger.info("Processing marked text")
        lines = text.split('\n')
        output_lines = []
        skip_until_blank = False
        in_scene_description = False
        
        # For tracking which play/section we're in
        in_sonnets = False
        current_play = None
        found_first_act_in_current_play = False
        
        # Log initial state
        self.logger.debug(f"Total lines to process: {len(lines)}")
        self.logger.debug(f"Number of lines with title marker: {sum(1 for line in lines if TITLE_MARKER in line)}")
        self.logger.debug(f"Number of lines with act marker: {sum(1 for line in lines if ACT_MARKER in line)}")
        self.logger.debug(f"Number of lines with scene marker: {sum(1 for line in lines if SCENE_MARKER in line)}")
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_strip = line.strip()
            
            # Always keep marked lines (titles, acts, scenes)
            if TITLE_MARKER in line:
                # Reset play tracking when a new title is found
                if "THE SONNETS" in line.upper():
                    in_sonnets = True
                else:
                    in_sonnets = False
                
                current_play = line_strip.replace(TITLE_MARKER, "").strip()
                found_first_act_in_current_play = False
                
                # Remove the marker from the output
                cleaned_line = line.replace(TITLE_MARKER, "").strip()
                output_lines.append(cleaned_line)
                self.logger.debug(f"Keeping title: {cleaned_line}")
                i += 1
                continue
                
            if ACT_MARKER in line:
                # We've found an act indicator for the current play
                found_first_act_in_current_play = True
                
                # Remove the marker from the output
                cleaned_line = line.replace(ACT_MARKER, "").strip()
                output_lines.append(cleaned_line)
                self.logger.debug(f"Keeping act header: {cleaned_line}")
                i += 1
                continue
                
            if SCENE_MARKER in line:
                # Remove the marker from the output
                cleaned_line = line.replace(SCENE_MARKER, "").strip()
                output_lines.append(cleaned_line)
                self.logger.debug(f"Keeping scene header: {cleaned_line}")
                
                # For sonnets, we don't want to skip anything after the scene marker
                # For regular plays, set flag to indicate we're in a scene description that should be skipped
                if not in_sonnets:
                    in_scene_description = True
                    
                i += 1
                continue
            
            # If we haven't found the first act in the current play yet, skip this line
            if not found_first_act_in_current_play:
                self.logger.debug(f"Skipping line before first act in current play: {line_strip[:50]}...")
                i += 1
                continue
                
            # If we're skipping stage directions, continue until we hit a blank line
            if skip_until_blank:
                if not line_strip:
                    self.logger.debug("Found blank line, ending stage direction skip")
                    skip_until_blank = False
                else:
                    self.logger.debug(f"Skipping line in stage direction: {line_strip[:50]}...")
                i += 1
                continue
                
            # If we're in a scene description, skip until we find an ALL CAPS line ending with a period
            if in_scene_description:
                # Check if this line looks like a character name (all uppercase ending with period)
                is_character_name = bool(line_strip and self.character_name_pattern.match(line_strip))
                if is_character_name:
                    self.logger.debug(f"Found character name at end of scene description: {line_strip}")
                    in_scene_description = False
                    # Skip this line too as it's a character name
                else:
                    self.logger.debug(f"Skipping line in scene description: {line_strip[:50]}...")
                i += 1
                continue
            
            # Special handling for sonnets
            if in_sonnets and line_strip:
                # For sonnets, we want to keep the actual sonnet text
                output_lines.append(line)
                i += 1
                continue
            
            # Handle stage directions that start with "Enter", "Exit", or "Exeunt"
            if line_strip and line_strip.startswith(("Enter ", "Exit ", "Exeunt ")):
                self.logger.debug(f"Skipping stage direction: {line_strip[:50]}...")
                skip_until_blank = True
                i += 1
                continue
                
            # Skip lines that look like character names (all caps ending with period)
            is_character_name = bool(line_strip and self.character_name_pattern.match(line_strip))
            if is_character_name:
                self.logger.debug(f"Skipping character name: {line_strip}")
                i += 1
                continue
                
            # For all other lines, check if they might be dialog
            # If a line is all caps but doesn't have a marker, it might be a stage direction
            if line_strip and line_strip.isupper() and not any(marker in line for marker in [TITLE_MARKER, ACT_MARKER, SCENE_MARKER]):
                self.logger.debug(f"Skipping all caps line (likely stage direction): {line_strip[:50]}...")
                i += 1
                continue
                    
            # If we've made it here, keep the line as it may be dialog
            if line_strip:  # Only log non-empty lines
                self.logger.debug(f"Keeping line as dialog: {line_strip[:50]}...")
            output_lines.append(line)  # Keep the original line with its whitespace
            i += 1
        
        # Join all lines, preserving blank lines for now
        cleaned_text = '\n'.join(output_lines)
        
        self.logger.info(f"Finished processing marked text. Output has {len(output_lines)} lines")
        
        # Log content summary
        has_title = any(line.strip() in SHAKESPEARE_TITLES for line in output_lines)
        has_act = any("ACT " in line.upper() for line in output_lines)
        has_scene = any("SCENE " in line.upper() or "PROLOGUE " in line.upper() for line in output_lines)
        self.logger.debug(f"Output summary - Has title: {has_title}, Has act: {has_act}, Has scene: {has_scene}")
        
        return cleaned_text

    def clean_shakespeare_text(self, input_text: str) -> str:
        """
        Clean Shakespeare's text for processing by LineChunker.
        
        Args:
            input_text: The raw Shakespeare text
            
        Returns:
            The cleaned text
        """
        self.logger.info("Starting Shakespeare text cleaning process")
        
        # Step 1: Mark all titles
        marked_text = self.mark_title(input_text)
        
        # Step 2: Mark act and scene headers, handling sonnets specially
        marked_text = self.mark_act_scene_headers(marked_text)
        
        # Step 3: Remove bracketed content (stage directions)
        marked_text = self.remove_bracketed_content(marked_text)
        
        # Step 4: Process the marked text to keep only relevant content
        cleaned_text = self.process_marked_text(marked_text)
        
        self.logger.info("Shakespeare text cleaning complete")
        return cleaned_text


def main():
    """Main function to process the input file and write the output."""
    # Set input and output file paths directly in the code
    # Modify these paths to point to your actual files
    input_file = "data/raw_texts/test_new_format.txt"
    output_file = "data/processed_texts/cleaned_new_format.txt"
    
    # Alternatively, use command-line arguments if provided
    if len(sys.argv) == 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    
    # Initialize logger
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, "shakespeare_cleaner.log")
    
    logger = CustomLogger("ShakespeareTextCleaner", log_file=log_file)
    cleaner = ShakespeareTextCleaner(logger)
    
    try:
        # Read input file
        logger.info(f"Processing file: {input_file}")
        input_text = cleaner.read_file(input_file)
        
        # Clean text
        cleaned_text = cleaner.clean_shakespeare_text(input_text)
        
        # Write output file
        cleaner.write_file(output_file, cleaned_text)
        
        logger.info(f"Successfully cleaned text and wrote to {output_file}")
        print(f"Successfully cleaned Shakespeare text and wrote to {output_file}")
        
    except Exception as e:
        logger.critical(f"Error processing file: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()