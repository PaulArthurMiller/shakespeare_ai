# main.py

# from modules.playwright.story_expander import StoryExpander

# def main():
#     expander = StoryExpander(
#         config_path="modules/playwright/config.py",
#         act_overview_path="data/prompts/act_overview.json",
#         character_voices_path="data/prompts/character_voices.json"
#     )
#     expanded_story = expander.expand_all()
#     print("Expansion complete. Check 'data/modern_play/expanded_story.json' for output.")

# if __name__ == "__main__":
#     main()

# main.py

# from modules.playwright.scene_writer import SceneWriter

# def main():
#     writer = SceneWriter(
#         config_path="modules/playwright/config.py",
#         expanded_story_path="data/modern_play/expanded_story2.json"
#     )
#     writer.generate_scenes()
#     print("Scene generation complete. Check 'data/modern_play/generated_scenes_claude2' for output.")

# if __name__ == "__main__":
#     main()

# import os

# def roman_to_int(roman: str) -> int:
#     roman_map = {'i': 1, 'v': 5, 'x': 10}
#     result = 0
#     prev = 0
#     for char in reversed(roman.lower()):
#         value = roman_map.get(char, 0)
#         if value < prev:
#             result -= value
#         else:
#             result += value
#             prev = value
#     return result

# directory = "data/modern_play/generated_scenes_claude2"
# output_path = "data/modern_play/modern_play_combined2.md"

# scene_files = sorted(
#     [f for f in os.listdir(directory) if f.endswith(".md")],
#     key=lambda x: (
#         roman_to_int(x.split("_")[1]),
#         int(x.split("_")[3].split(".")[0])
#     )
# )

# combined_script = ""
# for filename in scene_files:
#     with open(os.path.join(directory, filename), "r", encoding="utf-8") as f:
#         combined_script += f.read().strip() + "\n\n"

# with open(output_path, "w", encoding="utf-8") as f:
#     f.write(combined_script)

# print(f"Combined play saved to: {output_path}")

# main.py

# main.py

# main.py

import os
import re
import argparse
import logging
from typing import List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from modules.translator.translation_manager import TranslationManager
from modules.translator.scene_saver import SceneSaver
from modules.utils.logger import CustomLogger

def setup_logging(log_level: str = "DEBUG", save_logs: bool = True) -> CustomLogger:
    """Set up logging with specified level and save option."""
    
    # Create logs directory if it doesn't exist
    if save_logs:
        os.makedirs("logs", exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"logs/translation_{timestamp}.log"
    else:
        log_file = None
    
    # Initialize logger with DEBUG level for file logging
    # This ensures we capture all details in the file while still respecting terminal verbosity
    logger = CustomLogger("TranslationMain", log_level="DEBUG" if save_logs else log_level, log_file=log_file)
    
    # Set up custom formatting for file handler if we're saving logs
    if save_logs and hasattr(logger, "logger") and logger.logger.handlers:
        for handler in logger.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                # Use a more verbose format for file logging
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                ))
                # Ensure file handler captures everything
                handler.setLevel(logging.DEBUG)
    
    logger.info(f"Logging initialized at {log_level} level for console" + 
                (f" and DEBUG level to {log_file}" if log_file else ""))
    
    return logger

def extract_act_scene_from_filename(filepath: str) -> Tuple[str, str]:
    """Extract act and scene numbers from filename."""
    filename = os.path.basename(filepath)
    
    # Try common format patterns
    patterns = [
        r"act_?(\w+)_?scene_?(\w+)",  # act_1_scene_2, act1_scene2, etc.
        r"a(\w+)s(\w+)",              # a1s2, aIs, etc.
        r"(\w+)_(\w+)",               # I_1, 1_2, etc.
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)
    
    # Default if no pattern matches
    return "unknown", "unknown"

