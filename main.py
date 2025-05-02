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

# main.py

import os
import re
import argparse
import logging
import glob
import json
import uuid
from typing import List, Optional, Tuple, Dict, Any, Set
from pathlib import Path
from datetime import datetime

from modules.translator.translation_manager import TranslationManager
from modules.translator.scene_saver import SceneSaver
from modules.utils.logger import CustomLogger

# Constants for translation management
TRANSLATION_INFO_DIR = "translation_sessions"
TRANSLATION_INFO_FILE = "translation_info.json"


def generate_friendly_translation_id() -> str:
    """Generate a user-friendly translation ID with timestamp and a short random part."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    random_part = str(uuid.uuid4())[:6]  # Just take 6 characters from the UUID
    return f"trans_{timestamp}_{random_part}"


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


def get_translation_info(translation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get information about a translation session.
    If translation_id is None, list all available sessions.
    """
    os.makedirs(TRANSLATION_INFO_DIR, exist_ok=True)
    
    if translation_id:
        info_path = os.path.join(TRANSLATION_INFO_DIR, f"{translation_id}_{TRANSLATION_INFO_FILE}")
        if os.path.exists(info_path):
            try:
                with open(info_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"translation_id": translation_id, "scenes_translated": [], "created_at": "unknown"}
        else:
            return {"translation_id": translation_id, "scenes_translated": [], "created_at": "unknown"}
    else:
        # Return info about all sessions
        all_sessions = []
        info_files = glob.glob(os.path.join(TRANSLATION_INFO_DIR, f"*_{TRANSLATION_INFO_FILE}"))
        for info_file in info_files:
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    session_info = json.load(f)
                    all_sessions.append(session_info)
            except:
                # Skip invalid files
                pass
        
        # Sort by created_at, newest first
        all_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"sessions": all_sessions}


def update_translation_info(translation_id: str, scene_info: Dict[str, str], output_dir: str) -> None:
    """Update translation session information."""
    os.makedirs(TRANSLATION_INFO_DIR, exist_ok=True)
    info_path = os.path.join(TRANSLATION_INFO_DIR, f"{translation_id}_{TRANSLATION_INFO_FILE}")
    
    # Load existing info or create new
    if os.path.exists(info_path):
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                info = json.load(f)
        except:
            info = {
                "translation_id": translation_id,
                "scenes_translated": [],
                "created_at": datetime.now().isoformat()
            }
    else:
        info = {
            "translation_id": translation_id,
            "scenes_translated": [],
            "created_at": datetime.now().isoformat()
        }
    
    # Update scenes
    scenes = info.get("scenes_translated", [])
    scene_already_exists = False
    
    for i, s in enumerate(scenes):
        if s.get("act") == scene_info["act"] and s.get("scene") == scene_info["scene"]:
            # Update existing scene
            scenes[i] = scene_info
            scene_already_exists = True
            break
    
    if not scene_already_exists:
        scenes.append(scene_info)
    
    info["scenes_translated"] = scenes
    info["last_updated"] = datetime.now().isoformat()
    info["output_dir"] = output_dir
    
    # Save updated info
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2)
    
    # Also save a copy in the output directory for easy reference
    output_info_path = os.path.join(output_dir, TRANSLATION_INFO_FILE)
    with open(output_info_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2)


def get_all_translations() -> List[Dict[str, Any]]:
    """Get a list of all translation sessions with their info."""
    translation_info = get_translation_info()
    return translation_info.get("sessions", [])


def list_translations() -> None:
    """Print a list of all translation sessions."""
    translations = get_all_translations()
    
    if not translations:
        print("No translation sessions found.")
        return
    
    print("\n=== Available Translation Sessions ===\n")
    for i, t in enumerate(translations, 1):
        translation_id = t.get("translation_id", "unknown")
        created_at = t.get("created_at", "unknown")
        scene_count = len(t.get("scenes_translated", []))
        output_dir = t.get("output_dir", "unknown")
        
        print(f"{i}. ID: {translation_id}")
        print(f"   Created: {created_at}")
        print(f"   Scenes Translated: {scene_count}")
        print(f"   Output Directory: {output_dir}")
        print()


def is_scene_translated(translation_id: str, act: str, scene: str) -> bool:
    """Check if a scene has already been translated in this session."""
    info = get_translation_info(translation_id)
    
    for s in info.get("scenes_translated", []):
        if s.get("act") == act and s.get("scene") == scene:
            return True
    
    return False


