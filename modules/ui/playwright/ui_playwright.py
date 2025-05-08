"""
UI Playwright Adapter for Shakespeare AI.

This module provides an interface between the Streamlit UI and the 
underlying playwright functionality, handling user input validation,
error handling, and format conversion for the UI.
"""
import os
import json
import time
from datetime import datetime
import re
import shutil
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
        self._log("Initializing UIPlaywright")
        
        # Paths for story data
        self.base_output_dir = "data/modern_play"
        self.expanded_story_path = os.path.join(self.base_output_dir, "expanded_story.json") 
        self.characters_path = "data/prompts/character_voices.json"
        self.scenes_dir = os.path.join(self.base_output_dir, "generated_scenes")
        
        # Flag to track if playwright modules are available
        if not PLAYWRIGHT_AVAILABLE:
            self._log("Warning: Playwright modules not available. Limited functionality.")
    
    def _log(self, message: str, level: str = "info") -> None:
        """
        Log a message using the appropriate logger.
        
        Args:
            message: Message to log
            level: Log level (info, error, warning, debug, critical)
        """
        if self.logger:
            self.logger._log(message, level)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        ensure_directory(self.base_output_dir)
        ensure_directory(self.scenes_dir)
        ensure_directory("data/prompts")
        
    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the playwright configuration with all parameters from the UI.
        
        Args:
            config: Dictionary with configuration settings
                - model_provider: "anthropic" or "openai"
                - model_name: Name of the model to use
                - temperature: Float between 0.0 and 1.0 for creativity
                - random_seed: Optional random seed for reproducibility
                
        Returns:
            True if successful, False otherwise
        """
        try:
            self._log(f"Updating playwright configuration: {config}")
            
            # Load existing config to preserve any values not specified
            existing_config = load_playwright_config()
            
            # Update config with new values
            updated_config = existing_config.copy()
            for key, value in config.items():
                if value is not None:  # Only update if value is provided
                    updated_config[key] = value
            
            # Save the updated config
            result = save_playwright_config(updated_config)
            
            if result:
                self._log("Configuration updated successfully")
            else:
                self._log("Failed to update configuration", "error")
                
            return result
        except Exception as e:
            self._log(f"Error updating playwright configuration: {e}", "error")
            return False
        
    def create_play_project(self, title: str, thematic_guidelines: str, 
                        character_voices: Dict[str, str]) -> str:
        """
        Create a new play project with persistent metadata.
        
        Args:
            title: Title of the play
            thematic_guidelines: Overall thematic guidance for the play
            character_voices: Dictionary mapping character names to voice descriptions
            
        Returns:
            project_id: Unique identifier for the project
        """
        # Generate unique project ID
        project_id = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_folder = os.path.join("data/play_projects", project_id)
        ensure_directory(project_folder)
        ensure_directory(os.path.join(project_folder, "scenes"))
        
        # Create initial project data
        project_data = {
            "title": title,
            "thematic_guidelines": thematic_guidelines,
            "character_voices": character_voices,
            "scenes": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Save project data
        self._save_project_data(project_id, project_data)
        
        self._log(f"Created new play project: {title} (ID: {project_id})")
        return project_id

    def add_scene_to_project(self, project_id: str, act: str, scene: str, 
                            overview: str, setting: str, 
                            characters: List[str],
                            additional_instructions: str = "") -> bool:
        """
        Add a scene definition to a project without generating it.
        
        Args:
            project_id: Project identifier
            act: Act identifier (e.g., "I", "II")
            scene: Scene identifier (e.g., "1", "2")
            overview: Scene summary/description
            setting: Scene setting description
            characters: List of character names present in scene
            additional_instructions: Optional additional notes
            
        Returns:
            Success flag
        """
        # Get project data
        project_data = self.get_project_data(project_id)
        if not project_data:
            self._log(f"Project not found: {project_id}", "error")
            return False
        
        # Create scene summary
        scene_data = {
            "act": act,
            "scene": scene,
            "overview": overview,
            "setting": setting,
            "characters": characters,
            "additional_instructions": additional_instructions
        }
        
        # Add or update scene in project
        scenes = project_data.get("scenes", [])
        
        # Check if scene already exists
        for i, s in enumerate(scenes):
            if s.get("act") == act and s.get("scene") == scene:
                # Update existing scene
                scenes[i] = scene_data
                break
        else:
            # Add new scene
            scenes.append(scene_data)
        
        # Update scenes list
        project_data["scenes"] = scenes
        
        # Save updated project data
        success = self._save_project_data(project_id, project_data)
        
        if success:
            self._log(f"Added scene {act}.{scene} to project {project_id}")
        
        return success

    def generate_project_scene(self, project_id: str, act: str, scene: str,
                            length_option: str = "medium") -> Tuple[bool, str, str]:
        """
        Generate a specific scene from a project.
        
        Args:
            project_id: Project identifier
            act: Act identifier
            scene: Scene identifier
            length_option: Scene length option ("short", "medium", "long")
            
        Returns:
            Tuple of (success, scene_content, scene_path)
        """
        # Get project data
        project_data = self.get_project_data(project_id)
        if not project_data:
            return False, f"Project not found: {project_id}", ""
        
        # Find the scene data
        scene_data = None
        for s in project_data.get("scenes", []):
            if s.get("act") == act and s.get("scene") == scene:
                scene_data = s
                break
        
        if not scene_data:
            return False, f"Scene {act}.{scene} not found in project", ""
        
        # Create a session folder for this generation
        project_folder = os.path.join("data/play_projects", project_id)
        session_folder = os.path.join(project_folder, "generation_sessions", 
                                    f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        ensure_directory(session_folder)
        
        # Create scene summaries for StoryExpander
        scene_summary = {
            "act": act,
            "scene": scene,
            "overview": scene_data.get("overview", ""),
            "setting": scene_data.get("setting", ""),
            "characters": scene_data.get("characters", []),
            "additional_instructions": scene_data.get("additional_instructions", "")
        }
        
        scene_summaries = {"scenes": [scene_summary]}
        
        # Save necessary files for StoryExpander
        if not self.save_scene_summaries(scene_summaries, session_folder):
            return False, "Failed to save scene summaries", ""
            
        if not self.save_character_voices(project_data.get("character_voices", {}), session_folder):
            return False, "Failed to save character voices", ""
        
        # Create the required symlinks
        self._create_symlinks(session_folder)
        
        # Set thematic guidelines
        self._set_thematic_guidelines(project_data.get("thematic_guidelines", ""))
        
        # Expand the story
        expand_success, expand_result = self.expand_story()
        if not expand_success:
            return False, f"Failed to expand story: {expand_result}", ""
        
        # Generate the scene with SceneWriter
        generate_success, output_dir = self.generate_scenes(length_option=length_option)
        if not generate_success:
            return False, f"Failed to generate scene: {output_dir}", ""
        
        # Get the generated scene file paths
        scene_md_filename = f"act_{act.lower()}_scene_{scene.lower()}.md"
        scene_json_filename = f"act_{act.lower()}_scene_{scene.lower()}.json"
        scene_md_path = os.path.join(output_dir, scene_md_filename)
        scene_json_path = os.path.join(output_dir, scene_json_filename)
        
        if not os.path.exists(scene_md_path):
            return False, f"Generated scene file not found: {scene_md_path}", ""
        
        # Copy the generated files to the project folder
        project_scenes_dir = os.path.join(project_folder, "scenes")
        ensure_directory(project_scenes_dir)
        
        try:
            # Copy MD file
            project_md_path = os.path.join(project_scenes_dir, scene_md_filename)
            shutil.copy2(scene_md_path, project_md_path)
            
            # Try to copy JSON file if it exists
            if os.path.exists(scene_json_path):
                project_json_path = os.path.join(project_scenes_dir, scene_json_filename)
                shutil.copy2(scene_json_path, project_json_path)
        except Exception as e:
            return False, f"Error copying generated files: {str(e)}", ""
        
        # Read the generated scene
        scene_content = load_text_from_file(scene_md_path)
        if not scene_content:
            return False, f"Failed to read generated scene file: {scene_md_path}", ""
        
        return True, scene_content, project_md_path

    def _save_project_data(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """
        Save project data to the project file.
        
        Args:
            project_id: Project identifier
            project_data: Project data dictionary
            
        Returns:
            Success flag
        """
        project_folder = os.path.join("data/play_projects", project_id)
        project_file = os.path.join(project_folder, "project.json")
        
        # Update the timestamp
        project_data["updated_at"] = datetime.now().isoformat()
        
        return save_json_to_file(project_data, project_file)

    def _set_thematic_guidelines(self, guidelines: str) -> bool:
        """
        Write thematic guidelines to a file for StoryExpander.
        
        Args:
            guidelines: Thematic guidelines text
            
        Returns:
            Success flag
        """
        try:
            # Ensure directory exists
            guidelines_dir = "data/prompts"
            ensure_directory(guidelines_dir)
            
            # Write guidelines to file
            guidelines_path = os.path.join(guidelines_dir, "thematic_guidelines.txt")
            with open(guidelines_path, 'w', encoding='utf-8') as f:
                f.write(guidelines)
            
            return True
        except Exception as e:
            self._log(f"Error setting thematic guidelines: {e}", "error")
            return False
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        Get a list of all available projects.
        
        Returns:
            List of project metadata dictionaries
        """
        projects = []
        projects_dir = "data/play_projects"
        
        if not os.path.exists(projects_dir):
            return []
        
        for item in os.listdir(projects_dir):
            project_folder = os.path.join(projects_dir, item)
            if os.path.isdir(project_folder):
                project_file = os.path.join(project_folder, "project.json")
                if os.path.exists(project_file):
                    try:
                        project_data = load_json_from_file(project_file)
                        if project_data:
                            # Create a summary
                            projects.append({
                                "id": item,
                                "title": project_data.get("title", "Untitled"),
                                "scenes": len(project_data.get("scenes", [])),
                                "characters": len(project_data.get("character_voices", {})),
                                "created_at": project_data.get("created_at", ""),
                                "updated_at": project_data.get("updated_at", "")
                            })
                    except Exception as e:
                        self._log(f"Error loading project {item}: {e}", "error")
        
        # Sort by updated_at, newest first
        projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return projects
    
    def get_project_data(self, project_id: str) -> Dict[str, Any]:
        """
        Get project data for a specific project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Project data dictionary or empty dict if not found
        """
        project_file = os.path.join("data/play_projects", project_id, "project.json")
        data = load_json_from_file(project_file)
        return data if data else {}

    def generate_full_project(self, project_id: str, length_option: str = "medium") -> Tuple[bool, str]:
        """
        Generate all scenes for a project and combine them into a full play.
        
        Args:
            project_id: Project identifier
            length_option: Scene length option
            
        Returns:
            Tuple of (success, output_path or error_message)
        """
        # Get project data
        project_data = self.get_project_data(project_id)
        if not project_data:
            return False, f"Project not found: {project_id}"
        
        # Project folder
        project_folder = os.path.join("data/play_projects", project_id)
        project_scenes_dir = os.path.join(project_folder, "scenes")
        ensure_directory(project_scenes_dir)
        
        # Generate each scene
        scenes = project_data.get("scenes", [])
        if not scenes:
            return False, "No scenes defined in project"
        
        for scene_data in scenes:
            act = scene_data.get("act")
            scene = scene_data.get("scene")
            
            self._log(f"Generating scene {act}.{scene} for project {project_id}")
            
            success, result, _ = self.generate_project_scene(
                project_id=project_id,
                act=act,
                scene=scene,
                length_option=length_option
            )
            
            if not success:
                self._log(f"Failed to generate scene {act}.{scene}: {result}", "warning")
                # Continue with next scene despite failure
        
        # Combine all scenes into a full play
        combined_path = os.path.join(project_folder, f"{project_data.get('title', 'play')}_full.md")
        
        # Get all generated scene files
        scene_files = []
        for filename in os.listdir(project_scenes_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(project_scenes_dir, filename)
                act, scene = extract_act_scene_from_filename(filename)
                scene_files.append((filepath, filename, act, scene))
        
        # Sort scene files
        scene_files.sort(key=lambda x: (self._act_to_int(x[2]), self._scene_to_int(x[3])))
        
        # Combine scenes
        combined_text = f"# {project_data.get('title', 'Play')}\n\n"
        
        for filepath, _, _, _ in scene_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    scene_text = f.read().strip()
                combined_text += scene_text + "\n\n"
            except Exception as e:
                self._log(f"Error reading scene file {filepath}: {e}", "error")
        
        # Save combined play
        try:
            with open(combined_path, 'w', encoding='utf-8') as f:
                f.write(combined_text)
            
            self._log(f"Combined play saved to {combined_path}")
            return True, combined_path
        except Exception as e:
            error_msg = f"Error saving combined play: {e}"
            self._log(error_msg, "error")
            return False, error_msg

    def save_scene_to_file(self, project_id: str, act: str, scene: str, 
                        output_format: str = "docx") -> Tuple[bool, str]:
        """
        Save a specific scene to a file in the desired format.
        
        Args:
            project_id: Project identifier
            act: Act identifier
            scene: Scene identifier
            output_format: Output format ("docx" or "md")
            
        Returns:
            Tuple of (success, output_path)
        """
        project_folder = os.path.join("data/play_projects", project_id)
        scene_md_path = os.path.join(project_folder, "scenes", 
                                f"act_{act.lower()}_scene_{scene.lower()}.md")
        scene_json_path = os.path.join(project_folder, "scenes", 
                                    f"act_{act.lower()}_scene_{scene.lower()}.json")
        
        # Check if scene exists
        if not os.path.exists(scene_md_path):
            return False, f"Scene file not found: {scene_md_path}"
        
        # Create output directory
        output_dir = os.path.join(project_folder, "exports")
        ensure_directory(output_dir)
        
        if output_format.lower() == "md":
            # For markdown, just copy the file
            output_path = os.path.join(output_dir, f"act_{act.lower()}_scene_{scene.lower()}.md")
            try:
                shutil.copy2(scene_md_path, output_path)
                return True, output_path
            except Exception as e:
                return False, f"Error copying file: {str(e)}"
        
        elif output_format.lower() == "docx":
            # For docx, use the save_modern_play module
            try:
                from modules.output.save_modern_play import SceneExporter
                exporter = SceneExporter()
                
                # If we have the JSON, use it (it has more data)
                if os.path.exists(scene_json_path):
                    output_path = exporter.export_scene_from_json(
                        scene_json_path, 
                        os.path.join(output_dir, f"act_{act.lower()}_scene_{scene.lower()}.docx")
                    )
                else:
                    # Fallback to markdown
                    output_path = exporter.export_scene_from_markdown(
                        scene_md_path,
                        os.path.join(output_dir, f"act_{act.lower()}_scene_{scene.lower()}.docx")
                    )
                
                return True, output_path
            except Exception as e:
                return False, f"Error creating DOCX: {str(e)}"
        
        else:
            return False, f"Unsupported output format: {output_format}"

    def save_full_play_to_file(self, project_id: str, 
                            output_format: str = "docx") -> Tuple[bool, str]:
        """
        Save all scenes as a full play file in the desired format.
        
        Args:
            project_id: Project identifier
            output_format: Output format ("docx" or "md")
            
        Returns:
            Tuple of (success, output_path)
        """
        # Get project data
        project_data = self.get_project_data(project_id)
        if not project_data:
            return False, f"Project not found: {project_id}"
        
        project_folder = os.path.join("data/play_projects", project_id)
        project_scenes_dir = os.path.join(project_folder, "scenes")
        
        # Create output directory
        output_dir = os.path.join(project_folder, "exports")
        ensure_directory(output_dir)
        
        # Get title for filename
        title = project_data.get("title", "play").replace(" ", "_").lower()
        
        if output_format.lower() == "md":
            # For markdown, combine scenes
            output_path = os.path.join(output_dir, f"{title}_full.md")
            
            # Get all generated scene files
            scene_files = []
            for filename in os.listdir(project_scenes_dir):
                if filename.endswith(".md"):
                    filepath = os.path.join(project_scenes_dir, filename)
                    act, scene = extract_act_scene_from_filename(filename)
                    scene_files.append((filepath, filename, act, scene))
            
            # Sort scene files
            scene_files.sort(key=lambda x: (self._act_to_int(x[2]), self._scene_to_int(x[3])))
            
            # Combine scenes
            combined_text = f"# {project_data.get('title', 'Play')}\n\n"
            
            for filepath, _, _, _ in scene_files:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        scene_text = f.read().strip()
                    combined_text += scene_text + "\n\n"
                except Exception as e:
                    self._log(f"Error reading scene file {filepath}: {e}", "error")
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(combined_text)
                return True, output_path
            except Exception as e:
                return False, f"Error saving combined play: {str(e)}"
        
        elif output_format.lower() == "docx":
            # For docx, use the save_modern_play module
            try:
                from modules.output.save_modern_play import PlayExporter
                exporter = PlayExporter()
                
                # Get all JSON files for scenes
                scene_files = []
                for filename in os.listdir(project_scenes_dir):
                    if filename.endswith(".json"):
                        filepath = os.path.join(project_scenes_dir, filename)
                        act, scene = extract_act_scene_from_filename(filename)
                        scene_files.append((filepath, act, scene))
                
                # Sort scene files
                scene_files.sort(key=lambda x: (self._act_to_int(x[1]), self._scene_to_int(x[2])))
                
                # Export to DOCX
                output_path = os.path.join(output_dir, f"{title}_full.docx")
                exporter.export_play_from_scenes(
                    [path for path, _, _ in scene_files],
                    output_path,
                    title=project_data.get("title", "Play")
                )
                
                return True, output_path
            except Exception as e:
                return False, f"Error creating DOCX: {str(e)}"
        
        else:
            return False, f"Unsupported output format: {output_format}"
        
    def create_session_folder(self) -> str:
        """
        Create a timestamped folder for the current generation session.
        
        Returns:
            Path to the session folder
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_folder = os.path.join("data/generation_sessions", f"session_{timestamp}")
        os.makedirs(session_folder, exist_ok=True)
        self._log(f"Created session folder: {session_folder}")
        return session_folder
    
    def save_act_overviews(self, act_overviews: Dict[str, str], session_folder: str) -> bool:
        """
        Save act overviews to JSON.
        
        Args:
            act_overviews: Dictionary mapping act numbers to descriptions
            session_folder: Path to the session folder
            
        Returns:
            True if successful, False otherwise
        """
        filepath = os.path.join(session_folder, "act_overviews.json")
        return save_json_to_file(act_overviews, filepath)

    def save_character_voices(self, character_voices: Dict[str, str], session_folder: str) -> bool:
        """
        Save character voices to JSON.
        
        Args:
            character_voices: Dictionary mapping character names to descriptions
            session_folder: Path to the session folder
            
        Returns:
            True if successful, False otherwise
        """
        filepath = os.path.join(session_folder, "character_voices.json")
        return save_json_to_file(character_voices, filepath)

    def save_scene_summaries(self, scene_summaries: Dict[str, List[Dict[str, Any]]], session_folder: str) -> bool:
        """
        Save scene summaries to JSON.
        
        Args:
            scene_summaries: Dictionary with scene information
            session_folder: Path to the session folder
            
        Returns:
            True if successful, False otherwise
        """
        filepath = os.path.join(session_folder, "scene_summaries.json")
        return save_json_to_file(scene_summaries, filepath)
    
    def transform_ui_inputs_to_scene_summaries(
        self,
        act_scenes: Dict[str, Dict[str, Dict[str, Any]]],
        characters: Dict[str, str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Transform UI inputs into the scene summaries format expected by StoryExpander.
        
        Args:
            act_scenes: Dictionary structure containing acts and scenes with details
                Format: {act_number: {scene_number: {details}}}
            characters: Dictionary of character names and descriptions
        
        Returns:
            Dictionary structured for StoryExpander
        """
        scenes = []
        
        # Process each act and scene
        for act_num, act_data in act_scenes.items():
            for scene_num, scene_data in act_data.items():
                # Extract scene details
                scene_summary = {
                    "act": act_num,
                    "scene": scene_num,
                    "overview": scene_data.get("description", ""),
                    "setting": scene_data.get("setting", "Based on scene description"),
                    "characters": scene_data.get("characters", list(characters.keys())),
                    "additional_instructions": scene_data.get("additional_instructions", "")
                }
                scenes.append(scene_summary)
        
        # Sort scenes by act and scene number
        scenes.sort(key=lambda x: (self._act_to_int(x["act"]), self._scene_to_int(x["scene"])))
        
        return {"scenes": scenes}
    
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
        character_voices: Dict[str, str],
        session_folder: Optional[str] = None
    ) -> bool:
        """
        Create the story framework from user input.
        
        Args:
            story_data: Dictionary with story structure
            character_voices: Dictionary with character voices
            session_folder: Optional path to session folder (creates a new one if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_directories()
        
        # Create a session folder if not provided
        if session_folder is None:
            session_folder = self.create_session_folder()
        
        # Save character voices
        if not self.save_character_voices(character_voices, session_folder):
            self._log("Error saving character voices", "error")
            return False
        
        # Save story data
        scene_summaries_path = os.path.join(session_folder, "scene_summaries.json")
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
    
    def generate_single_scene(
        self, 
        act_number: str, 
        scene_number: str,
        scene_description: str,
        scene_setting: str,
        scene_characters: List[str],
        additional_instructions: str,
        character_voices: Dict[str, str],
        act_overviews: Dict[str, str],
        length_option: str = "medium"
    ) -> Tuple[bool, str]:
        """
        Generate a single scene based on user input.
        
        Args:
            act_number: Act identifier (e.g., "I", "1")
            scene_number: Scene identifier (e.g., "1", "2")
            scene_description: Description of the scene
            scene_setting: Description of the scene setting
            scene_characters: List of character names in the scene
            additional_instructions: Additional instructions for the scene
            character_voices: Dictionary mapping character names to descriptions
            act_overviews: Dictionary mapping act numbers to descriptions
            length_option: Scene length option ("short", "medium", or "long")
            
        Returns:
            Tuple of (success, result_text or error_message)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, "Playwright modules not available"
        
        try:
            self._log(f"Generating single scene: Act {act_number}, Scene {scene_number}")
            
            # Create a session folder
            session_folder = self.create_session_folder()
            
            # Create a minimal scene summaries structure
            scene_summary = {
                "act": act_number,
                "scene": int(scene_number) if scene_number.isdigit() else scene_number,
                "overview": scene_description,
                "setting": scene_setting,
                "characters": scene_characters,
                "additional_instructions": additional_instructions
            }
            
            scene_summaries = {"scenes": [scene_summary]}
            
            # Save all three JSON structures
            if not self.save_scene_summaries(scene_summaries, session_folder):
                return False, "Failed to save scene summaries"
                
            if not self.save_character_voices(character_voices, session_folder):
                return False, "Failed to save character voices"
                
            if not self.save_act_overviews(act_overviews, session_folder):
                return False, "Failed to save act overviews"
            
            # Create symlinks for the StoryExpander to find the files
            self._create_symlinks(session_folder)
            
            # Expand the story
            expand_success, expand_result = self.expand_story()
            if not expand_success:
                return False, f"Failed to expand story: {expand_result}"
            
            # Generate the scene
            generate_success, output_dir = self.generate_scenes(length_option=length_option)
            if not generate_success:
                return False, f"Failed to generate scene: {output_dir}"
            
            # Find and read the generated scene file
            scene_filename = f"act_{act_number.lower()}_scene_{scene_number.lower()}.md"
            scene_path = os.path.join(output_dir, scene_filename)
            
            if not os.path.exists(scene_path):
                return False, f"Generated scene file not found: {scene_path}"
            
            # Read the generated scene
            scene_content = load_text_from_file(scene_path)
            if not scene_content:
                return False, f"Failed to read generated scene file: {scene_path}"
            
            return True, scene_content
        except Exception as e:
            error_msg = f"Error generating single scene: {str(e)}"
            self._log(error_msg, "error")
            return False, error_msg
    
    def generate_scenes(self, length_option: str = "medium") -> Tuple[bool, str]:
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
            
            # Create SceneWriter with the length option
            writer = SceneWriter(
                config_path="modules/playwright/config.py",
                expanded_story_path=self.expanded_story_path,
                length_option=length_option
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
        
    def generate_full_play(
        self,
        act_overviews: Dict[str, str],
        character_voices: Dict[str, str],
        scene_details: Dict[str, Dict[str, Dict[str, Any]]],
        length_option: str = "medium"
    ) -> Tuple[bool, str]:
        """
        Generate a full play based on user input.
        
        Args:
            act_overviews: Dictionary mapping act numbers to descriptions
            character_voices: Dictionary mapping character names to descriptions
            scene_details: Nested dictionary of act/scene details
                Format: {act_number: {scene_number: {details}}}
            length_option: Scene length option ("short", "medium", or "long")
            
        Returns:
            Tuple of (success, output_path or error_message)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, "Playwright modules not available"
        
        try:
            self._log("Generating full play based on provided structure")
            
            # Create a session folder
            session_folder = self.create_session_folder()
            
            # Transform scene details to scene summaries
            scene_summaries = self.transform_ui_inputs_to_scene_summaries(scene_details, character_voices)
            
            # Save all three JSON structures
            if not self.save_scene_summaries(scene_summaries, session_folder):
                return False, "Failed to save scene summaries"
                
            if not self.save_character_voices(character_voices, session_folder):
                return False, "Failed to save character voices"
                
            if not self.save_act_overviews(act_overviews, session_folder):
                return False, "Failed to save act overviews"
            
            # Create symlinks for the StoryExpander to find the files
            self._create_symlinks(session_folder)
            
            # Expand the story
            expand_success, expand_result = self.expand_story()
            if not expand_success:
                return False, f"Failed to expand story: {expand_result}"
            
            # Generate all scenes
            generate_success, output_dir = self.generate_scenes(length_option=length_option)
            if not generate_success:
                return False, f"Failed to generate scenes: {output_dir}"
            
            # Combine all scenes into a single play file
            combine_success, combined_path = self.combine_scenes(output_filename="full_play.md")
            if not combine_success:
                return False, f"Failed to combine scenes: {combined_path}"
            
            return True, combined_path
        except Exception as e:
            error_msg = f"Error generating full play: {str(e)}"
            self._log(error_msg, "error")
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
    
    def _create_symlinks(self, session_folder: str) -> None:
        """
        Create symlinks for the StoryExpander to find the files.
        
        Args:
            session_folder: Path to the session folder
        """
        # Define the target paths that StoryExpander expects
        target_scene_summaries = "data/prompts/scene_summaries.json"
        target_character_voices = "data/prompts/character_voices.json"
        
        # Source paths in the session folder
        source_scene_summaries = os.path.join(session_folder, "scene_summaries.json")
        source_character_voices = os.path.join(session_folder, "character_voices.json")
        
        # Ensure the target directories exist
        os.makedirs(os.path.dirname(target_scene_summaries), exist_ok=True)
        
        # Remove existing files if they exist
        if os.path.exists(target_scene_summaries):
            os.remove(target_scene_summaries)
        if os.path.exists(target_character_voices):
            os.remove(target_character_voices)
        
        # Create physical copies (more reliable than symlinks across platforms)
        shutil.copy2(source_scene_summaries, target_scene_summaries)
        shutil.copy2(source_character_voices, target_character_voices)
        
        self._log(f"Created file copies from session folder to target paths")
    
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