def parse_markdown_file(filepath: str) -> List[str]:
    """
    Parse a markdown file to extract individual lines for translation.
    Skip headers, blank lines, and non-dialogue content.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into lines
    lines = content.split('\n')
    
    # Filter out headers, blank lines, and stage directions
    dialogue_lines = []
    for line in lines:
        line = line.strip()
        # Skip if empty or looks like a header, stage direction, or character name
        if (not line or 
            line.startswith('#') or 
            line.startswith('---') or
            (line.startswith('[') and line.endswith(']')) or
            line.isupper()):
            continue
        dialogue_lines.append(line)
    
    return dialogue_lines

def translate_scene_from_file(
    filepath: str, 
    output_dir: str = "outputs/translated_scenes",
    log_level: str = "INFO",
    save_logs: bool = True,
    checkpoint_interval: int = 5
) -> None:
    """
    Translate a scene from a markdown file.
    """
    # Setup logging
    logger = setup_logging(log_level, save_logs)
    
    # Ensure all module loggers respect the file logging setup
    for module_name in ["Assembler", "Selector", "Validator", "RagCaller", "TranslationManager"]:
        module_logger = CustomLogger(module_name, log_level="DEBUG" if save_logs else log_level)
        if save_logs and hasattr(logger, "logger") and logger.logger.handlers:
            for handler in [h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)]:
                # Add the file handler to this logger too
                module_logger.logger.addHandler(handler)
    
    # Extract act and scene from filename
    act, scene = extract_act_scene_from_filename(filepath)
    logger.info(f"Processing file: {filepath}")
    logger.info(f"Identified as Act {act}, Scene {scene}")
    
    # Parse the file to get dialogue lines
    lines = parse_markdown_file(filepath)
    logger.info(f"Extracted {len(lines)} dialogue lines for translation")
    
    if not lines:
        logger.error("No dialogue lines found in file. Please check the format.")
        return
    
    # Initialize translation manager
    manager = TranslationManager()
    manager.start_translation_session()
    
    # Translate the lines
    translated_lines = manager.translate_group(lines)
    logger.info(f"Translated {len(translated_lines)} lines")
    
    # Save output with original lines
    saver = SceneSaver(output_dir=output_dir)
    saver.save_scene(
        act=act,
        scene=scene,
        translated_lines=translated_lines,
        original_lines=lines,
        checkpoint_interval=checkpoint_interval
    )
    
    logger.info(f"Scene translation complete. Output saved to {output_dir}/act_{act.lower()}_scene_{scene}")

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Shakespeare Translation System")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Sample lines translator (original functionality)
    sample_parser = subparsers.add_parser("sample", help="Translate sample lines")
    
    # File translator
    file_parser = subparsers.add_parser("file", help="Translate a scene from a file")
    file_parser.add_argument("filepath", type=str, help="Path to markdown file with the scene")
    file_parser.add_argument("--output-dir", type=str, default="outputs/translated_scenes",
                            help="Directory to save output (default: outputs/translated_scenes)")
    file_parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                            default="INFO", help="Logging level (default: INFO)")
    file_parser.add_argument("--no-save-logs", action="store_true", 
                            help="Don't save logs to file")
    file_parser.add_argument("--checkpoint", type=int, default=5,
                            help="Save checkpoint every N lines (default: 5)")
    
    args = parser.parse_args()
    
    if args.command == "file":
        translate_scene_from_file(
            filepath=args.filepath,
            output_dir=args.output_dir,
            log_level=args.log_level,
            save_logs=not args.no_save_logs,
            checkpoint_interval=args.checkpoint
        )
    else:  # Default to sample if no command or "sample" command
        # Original sample functionality
        test_lines = [
            "The wise Edgar, they called you once.",
            "The brilliant strategist, the trusted voice.",
            "Now look—reduced to breathing flesh,",
            "A symbol rather than a man."
        ]

        # Initialize manager and session
        manager = TranslationManager()
        manager.start_translation_session()

        # Run translation
        translated_lines = manager.translate_group(test_lines)

        # Save output with original modern lines explicitly provided
        saver = SceneSaver(output_dir="outputs/test_run")
        saver.save_scene(
            act="Test", 
            scene="1", 
            translated_lines=translated_lines,
            original_lines=test_lines
        )

        # Print summary
        print("\n=== Translated Lines ===\n")
        for i, line in enumerate(translated_lines, 1):
            print(f"{i}. Shakespeare: {line['text']}")
            
            # Print references
            refs = []
            for ref in line.get('references', []):
                source = ref.get('title', '')
                act = ref.get('act', '')
                scene = ref.get('scene', '')
                line_num = ref.get('line', '')
                refs.append(f"{source} ({act}.{scene}.{line_num})")
            
            print(f"   References: {', '.join(refs)}")
            print(f"   Modern: {line.get('original_modern_line', '')}")
            print()

if __name__ == "__main__":
    main()