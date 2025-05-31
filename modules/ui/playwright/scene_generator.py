"""
Scene Generator for Shakespeare AI.

This module handles scene generation from expanded story structures,
as well as adjusting scenes based on critiques.
"""
import os
import re
import shutil
import glob
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

from modules.ui.file_helper import (
    load_text_from_file,
    save_text_to_file,
    ensure_directory,
    extract_act_scene_from_filename
)

# Check if core playwright modules are available
try:
    from modules.ui.playwright.project_manager import ProjectManager
    from modules.ui.playwright.story_manager import StoryManager
    from modules.playwright.story_expander import StoryExpander
    from modules.playwright.scene_writer import SceneWriter
    from modules.playwright.artistic_adjuster import ArtisticAdjuster
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class SceneGenerator:
    """
    Handles scene generation operations for the Shakespeare AI playwright.
    """
    
    def __init__(self, logger, base_output_dir: str = "data/modern_play", config_path: str = "modules/playwright/config.py"):
        """
            Args:
            logger: your logging instance
            base_output_dir: where intermediate files (expanded_story.json, etc.) live
            config_path: path to your model/config file
        """
        self.logger = logger
        self.base_output_dir = base_output_dir
        self.config_path = config_path      
        self.expanded_story_path = os.path.join(self.base_output_dir, "expanded_story.json")
        
        # Ensure directories exist
        ensure_directory(self.base_output_dir)
        ensure_directory(os.path.join(self.base_output_dir, "generated_scenes"))
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log a message using the provided logger if available."""
        if self.logger:
            if hasattr(self.logger, "_log"):
                self.logger._log(message, level)
            elif hasattr(self.logger, level):
                getattr(self.logger, level)(message)
        else:
            print(f"[{level.upper()}] {message}")

    def _act_to_int(self, act: Union[int, str]) -> int:
        """
        Turn an act identifier into an integer for sorting.
        Accepts either an int or something like "I", "II", "3", etc.
        """
        if isinstance(act, int):
            return act
        # Strip non-digits (handles "Act I" or roman numerals poorly, but if yours
        # are already ints or simple strings this will work)
        digits = re.findall(r"\d+", str(act))
        return int(digits[0]) if digits else 0

    def _scene_to_int(self, scene: Union[int, str]) -> int:
        """
        Same idea for scene numbers.
        """
        if isinstance(scene, int):
            return scene
        digits = re.findall(r"\d+", str(scene))
        return int(digits[0]) if digits else 0
        
    def generate_scenes(self, length_option: str = "medium") -> Tuple[bool, str]:
        """
        Generate scenes from the expanded story.
        
        Args:
            length_option: Scene length option ("short", "medium", or "long")
            
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
                expanded_story_path=self.expanded_story_path,
                length_option=length_option,
                session_id=None
            )
            
            # Generate scenes
            writer.generate_scenes()
            
            # Log the result
            self._log(f"Scenes saved to {writer.output_dir}")
            
            return True, writer.output_dir
        
        except Exception as e:
            error_msg = f"Error generating scenes: {str(e)}"
            self._log(error_msg, "error")
            return False, error_msg
    
    # Note: Scene adjustment functionality is experimental and not currently 
    # connected to the UI. This can be activated for future development if needed.
    def adjust_scene(self, scene_path: str, critique: str,
                    output_dir: Optional[str] = None) -> Tuple[bool, str]:
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
            adjusted_text = adjuster.revise_scene(
                scene_path=scene_path,
                critique=critique,
                output_dir=output_dir
            )
            
            # Log the result
            self._log(f"Scene adjustment completed")
            
            return True, adjusted_text
        except Exception as e:
            error_msg = f"Error adjusting scene: {str(e)}"
            self._log(error_msg, "error")
            return False, error_msg
    
    def generate_project_scene(self,
                               project_id: str,
                               act: str,
                               scene: str,
                               length_option: str = "medium",
                               session_id: Optional[str] = None
                               ) -> Tuple[bool, str, str]:
        """
        Generate a specific scene from a project.
        
        Args:
            project_id: Project identifier
            act: Act identifier (e.g. "I" or "1")
            scene: Scene identifier (e.g. "1")
            length_option: Scene length option ("short", "medium", "long")
            session_id: Optional session identifier for namespacing
        
        Returns:
            Tuple: (success flag, scene content or error message, scene file path)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, "Playwright modules not available", ""
        
        try:
            self._log(f"Generating scene for project {project_id}: Act {act}, Scene {scene}", "info")

            # 1) Establish session_id
            import time
            if session_id is None:
                session_id = str(int(time.time()))
            self._log(f"Using session_id: {session_id}", "debug")

            # 2) Load project and locate the requested scene
            pm = ProjectManager(logger=self.logger)
            project_data = pm.get_project_data(project_id)
            if not project_data:
                return False, f"Project not found: {project_id}", ""
            
            # Find matching scene entry
            scene_data = None
            for s in project_data.get("scenes", []):
                if s.get("act") == act and s.get("scene") == scene:
                    scene_data = s
                    break
            if not scene_data:
                return False, f"Scene {act}.{scene} not found in project", ""
            
            # 3) Prepare session folder (generation_sessions/session_<id>)
            project_folder = Path("data") / "play_projects" / project_id
            session_folder = project_folder / "generation_sessions" / f"session_{session_id}"
            ensure_directory(str(session_folder))
            self._log(f"Session folder: {session_folder}", "debug")

            # 4) If there's a previous session, copy over voices & summaries
            prev_dir = project_folder / "generation_sessions"
            previous = sorted(prev_dir.glob("session_*"), reverse=True)
            if previous:
                latest = previous[0]
                for fname in ("character_voices.json", "scene_summaries.json"):
                    src = latest / fname
                    dst = session_folder / fname
                    if src.exists():
                        try:
                            shutil.copy2(str(src), str(dst))
                            self._log(f"Copied {fname} from {latest}", "debug")
                        except Exception as e:
                            self._log(
                                f"Could not copy {fname} from previous session ({latest}): {e}",
                                "warning"
                            )

            # 5) Write out only *this* scene into scene_summaries.json
            sm = StoryManager(logger=self.logger)
            sm.save_scene_summaries({"scenes": [scene_data]}, str(session_folder))
            sm.save_character_voices(project_data.get("character_voices", {}), str(session_folder))
            self._log("Scene summaries & voices written", "debug")

            # 6) Expand that one scene
            expanded_path = session_folder / "expanded_story.json"
            try:
                expander = StoryExpander(
                    config_path=self.config_path,
                    scene_summaries_path=str(session_folder / "scene_summaries.json"),
                    character_voices_path=str(session_folder / "character_voices.json"),
                    output_path=str(expanded_path)
                )
                expander.expand_all_scenes()
                self._log(f"Expanded story saved to {expanded_path}", "info")
            except Exception as e:
                err = f"Error expanding story: {e}"
                self._log(err, "error")
                return False, err, ""

            # 7) Generate the Markdown + JSON for that scene
            scenes_dir = project_folder / "scenes" / f"session_{session_id}"
            ensure_directory(str(scenes_dir))
            try:
                self._log("Starting scene writer", "debug")
                writer = SceneWriter(
                    config_path=self.config_path,
                    expanded_story_path=str(expanded_path),
                    output_dir=str(scenes_dir),
                    length_option=length_option,
                    session_id=session_id
                )
                writer.generate_scenes()
                self._log(f"Scenes saved to {writer.output_dir}", "info")
            except Exception as e:
                err = f"Error generating scenes: {e}"
                self._log(err, "error")
                return False, err, ""

            # 8) Compute the exact .md filepath for our single scene
            filename = f"session_{session_id}_act_{str(act).lower()}_scene_{str(scene).lower()}.md"
            scene_md_path = scenes_dir / filename
            if not scene_md_path.exists():
                return False, f"Generated scene file not found: {scene_md_path}", ""
            
            self._log(f"Full scene path: {scene_md_path}", "debug")

            # 9) Read and return its contents
            content = load_text_from_file(str(scene_md_path))
            if content is None:
                return False, f"Failed to read generated scene file: {scene_md_path}", ""
            
            return True, content, str(scene_md_path)

        except Exception as e:
            err = f"Error generating project scene: {e}"
            self._log(err, "error")
            return False, err, ""
    
    def generate_full_project(
        self,
        project_id: str,
        length_option: str = "medium",
        session_id: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Generate all scenes for a project and combine them into a full play.
        Delegates each scene to generate_project_scene, then concatenates
        the resulting .md files in act/scene order.

        Args:
            project_id: Project identifier
            length_option: Scene length option ("short", "medium", "long")
            session_id: Optional session identifier for namespacing outputs

        Returns:
            Tuple of (success flag, output_path or error message)
        """
        if session_id is None:
            session_id = str(int(time.time()))
        self._log(f"Using session_id: {session_id}", "debug")    
        try:
            self._log(f"Generating full project for {project_id}", "info")

            # Load project data
            from modules.ui.playwright.project_manager import ProjectManager
            project_manager = ProjectManager(logger=self.logger)
            project_data = project_manager.get_project_data(project_id)
            if not project_data:
                msg = f"Project not found: {project_id}"
                self._log(msg, "error")
                return False, msg, session_id

            scenes = project_data.get("scenes", [])
            self._log(f"[DEBUG] Total scenes to generate: {len(scenes)}", "debug")
            self._log(f"[DEBUG] Scene list: {[(s.get('act'), s.get('scene')) for s in scenes]}", "debug")
            if not scenes:
                msg = "No scenes defined in project"
                self._log(msg, "warning")
                return False, msg, session_id

            # Prepare output directory for this session
            project_folder = Path("data") / "play_projects" / project_id
            session_scenes_dir = project_folder / "scenes" / f"session_{session_id}"
            ensure_directory(str(session_scenes_dir))
            self._log(f"Session scenes directory: {session_scenes_dir}", "debug")

            md_paths: List[Path] = []
            # Generate each scene
            for s in scenes:
                act, scene = s["act"], s["scene"]
                self._log(f"[DEBUG] Loop iteration for scene_data: act={act!r}, scene={scene!r}", "debug")
                self._log(f"Generating Act {act}, Scene {scene}", "info")
                ok, content_or_err, scene_md = self.generate_project_scene(
                    project_id, act, scene, length_option, session_id
                )
                self._log(f"[DEBUG] generate_project_scene returned: success={ok}, message={scene_md}", "debug")
                if not ok:
                    # Propagate the first failure
                    self._log(f"Failed to generate scene {act}.{scene}: {content_or_err}", "error")
                    return False, content_or_err, session_id
                md_paths.append(Path(scene_md))

            # Sort by act/scene
            def sort_key(p: Path):
                a, sc = extract_act_scene_from_filename(p.name)
                return (self._act_to_int(a), self._scene_to_int(sc))
            md_paths.sort(key=sort_key)

            # Combine
            combined = ""
            for md in md_paths:
                try:
                    self._log(f"Reading {md}", "debug")
                    text = md.read_text(encoding="utf-8").strip()
                    combined += text + "\n\n"
                except Exception as e:
                    msg = f"Error reading {md}: {e}"
                    self._log(msg, "error")
                    return False, msg, session_id

            # Write out
            output_filename = f"session_{session_id}_{project_id}_full_play.md"
            output_path = project_folder / "exports" / output_filename
            ensure_directory(str(output_path.parent))
            output_path.write_text(combined, encoding="utf-8")
            self._log(f"Full play saved to {output_path}", "info")

            return True, str(output_path), session_id

        except Exception as e:
            msg = f"Unexpected error in generate_full_project: {e}"
            self._log(msg, "error")
            return False, msg, session_id
