"""
UI Translator Adapter for Shakespeare AI.

This module provides an interface between the Streamlit UI and the 
underlying translator functionality, handling user input validation,
error handling, and format conversion for the UI.
"""
import os
import time
from typing import Dict, List, Any, Optional, Tuple, Union, cast

# Import module-specific helpers
from modules.ui.file_helper import (
    parse_markdown_scene,
    extract_act_scene_from_filename,
    save_uploaded_file,
    load_translated_scene,
    ensure_directory
)
from modules.ui.session_manager import (
    get_session_info,
    update_scene_info,
    is_scene_translated
)

# Import the core translator functionality
try:
    from modules.translator.translation_manager import TranslationManager
    from modules.translator.scene_saver import SceneSaver
    TRANSLATOR_AVAILABLE = True
except ImportError:
    print("Warning: Translator modules not available")
    TRANSLATOR_AVAILABLE = False


class UITranslator:
    """
    Adapter class for interfacing between the UI and the translator functionality.
    """
    
    def __init__(self, translation_id: Optional[str] = None, logger=None):
        """
        Initialize the UI translator.
        
        Args:
            translation_id: Optional translation session ID
            logger: Optional logger object (for Streamlit)
        """
        self.translation_id = translation_id
        self.logger = logger  # For Streamlit logging
        
        # Explicit typing to avoid None-type errors
        self.translation_manager: Optional[TranslationManager] = None
        
        # Flag to track if the translator is initialized
        self.is_initialized = False
        
        # Check if translator modules are available
        if not TRANSLATOR_AVAILABLE:
            self._log("Warning: Translator modules not available. Limited functionality.")
    
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
    
    def initialize(self, force_reinit: bool = False) -> bool:
        """
        Initialize the translator components.
        
        Args:
            force_reinit: Force reinitialization even if already initialized
            
        Returns:
            True if successful, False otherwise
        """
        if self.is_initialized and not force_reinit:
            return True
        
        if not TRANSLATOR_AVAILABLE:
            self._log("Error: Translator modules not available")
            return False
        
        try:
            # Initialize the translation manager
            self.translation_manager = TranslationManager()
            
            # Start a translation session if we have an ID
            if self.translation_id:
                if self.translation_manager is not None:
                    self.translation_manager.start_translation_session(self.translation_id)
                    self._log(f"Translation session started with ID: {self.translation_id}")
                else:
                    self._log("Failed to initialize translation manager")
                    return False
            else:
                self._log("No translation ID provided, session not started")
            
            self.is_initialized = True
            self._log(f"Translator initialized with ID: {self.translation_id}")
            return True
        except Exception as e:
            self._log(f"Error initializing translator: {e}")
            return False
    
    def set_translation_id(self, translation_id: str) -> bool:
        """
        Set the translation ID and initialize the translator.
        
        Args:
            translation_id: Translation session ID
            
        Returns:
            True if successful, False otherwise
        """
        if not translation_id:
            self._log("Error: Empty translation ID provided")
            return False
            
        self.translation_id = translation_id
        
        # Re-initialize with the new ID
        return self.initialize(force_reinit=True)
    
    def translate_line(self, modern_line: str, use_hybrid_search: bool = True) -> Optional[Dict[str, Any]]:
        """
        Translate a single modern line to Shakespearean English.
        
        Args:
            modern_line: Modern English line
            use_hybrid_search: Whether to use hybrid search
            
        Returns:
            Dictionary with translation results or None if failed
        """
        if not self.is_initialized:
            if not self.initialize():
                return None
        
        if not modern_line or not modern_line.strip():
            self._log("Error: Empty line provided for translation")
            return None
            
        if self.translation_manager is None:
            self._log("Error: Translation manager not initialized")
            return None
            
        try:
            # Start a timer to measure translation time
            start_time = time.time()
            
            self._log(f"Translating line: '{modern_line}'")
            
            # Call the translation manager
            result = self.translation_manager.translate_line(
                modern_line=modern_line,
                selector_results={},  # Empty dict tells the translator to run its own search
                use_hybrid_search=use_hybrid_search
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            if result:
                self._log(f"Translation completed in {elapsed_time:.2f} seconds")
                return result
            else:
                self._log(f"Translation failed after {elapsed_time:.2f} seconds")
                return None
                
        except Exception as e:
            self._log(f"Error translating line: {e}")
            return None
    
    def translate_lines(self, modern_lines: List[str], use_hybrid_search: bool = True) -> List[Dict[str, Any]]:
        """
        Translate multiple modern lines to Shakespearean English.
        
        Args:
            modern_lines: List of modern English lines
            use_hybrid_search: Whether to use hybrid search
            
        Returns:
            List of dictionaries with translation results
        """
        if not self.is_initialized:
            if not self.initialize():
                return []
        
        if not modern_lines:
            self._log("Error: Empty list of lines provided for translation")
            return []
            
        if self.translation_manager is None:
            self._log("Error: Translation manager not initialized")
            return []
        
        try:
            self._log(f"Translating {len(modern_lines)} lines")
            
            # Filter out empty lines
            filtered_lines = [line for line in modern_lines if line and line.strip()]
            
            if not filtered_lines:
                self._log("Error: All lines were empty after filtering")
                return []
                
            # Call the translation manager
            results = self.translation_manager.translate_group(
                modern_lines=filtered_lines,
                use_hybrid_search=use_hybrid_search
            )
            
            self._log(f"Translation completed for {len(results)} lines")
            return results
        except Exception as e:
            self._log(f"Error translating lines: {e}")
            return []
    
    def translate_file(
        self, 
        filepath: str, 
        output_dir: Optional[str] = None,
        force_retranslate: bool = False,
        use_hybrid_search: bool = True
    ) -> Tuple[bool, str, int]:
        """
        Translate a file containing modern English lines.
        
        Args:
            filepath: Path to the file
            output_dir: Optional output directory (uses default if not provided)
            force_retranslate: Force retranslation even if already translated
            use_hybrid_search: Whether to use hybrid search
            
        Returns:
            Tuple of (success, output_path, lines_translated)
        """
        if not self.is_initialized:
            if not self.initialize():
                return False, "", 0
                
        if not self.translation_id:
            self._log("Error: No translation ID set for file translation")
            return False, "", 0
            
        if not os.path.exists(filepath):
            self._log(f"Error: File not found: {filepath}")
            return False, "", 0
        
        try:
            # Extract act and scene from filename
            act, scene = extract_act_scene_from_filename(filepath)
            self._log(f"Translating file: {filepath} (Act {act}, Scene {scene})")
            
            # Check if this scene has already been translated
            if not force_retranslate and is_scene_translated(self.translation_id, act, scene):
                self._log(f"Scene Act {act}, Scene {scene} has already been translated")
                
                # Get the output directory from session info
                session_info = get_session_info(self.translation_id)
                existing_output_dir = session_info.get("output_dir", "")
                
                if existing_output_dir and os.path.exists(existing_output_dir):
                    scene_id = f"act_{act.lower()}_scene_{scene.lower()}"
                    json_path = os.path.join(existing_output_dir, f"{scene_id}.json")
                    
                    if os.path.exists(json_path):
                        translated_lines, _ = load_translated_scene(json_path)
                        return True, existing_output_dir, len(translated_lines)
                
                return True, "", 0
            
            # Parse the file to get dialogue lines
            modern_lines = parse_markdown_scene(filepath)
            
            if not modern_lines:
                self._log("No dialogue lines found in file")
                return False, "", 0
            
            # Determine output directory
            actual_output_dir: str
            if output_dir is None:
                session_info = get_session_info(self.translation_id)
                actual_output_dir = session_info.get("output_dir", "outputs/translated_scenes")
                if not actual_output_dir:
                    actual_output_dir = "outputs/translated_scenes"
            else:
                actual_output_dir = output_dir
            
            # Now ensure_directory receives a string, not Optional[str]
            ensure_directory(actual_output_dir)
            
            # Translate the lines
            translated_lines = self.translate_lines(
                modern_lines=modern_lines,
                use_hybrid_search=use_hybrid_search
            )
            
            if not translated_lines:
                self._log("Translation failed - no lines translated")
                return False, "", 0
            
            # Save the translation using SceneSaver
            if TRANSLATOR_AVAILABLE:
                saver = SceneSaver(translation_id=self.translation_id, base_output_dir=actual_output_dir)
                saver.save_scene(
                    act=act,
                    scene=scene,
                    translated_lines=translated_lines,
                    original_lines=modern_lines
                )
                
                # Update scene info in the session
                update_scene_info(
                    translation_id=self.translation_id,
                    act=act,
                    scene=scene,
                    filename=os.path.basename(filepath),
                    line_count=len(translated_lines)
                )
                
                self._log(f"Translation completed and saved to {actual_output_dir}")
                return True, actual_output_dir, len(translated_lines)
            else:
                self._log("Error: Translator modules not available for saving")
                return False, "", 0
                
        except Exception as e:
            self._log(f"Error translating file: {e}")
            return False, "", 0
    
    def translate_uploaded_file(
        self, 
        uploaded_file, 
        temp_dir: str = "temp",
        output_dir: Optional[str] = None,
        force_retranslate: bool = False,
        use_hybrid_search: bool = True
    ) -> Tuple[bool, str, int]:
        """
        Translate an uploaded file from Streamlit.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            temp_dir: Directory to save the temporary file
            output_dir: Optional output directory
            force_retranslate: Force retranslation even if already translated
            use_hybrid_search: Whether to use hybrid search
            
        Returns:
            Tuple of (success, output_path, lines_translated)
        """
        if not self.translation_id:
            self._log("Error: No translation ID set for file translation")
            return False, "", 0
            
        if uploaded_file is None:
            self._log("Error: No file uploaded")
            return False, "", 0
            
        try:
            # Save the uploaded file temporarily
            ensure_directory(temp_dir)
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Translate the file
            success, out_dir, line_count = self.translate_file(
                filepath=temp_path,
                output_dir=output_dir,
                force_retranslate=force_retranslate,
                use_hybrid_search=use_hybrid_search
            )
            
            # Clean up temp file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as remove_error:
                self._log(f"Warning: Could not remove temporary file: {remove_error}")
            
            return success, out_dir, line_count
        except Exception as e:
            self._log(f"Error processing uploaded file: {e}")
            return False, "", 0
    
    def get_translation_status(self) -> Dict[str, Any]:
        """
        Get the current status of the translation session.
        
        Returns:
            Dictionary with status information
        """
        if not self.translation_id:
            return {
                "initialized": False,
                "translation_id": None,
                "scene_count": 0,
                "message": "No translation session active"
            }
        
        session_info = get_session_info(self.translation_id)
        
        return {
            "initialized": self.is_initialized,
            "translation_id": self.translation_id,
            "scene_count": len(session_info.get("scenes_translated", [])),
            "output_dir": session_info.get("output_dir", ""),
            "created_at": session_info.get("created_at", ""),
            "last_updated": session_info.get("last_updated", "")
        }


# Create a function to get a singleton instance
_INSTANCE: Optional[UITranslator] = None

def get_ui_translator(translation_id: Optional[str] = None, logger=None) -> UITranslator:
    """
    Get the UITranslator instance (singleton pattern).
    
    Args:
        translation_id: Optional translation session ID
        logger: Optional logger object
        
    Returns:
        UITranslator instance
    """
    global _INSTANCE
    
    if _INSTANCE is None:
        _INSTANCE = UITranslator(translation_id=translation_id, logger=logger)
    elif translation_id and _INSTANCE.translation_id != translation_id:
        _INSTANCE.set_translation_id(translation_id)
    
    return _INSTANCE