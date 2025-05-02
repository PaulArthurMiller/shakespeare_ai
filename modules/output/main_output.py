# modules/output/main_output.py

import os
import argparse
import json
from pathlib import Path
from modules.output.final_output_generator import FinalOutputGenerator
from modules.utils.logger import CustomLogger

def debug_translations(translations_dir, act, scene, logger):
    """
    Debug function to examine translation files and their content.
    """
    logger.info(f"=== DEBUGGING TRANSLATIONS ===")
    logger.info(f"Looking for translations in: {translations_dir}")
    
    # Check if directory exists
    if not os.path.exists(translations_dir):
        logger.error(f"⚠️ Translations directory does not exist: {translations_dir}")
        return False
    
    # List all JSON files in the directory
    json_files = list(Path(translations_dir).glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files in directory:")
    for file in json_files:
        logger.info(f"  - {file.name}")
    
    # If act and scene are specified, check for specific file
    if act is not None and scene is not None:
        expected_filename = f"act_{act.lower()}_scene_{scene.lower()}.json"
        expected_path = os.path.join(translations_dir, expected_filename)
        logger.info(f"Looking for specific file: {expected_filename}")
        
        if not os.path.exists(expected_path):
            logger.error(f"⚠️ Expected translation file not found: {expected_path}")
            return False
        
        # File exists, check its content
        logger.info(f"Found translation file: {expected_path}")
        try:
            with open(expected_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check for translated_lines key
            if "translated_lines" not in data:
                logger.error("⚠️ File does not contain 'translated_lines' key")
                logger.info(f"File keys: {list(data.keys())}")
                return False
                
            translated_lines = data["translated_lines"]
            logger.info(f"File contains {len(translated_lines)} translated lines")
            
            # Check structure of first few translated lines
            for i, line in enumerate(translated_lines[:3]):
                logger.info(f"Line {i+1} keys: {list(line.keys())}")
                if "text" in line:
                    logger.info(f"Line {i+1} text: {line['text'][:50]}...")
                if "references" in line:
                    logger.info(f"Line {i+1} has {len(line['references'])} references")
            
            return True
            
        except json.JSONDecodeError:
            logger.error(f"⚠️ File is not valid JSON: {expected_path}")
            return False
        except Exception as e:
            logger.error(f"⚠️ Error reading file: {e}")
            return False
    else:
        # Full play mode - just check if we have files
        logger.info(f"Full play mode: Will process all translation files")
        return len(json_files) > 0

def main():
    """
    Simple test function for generating a formatted document from translations.
    """
    # Create a logger
    logger = CustomLogger("OutputTest")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate formatted Shakespeare translations")
    parser.add_argument("--act", help="Act identifier (e.g., 'i', '1', 'II'). Omit for full play.")
    parser.add_argument("--scene", help="Scene identifier (e.g., '1', '2'). Omit for full play.")
    parser.add_argument("--play", default="data/modern_play/modern_play_combined2.md", 
                        help="Path to the modern play markdown file")
    parser.add_argument("--translations", default="outputs/translated_scenes",
                        help="Directory containing translation JSON files")
    parser.add_argument("--output", default="outputs/test_output.docx",
                        help="Path for output document")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Debug translations
    debug_result = debug_translations(args.translations, args.act, args.scene, logger)
    if not debug_result:
        print("\n⚠️ WARNING: Translation debugging found issues. Output may be incomplete.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting.")
            return
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Create generator
    generator = FinalOutputGenerator(logger=logger)
    
    try:
        # Generate the document
        result_path = generator.generate_final_document(
            modern_play_path=args.play,
            translations_dir=args.translations,
            output_path=args.output,
            specific_act=args.act,
            specific_scene=args.scene
        )
        
        logger.info(f"✅ Success! Document saved to: {result_path}")
        print(f"\nDocument successfully generated and saved to: {result_path}")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"\nError: {e}")
        print("Make sure you have python-docx installed. Run: pip install python-docx")
        
    except Exception as e:
        logger.error(f"Error generating document: {e}")
        print(f"\nError generating document: {e}")

if __name__ == "__main__":
    main()