def gather_scene_files(input_dir: str, file_pattern: str) -> List[Tuple[str, str, str, str]]:
    """
    Gather and sort scene files from a directory.
    Returns a list of tuples: (filepath, clean_filename, act, scene)
    """
    scene_files = []
    
    # Get all files matching pattern
    file_paths = glob.glob(os.path.join(input_dir, file_pattern))
    
    for filepath in file_paths:
        filename = os.path.basename(filepath)
        act, scene = extract_act_scene_from_filename(filepath)
        
        if act == "unknown" or scene == "unknown":
            # Skip files we can't parse
            continue
        
        scene_files.append((filepath, filename, act, scene))
    
    # Sort by act and scene
    def sort_key(item):
        act, scene = item[2], item[3]
        
        # Try to convert act to number (handle roman numerals)
        try:
            if re.match(r'^[IVXLCDM]+$', act.upper()):
                act_num = roman_to_int(act.upper())
            else:
                act_num = float(act)
        except:
            act_num = act  # Keep as string if conversion fails
            
        # Try to convert scene to number
        try:
            if re.match(r'^[IVXLCDM]+$', scene.upper()):
                scene_num = roman_to_int(scene.upper())
            else:
                scene_num = float(scene)
        except:
            scene_num = scene  # Keep as string if conversion fails
            
        return (act_num, scene_num)
    
    return sorted(scene_files, key=sort_key)


def roman_to_int(roman: str) -> int:
    """Convert Roman numeral to integer."""
    values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50, 
        'C': 100, 'D': 500, 'M': 1000
    }
    total = 0
    prev = 0
    
    for char in reversed(roman):
        if char not in values:
            return 0  # Invalid Roman numeral
        current = values[char]
        if current >= prev:
            total += current
        else:
            total -= current
        prev = current
        
    return total


