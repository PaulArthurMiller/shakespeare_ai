"""
UI Playwright Adapter for Shakespeare AI.

This module provides an interface between the Streamlit UI and the 
underlying playwright functionality, handling user input validation,
error handling, and format conversion for the UI.
"""
import os
import json
import time
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

# Import module-specific helpers
from modules.ui.file_helper import (
    save_text_to_file,
    load_text_from_file,
    load_json_from_file,
    save_json_to_file,
    ensure_directory,
    extract_act_scene_from_filename  # Import the function
)
from modules.ui.config_manager import (
    load_playwright_config,
    save_playwright_config
)

# Import the core playwright functionality if available
try:
    from modules.playwright.story_expander import StoryExpander
    from modules.playwright.scene_writer import SceneWriter
    from modules.playwright.artistic_adjuster import ArtisticAdjuster
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    print("Warning: Playwright modules not available")
    PLAYWRIGHT_AVAILABLE = False


class UIPlaywright:
    """
    Adapter class for interfacing between the UI and the playwright functionality.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the UI playwright.
        
        Args:
            logger: Optional logger object (for Streamlit)
        """
        self.logger = logger  # For Streamlit logging
        
        # Paths for story data
        self.base_output_dir = "data/modern_play"
        self.expanded_story_path = os.path.join(self.base_output_dir, "expanded_story.json") 
        self.characters_path = "data/prompts/character_voices.json"
        self.scenes_dir = os.path.join(self.base_output_dir, "generated_scenes")
        
        # Flag to track if playwright modules are available
        if not PLAYWRIGHT_AVAILABLE:
            self._log("Warning: Playwright modules not available. Limited functionality.")
    
    def _log(self, message: str) -> None:
        """
        Log a message using the appropriate logger.
        
        Args:
            message: Message to log
        """
        if self.logger:
            self.logger.info(message)
        else:
            print(message)
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        ensure_directory(self.base_output_dir)
        ensure_directory(self.scenes_dir)
        ensure_directory("data/prompts")
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the playwright configuration.
        
        Args:
            config: Dictionary with configuration settings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return save_playwright_config(config)
        except Exception as e:
            self._log(f"Error updating playwright configuration: {e}")
            return False
    
    def save_character_voices(self, characters: Dict[str, str]) -> bool:
        """
        Save character voice descriptions.
        
        Args:
            characters: Dictionary mapping character names to voice descriptions
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_directories()
        return save_json_to_file(characters, self.characters_path)
    
    def load_character_voices(self) -> Dict[str, str]:
        """
        Load character voice descriptions.
        
        Returns:
            Dictionary mapping character names to voice descriptions
        """
        data = load_json_from_file(self.characters_path)
        return data if data else {}
    
    def create_story_framework(
        self, 
        story_data: Dict[str, Any],
        character_voices: Dict[str, str]
    ) -> bool:
        """
        Create the story framework from user input.
        
        Args:
            story_data: Dictionary with story structure
            character_voices: Dictionary with character voices
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_directories()
        
        # Save character voices
        if not self.save_character_voices(character_voices):
            self._log("Error saving character voices")
            return False
        
        # Save story data
        scene_summaries_path = os.path.join("data/prompts", "scene_summaries.json")
        return save_json_to_file(story_data, scene_summaries_path)
    
    def expand_story(self) -> Tuple[bool, str]:
        """
        Expand a story structure into detailed scene descriptions.
        
        Returns:
            Tuple of (success, error_message or output_path)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, "Playwright modules not available"
        
        try:
            self._log("Starting story expansion...")
            
            # Load playwright config
            config = load_playwright_config()
            
            # Create StoryExpander
            expander = StoryExpander(
                config_path="modules/playwright/config.py",
                scene_summaries_path="data/prompts/scene_summaries.json",
                character_voices_path=self.characters_path
            )
            
            # Expand the story
            start_time = time.time()
            expander.expand_all_scenes()
            elapsed_time = time.time() - start_time
            
            # Log the result
            self._log(f"Story expansion completed in {elapsed_time:.2f} seconds")
            self._log(f"Expanded story saved to {self.expanded_story_path}")
            
            return True, self.expanded_story_path
        except Exception as e:
            error_msg = f"Error expanding story: {str(e)}"
            self._log(error_msg)
            return False, error_msg
    
    def generate_scenes(self) -> Tuple[bool, str]:
        """
        Generate scenes from the expanded story.
        
        Returns:
            Tuple of (success, error_message or output_directory)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, "Playwright modules not available"
        
        try:
            self._log("Starting scene generation...")
            
            # Ensure the expanded story exists
            if not os.path.exists(self.expanded_story_path):
                return False, f"Expanded story not found at {self.expanded_story_path}"
            
            # Create SceneWriter
            writer = SceneWriter(
                config_path="modules/playwright/config.py",
                expanded_story_path=self.expanded_story_path
            )
            
            # Generate scenes
            start_time = time.time()
            writer.generate_scenes()
            elapsed_time = time.time() - start_time
            
            # Log the result
            self._log(f"Scene generation completed in {elapsed_time:.2f} seconds")
            self._log(f"Scenes saved to {writer.output_dir}")
            
            return True, writer.output_dir
        except Exception as e:
            error_msg = f"Error generating scenes: {str(e)}"
            self._log(error_msg)
            return False, error_msg
    
    def adjust_scene(
        self, 
        scene_path: str, 
        critique: str,
        output_dir: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Adjust a scene based on a critique.
        
        Args:
            scene_path: Path to the scene file
            critique: Critique text
            output_dir: Optional output directory
            
        Returns:
            Tuple of (success, error_message or adjusted_text)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, "Playwright modules not available"
        
        try:
            self._log(f"Adjusting scene: {scene_path}")
            
            # Ensure the scene file exists
            if not os.path.exists(scene_path):
                return False, f"Scene file not found at {scene_path}"
            
            # Determine output directory
            if output_dir is None:
                output_dir = os.path.join(self.base_output_dir, "final_edits")
            
            ensure_directory(output_dir)
            
            # Create ArtisticAdjuster
            adjuster = ArtisticAdjuster()
            
            # Adjust the scene
            start_time = time.time()
            adjusted_text = adjuster.revise_scene(
                scene_path=scene_path,
                critique=critique,
                output_dir=output_dir
            )
            elapsed_time = time.time() - start_time
            
            # Log the result
            self._log(f"Scene adjustment completed in {elapsed_time:.2f} seconds")
            
            return True, adjusted_text
        except Exception as e:
            error_msg = f"Error adjusting scene: {str(e)}"
            self._log(error_msg)
            return False, error_msg
    
    def combine_scenes(self, output_filename: Optional[str] = None) -> Tuple[bool, str]:
        """
        Combine all generated scenes into a single play file.
        
        Args:
            output_filename: Optional output filename
            
        Returns:
            Tuple of (success, error_message or output_path)
        """
        try:
            self._log("Combining scenes into a single play file...")
            
            # Set default output filename if not provided
            if output_filename is None:
                output_filename = "modern_play_combined.md"
            
            # Full output path
            output_path = os.path.join(self.base_output_dir, output_filename)
            
            # Get scene files
            scenes_dir = os.path.join(self.base_output_dir, "generated_scenes_claude2")
            if not os.path.exists(scenes_dir):
                scenes_dir = self.scenes_dir
            
            if not os.path.exists(scenes_dir):
                return False, f"Scenes directory not found at {scenes_dir}"
            
            # Get scene files and sort them
            scene_files = []
            for filename in os.listdir(scenes_dir):
                if filename.endswith(".md"):
                    filepath = os.path.join(scenes_dir, filename)
                    act, scene = extract_act_scene_from_filename(filename)
                    scene_files.append((filepath, filename, act, scene))
            
            # Sort scene files by act and scene
            scene_files.sort(key=lambda x: (self._act_to_int(x[2]), self._scene_to_int(x[3])))
            
            if not scene_files:
                return False, f"No scene files found in {scenes_dir}"
            
            # Combine the files
            combined_text = ""
            for filepath, _, _, _ in scene_files:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        scene_text = f.read().strip()
                    combined_text += scene_text + "\n\n"
                except Exception as e:
                    self._log(f"Error reading scene file {filepath}: {e}")
            
            # Save the combined play
            if not save_text_to_file(combined_text, output_path):
                return False, f"Error saving combined play to {output_path}"
            
            self._log(f"Combined play saved to {output_path}")
            return True, output_path
        except Exception as e:
            error_msg = f"Error combining scenes: {str(e)}"
            self._log(error_msg)
            return False, error_msg
    
    def _act_to_int(self, act: str) -> int:
        """
        Convert act identifier to integer for sorting.
        
        Args:
            act: Act identifier
            
        Returns:
            Integer value
        """
        # Check if it's a Roman numeral
        if re.match(r'^[IVXLCDM]+$', act.upper()):
            try:
                from modules.ui.file_helper import roman_to_int
                return roman_to_int(act.upper())
            except:
                # Fallback if roman_to_int is not available
                romans = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
                result = 0
                for i, c in enumerate(act.upper()):
                    if i > 0 and romans[c] > romans[act.upper()[i-1]]:
                        result += romans[c] - 2 * romans[act.upper()[i-1]]
                    else:
                        result += romans[c]
                return result
        
        # Try to convert to integer directly
        try:
            return int(act)
        except ValueError:
            # If all else fails, return a large number to sort it last
            return 9999
    
    def _scene_to_int(self, scene: str) -> int:
        """
        Convert scene identifier to integer for sorting.
        
        Args:
            scene: Scene identifier
            
        Returns:
            Integer value
        """
        # Same as _act_to_int but for scenes
        return self._act_to_int(scene)
    
    def get_scene_list(self) -> List[Dict[str, Any]]:
        """
        Get a list of all available scenes.
        
        Returns:
            List of dictionaries with scene information
        """
        scenes_dir = os.path.join(self.base_output_dir, "generated_scenes_claude2")
        if not os.path.exists(scenes_dir):
            scenes_dir = self.scenes_dir
        
        if not os.path.exists(scenes_dir):
            return []
        
        scene_list = []
        for filename in os.listdir(scenes_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(scenes_dir, filename)
                act, scene = extract_act_scene_from_filename(filename)
                
                # Get basic file info
                file_size = os.path.getsize(filepath)
                mod_time = os.path.getmtime(filepath)
                
                scene_list.append({
                    "filename": filename,
                    "filepath": filepath,
                    "act": act,
                    "scene": scene,
                    "file_size": file_size,
                    "last_modified": mod_time
                })
        
        # Sort by act and scene
        scene_list.sort(key=lambda x: (self._act_to_int(x["act"]), self._scene_to_int(x["scene"])))
        
        return scene_list
    
    def create_story_from_template(self, template_name: str) -> bool:
        """
        Create a story from a predefined template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            True if successful, False otherwise
        """
        template_path = os.path.join("data/templates", f"{template_name}.json")
        
        if not os.path.exists(template_path):
            self._log(f"Template not found: {template_path}")
            return False
        
        try:
            # Load the template
            template_data = load_json_from_file(template_path)
            if not template_data:
                return False
            
            # Save the template data as scene summaries
            scene_summaries_path = os.path.join("data/prompts", "scene_summaries.json")
            if not save_json_to_file(template_data, scene_summaries_path):
                return False
            
            # If character voices are included in the template, save them too
            if "character_voices" in template_data:
                self.save_character_voices(template_data["character_voices"])
            
            self._log(f"Story created from template: {template_name}")
            return True
        except Exception as e:
            self._log(f"Error creating story from template: {e}")
            return False
    
    def get_scene_content(self, act: str, scene: str) -> Optional[str]:
        """
        Get the content of a specific scene.
        
        Args:
            act: Act identifier
            scene: Scene identifier
            
        Returns:
            Scene content or None if not found
        """
        scenes_dir = os.path.join(self.base_output_dir, "generated_scenes_claude2")
        if not os.path.exists(scenes_dir):
            scenes_dir = self.scenes_dir
        
        # Try different filename formats
        potential_filenames = [
            f"act_{act.lower()}_scene_{scene.lower()}.md",
            f"act_{act}_scene_{scene}.md",
            f"a{act}s{scene}.md"
        ]
        
        for filename in potential_filenames:
            filepath = os.path.join(scenes_dir, filename)
            if os.path.exists(filepath):
                return load_text_from_file(filepath)
        
        return None
    
    def save_scene_content(self, act: str, scene: str, content: str) -> bool:
        """
        Save the content of a specific scene.
        
        Args:
            act: Act identifier
            scene: Scene identifier
            content: Scene content
            
        Returns:
            True if successful, False otherwise
        """
        scenes_dir = os.path.join(self.base_output_dir, "generated_scenes_claude2")
        if not os.path.exists(scenes_dir):
            scenes_dir = self.scenes_dir
        
        ensure_directory(scenes_dir)
        
        # Create filename
        filename = f"act_{act.lower()}_scene_{scene.lower()}.md"
        filepath = os.path.join(scenes_dir, filename)
        
        return save_text_to_file(content, filepath)

# Create a function to get a singleton instance
_INSTANCE = None

def get_ui_playwright(logger=None) -> UIPlaywright:
    """
    Get the UIPlaywright instance (singleton pattern).
    
    Args:
        logger: Optional logger object
        
    Returns:
        UIPlaywright instance
    """
    global _INSTANCE
    
    if _INSTANCE is None:
        _INSTANCE = UIPlaywright(logger=logger)
    
    return _INSTANCE