def translate_scene_from_file(
    filepath: str, 
    output_dir: str = "outputs/translated_scenes",
    log_level: str = "INFO",
    save_logs: bool = True,
    checkpoint_interval: int = 5,
    translation_id: Optional[str] = None,
    force_retranslate: bool = False
) -> str:  # Return the translation_id
    """
    Translate a scene from a markdown file.
    Returns the translation_id used, so it can be reused for subsequent scenes.
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
    
    # Create a translation ID if not provided
    if not translation_id:
        translation_id = generate_friendly_translation_id()
        logger.info(f"Generated new translation ID: {translation_id}")
    else:
        logger.info(f"Using existing translation ID: {translation_id}")
    
    # Check if this scene has already been translated in this session
    if not force_retranslate and is_scene_translated(translation_id, act, scene):
        logger.info(f"Scene Act {act}, Scene {scene} has already been translated in this session.")
        logger.info(f"Skipping translation. Use --force to retranslate.")
        return translation_id
    
    # Parse the file to get dialogue lines
    lines = parse_markdown_file(filepath)
    logger.info(f"Extracted {len(lines)} dialogue lines for translation")
    
    if not lines:
        logger.error("No dialogue lines found in file. Please check the format.")
        return translation_id or ""  # Return the original translation_id if no lines found
    
    # Initialize translation manager
    manager = TranslationManager()
    
    # Start translation session with provided translation_id
    manager.start_translation_session(translation_id)
    logger.info(f"Using translation_id: {manager.translation_id}")
    
    # Translate the lines
    translated_lines = manager.translate_group(lines)
    logger.info(f"Translated {len(translated_lines)} lines")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
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
    
    # Update translation info
    scene_info = {
        "act": act,
        "scene": scene,
        "filename": os.path.basename(filepath),
        "translated_at": datetime.now().isoformat(),
        "line_count": len(translated_lines)
    }
    update_translation_info(translation_id, scene_info, output_dir)
    
    # Return the translation_id so it can be used for subsequent scenes
    return translation_id


def translate_play(
    input_dir: str,
    output_dir: str = "outputs/translated_play",
    file_pattern: str = "*.md",
    log_level: str = "INFO",
    save_logs: bool = True,
    checkpoint_interval: int = 5,
    translation_id: Optional[str] = None,
    force_retranslate: bool = False,
    scene_filter: Optional[List[str]] = None
) -> str:
    """
    Translate multiple scenes from files in a directory, maintaining the same translation_id.
    
    Args:
        input_dir: Directory containing scene files
        output_dir: Directory to save translated scenes
        file_pattern: Glob pattern to match scene files
        log_level: Logging level
        save_logs: Whether to save logs to file
        checkpoint_interval: Save checkpoint every N lines
        translation_id: Optional existing translation_id to continue from
        force_retranslate: Force retranslation of already translated scenes
        scene_filter: List of scene identifiers to translate (format: 'act_scene', e.g. '1_2')
        
    Returns:
        The translation_id used
    """
    # Setup logging
    logger = setup_logging(log_level, save_logs)
    logger.info(f"Starting play translation from directory: {input_dir}")
    
    # Create a translation ID if not provided
    if not translation_id:
        translation_id = generate_friendly_translation_id()
        logger.info(f"Generated new translation ID: {translation_id}")
    else:
        logger.info(f"Using existing translation ID: {translation_id}")
    
    # Get and sort scene files
    scene_files = gather_scene_files(input_dir, file_pattern)
    
    if not scene_files:
        logger.error(f"No valid scene files found matching pattern '{file_pattern}' in directory '{input_dir}'")
        return translation_id
    
    logger.info(f"Found {len(scene_files)} scene files to translate")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Filter scenes if requested
    if scene_filter:
        filtered_scene_files = []
        for filepath, filename, act, scene in scene_files:
            scene_id = f"{act}_{scene}"
            if scene_id in scene_filter:
                filtered_scene_files.append((filepath, filename, act, scene))
        
        if not filtered_scene_files:
            logger.error(f"No scenes match the requested filter: {scene_filter}")
            return translation_id
        
        logger.info(f"Filtered to {len(filtered_scene_files)} scenes: {scene_filter}")
        scene_files = filtered_scene_files
    
    # Process each scene file
    for i, (filepath, filename, act, scene) in enumerate(scene_files):
        scene_id = f"{act}_{scene}"
        logger.info(f"Processing scene {i+1}/{len(scene_files)}: Act {act}, Scene {scene}")
        
        # Check if already translated (unless force_retranslate is True)
        if not force_retranslate and is_scene_translated(translation_id, act, scene):
            logger.info(f"Scene Act {act}, Scene {scene} has already been translated in this session.")
            logger.info(f"Skipping translation. Use --force to retranslate.")
            continue
        
        try:
            # Translate the scene
            translation_id = translate_scene_from_file(
                filepath=filepath,
                output_dir=output_dir,
                log_level=log_level,
                save_logs=save_logs,
                checkpoint_interval=checkpoint_interval,
                translation_id=translation_id,
                force_retranslate=force_retranslate
            )
            
            logger.info(f"Completed scene {i+1}/{len(scene_files)}")
            
        except Exception as e:
            logger.error(f"Error processing scene {scene_id}: {e}")
            logger.info("Continuing with next scene...")
    
    logger.info(f"Play translation complete. All outputs saved to {output_dir}")
    logger.info(f"Final translation_id: {translation_id}")
    return translation_id


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Shakespeare Translation System")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Sample lines translator
    sample_parser = subparsers.add_parser("sample", help="Translate sample lines")
    
    # List translations command
    list_parser = subparsers.add_parser("list", help="List all translation sessions")
    
    # Single file translator
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
    file_parser.add_argument("--translation-id", type=str, default=None,
                            help="Translation ID to use (for continuing a translation)")
    file_parser.add_argument("--force", action="store_true",
                            help="Force retranslation even if already translated")
    
    # Multi-file translator for whole play
    play_parser = subparsers.add_parser("play", help="Translate all scenes in a directory")
    play_parser.add_argument("input_dir", type=str, help="Directory containing scene files")
    play_parser.add_argument("--output-dir", type=str, default="outputs/translated_play",
                           help="Directory to save output (default: outputs/translated_play)")
    play_parser.add_argument("--file-pattern", type=str, default="*.md",
                           help="File pattern to match scene files (default: *.md)")
    play_parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                           default="INFO", help="Logging level (default: INFO)")
    play_parser.add_argument("--no-save-logs", action="store_true", 
                           help="Don't save logs to file")
    play_parser.add_argument("--checkpoint", type=int, default=5,
                           help="Save checkpoint every N lines (default: 5)")
    play_parser.add_argument("--translation-id", type=str, default=None,
                           help="Translation ID to use (for continuing a translation)")
    play_parser.add_argument("--force", action="store_true",
                           help="Force retranslation of already translated scenes")
    play_parser.add_argument("--scenes", type=str, nargs="+",
                           help="Specific scenes to translate (format: '1_2' for Act 1, Scene 2)")
    
    args = parser.parse_args()
    
    if args.command == "file":
        translate_scene_from_file(
            filepath=args.filepath,
            output_dir=args.output_dir,
            log_level=args.log_level,
            save_logs=not args.no_save_logs,
            checkpoint_interval=args.checkpoint,
            translation_id=args.translation_id,
            force_retranslate=args.force
        )
    elif args.command == "play":
        translate_play(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            file_pattern=args.file_pattern,
            log_level=args.log_level,
            save_logs=not args.no_save_logs,
            checkpoint_interval=args.checkpoint,
            translation_id=args.translation_id,
            force_retranslate=args.force,
            scene_filter=args.scenes
        )
    elif args.command == "list":
        list_translations()
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