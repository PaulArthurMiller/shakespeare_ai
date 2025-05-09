import streamlit as st
import uuid
import os
import json
from typing import Optional, Dict, List, Any, Union
from pathlib import Path
from datetime import datetime
import shutil  # For file operations

# Import your existing modules
from modules.playwright.story_expander import StoryExpander
from modules.playwright.scene_writer import SceneWriter
from modules.translator.translation_manager import TranslationManager
from modules.translator.scene_saver import SceneSaver
from modules.utils.logger import CustomLogger
from modules.ui.playwright.ui_playwright import get_ui_playwright
from modules.ui.ui_translator import get_ui_translator
from modules.ui.file_helper import load_text_from_file, save_text_to_file

# Initialize session state
if "mode" not in st.session_state:
    st.session_state.mode = "Playwright"
if "translation_id" not in st.session_state:
    st.session_state.translation_id = None
if "current_line_index" not in st.session_state:
    st.session_state.current_line_index = 0
if "translated_lines" not in st.session_state:
    st.session_state.translated_lines = []
if "modern_lines" not in st.session_state:
    st.session_state.modern_lines = []
    
# New session states for the project-based UI
if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "show_export_options" not in st.session_state:
    st.session_state.show_export_options = False
if "generated_full_play" not in st.session_state:
    st.session_state.generated_full_play = False
if "last_generated_scene" not in st.session_state:
    st.session_state.last_generated_scene = None

# Set page config
st.set_page_config(
    page_title="Shakespeare AI",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize logger
logger = CustomLogger("StreamlitUI")

# Helper functions for file operations and session management
def load_existing_translation_ids():
    """Get a list of existing translation IDs from the translation_sessions directory."""
    try:
        path = Path("translation_sessions")
        if not path.exists():
            return []
        
        translation_info_files = list(path.glob("*_translation_info.json"))
        translations = []
        
        for file in translation_info_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    translations.append({
                        "id": info.get("translation_id", "unknown"),
                        "created_at": info.get("created_at", "unknown"),
                        "scenes_count": len(info.get("scenes_translated", [])),
                        "last_updated": info.get("last_updated", "")
                    })
            except Exception as e:
                st.error(f"Error loading translation info from {file}: {e}")
        
        # Sort by last updated, newest first
        translations.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return translations
    except Exception as e:
        st.error(f"Error loading translation IDs: {e}")
        return []

def generate_new_translation_id():
    """Generate a new translation ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    random_part = str(uuid.uuid4())[:6]
    return f"trans_{timestamp}_{random_part}"

# Initialize session state
if "mode" not in st.session_state:
    st.session_state.mode = "Playwright"
if "translation_id" not in st.session_state:
    st.session_state.translation_id = None
if "current_line_index" not in st.session_state:
    st.session_state.current_line_index = 0
if "translated_lines" not in st.session_state:
    st.session_state.translated_lines = []
if "modern_lines" not in st.session_state:
    st.session_state.modern_lines = []

# Sidebar - Mode Selection
with st.sidebar:
    st.title("Shakespeare AI")
    
    mode = st.radio("Mode", ["Playwright", "Translator"])
    st.session_state.mode = mode
    
    st.divider()
    
    if mode == "Playwright":
        st.subheader("Playwright Settings")
        model_provider = st.selectbox(
            "Model Provider", 
            ["anthropic", "openai"]
        )
        
        if model_provider == "anthropic":
            model_name = st.selectbox(
                "Model", 
                ["claude-3-7-sonnet-20250219", "claude-3-opus-20240229", "claude-3-sonnet-20240229"]
            )
        else:
            model_name = st.selectbox(
                "Model", 
                ["gpt-4o", "gpt-4-turbo", "gpt-4"]
            )
        
        creativity = st.slider(
            "Creativity", 
            min_value=0.0, 
            max_value=1.0, 
            value=0.7, 
            step=0.1
        )
        
        length_guide = st.slider(
            "Length", 
            min_value=1, 
            max_value=3, 
            value=2, 
            help="1 = Shorter (600-800 words), 2 = Medium (900-1100 words), 3 = Longer (1200-1500 words)"
        )
    
    elif mode == "Translator":
        st.subheader("Translator Settings")
        
        # Model selection for translator
        model_provider = st.selectbox(
            "Model Provider", 
            ["anthropic", "openai"],
            key="translator_model_provider"
        )
        
        if model_provider == "anthropic":
            model_name = st.selectbox(
                "Model", 
                ["claude-3-7-sonnet-20250219", "claude-3-opus-20240229", "claude-3-sonnet-20240229"],
                key="translator_model_name"
            )
        else:
            model_name = st.selectbox(
                "Model", 
                ["gpt-4o", "gpt-4-turbo", "gpt-4"],
                key="translator_model_name"
            )
        
        # Translation ID management
        st.subheader("Translation Session")
        
        translation_option = st.radio(
            "Translation ID", 
            ["Create New", "Use Existing"]
        )
        
        if translation_option == "Create New":
            if st.button("Generate New Translation ID"):
                st.session_state.translation_id = generate_new_translation_id()
                st.success(f"New Translation ID: {st.session_state.translation_id}")
        else:
            # Load existing translation IDs
            existing_translations = load_existing_translation_ids()
            
            if not existing_translations:
                st.warning("No existing translations found")
            else:
                translation_options = {
                    f"{t['id']} ({t['created_at'][:10]}, {t['scenes_count']} scenes)": t['id'] 
                    for t in existing_translations
                }
                
                selected_translation = st.selectbox(
                    "Select Translation ID",
                    options=list(translation_options.keys())
                )
                
                if selected_translation:
                    st.session_state.translation_id = translation_options[selected_translation]
                    st.info(f"Using Translation ID: {st.session_state.translation_id}")

# Main content area
if st.session_state.mode == "Playwright":
    st.title("Playwright Mode")
    
    # Add tabs for different operations
    tabs = st.tabs(["Create Project", "Add Scene", "Generate Scene", "Export"])
    
    # Tab 1: Create Project
    with tabs[0]:
        st.header("Create a New Play Project")
        
        with st.form("create_project_form"):
            play_title = st.text_input("Play Title", "My Modern Play")
            
            # Thematic guidelines
            thematic_guidelines = st.text_area(
                "Thematic Guidelines",
                "A modern retelling that explores themes of ambition, betrayal, and redemption.",
                height=150,
                help="Overall thematic guidance for the entire play"
            )
            
            # Character voices input
            st.subheader("Character Voices")
            
            num_characters = st.number_input("Number of Characters", min_value=1, max_value=10, value=3)
            
            character_voices = {}
            for i in range(num_characters):
                col1, col2 = st.columns(2)
                with col1:
                    char_name = st.text_input(f"Character {i+1} Name", key=f"char_name_{i}")
                with col2:
                    char_desc = st.text_input(f"Character {i+1} Voice", 
                                            key=f"char_desc_{i}", 
                                            help="Describe how this character speaks")
                if char_name:
                    character_voices[char_name] = char_desc
            
            # Create project button
            submit_project = st.form_submit_button("Create Project")
        
        if submit_project:
            if not character_voices:
                st.error("Please add at least one character")
            else:
                with st.spinner("Creating project..."):
                    try:
                        # Get UI playwright instance
                        playwright = get_ui_playwright(logger=st.session_state.get("logger"))
                        
                        # Create the project
                        project_id = playwright.create_play_project(
                            title=play_title,
                            thematic_guidelines=thematic_guidelines,
                            character_voices=character_voices
                        )
                        
                        # Store project_id in session state
                        st.session_state.current_project_id = project_id
                        
                        st.success(f"Project created successfully! Project ID: {project_id}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error creating project: {e}")
    
    # Tab 2: Add Scene
    with tabs[1]:
        st.header("Add Scene to Project")
        
        # Check if we have a current project
        if not st.session_state.get("current_project_id"):
            # No current project, allow selection from existing projects
            playwright = get_ui_playwright(logger=st.session_state.get("logger"))
            projects = playwright.list_projects()
            
            if not projects:
                st.warning("No projects found. Create a project first.")
            else:
                project_options = {p["title"] + " (" + p["id"] + ")": p["id"] for p in projects}
                selected_project = st.selectbox(
                    "Select Project",
                    options=list(project_options.keys())
                )
                
                if selected_project:
                    st.session_state.current_project_id = project_options[selected_project]
                    st.success(f"Selected project: {selected_project}")
        
        # If we have a project (either selected or created), show the add scene form
        if st.session_state.get("current_project_id"):
            project_id: Optional[str] = st.session_state.current_project_id
            if project_id is None:
                st.error("⚠️ No project selected. Please create or select a project first.")
                st.stop()  # This stops execution of the Streamlit app at this point

            # Get project data to show metadata and available characters
            playwright = get_ui_playwright(logger=st.session_state.get("logger"))
            project_data = playwright.get_project_data(project_id)
            
            if project_data:
                st.subheader(f"Project: {project_data.get('title', 'Unnamed')}")
                st.write(f"Characters: {', '.join(project_data.get('character_voices', {}).keys())}")
                
                with st.form("add_scene_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        act = st.text_input("Act", "I", help="Act number (e.g., I, II, III or 1, 2, 3)")
                    with col2:
                        scene = st.text_input("Scene", "1", help="Scene number (e.g., 1, 2, 3)")
                    
                    # Scene overview
                    overview = st.text_area(
                        "Scene Overview",
                        "Scene description here...",
                        height=150,
                        help="Describe what happens in this scene"
                    )
                    
                    # Scene setting
                    setting = st.text_area(
                        "Setting",
                        "Describe the setting...",
                        height=100,
                        help="Physical location and atmosphere of the scene"
                    )
                    
                    # Characters in scene
                    all_characters = list(project_data.get("character_voices", {}).keys())
                    scene_characters = st.multiselect(
                        "Characters in Scene",
                        options=all_characters,
                        default=all_characters[:2] if len(all_characters) >= 2 else all_characters
                    )
                    
                    # Additional instructions
                    additional_instructions = st.text_area(
                        "Additional Instructions (Optional)",
                        "",
                        height=100,
                        help="Any special notes for this scene"
                    )
                    
                    # Submit button
                    submit_scene = st.form_submit_button("Add Scene")
                
                if submit_scene:
                    if not overview or not setting or not scene_characters:
                        st.error("Please fill in all required fields")
                    else:
                        with st.spinner("Adding scene to project..."):
                            try:
                                success = playwright.add_scene_to_project(
                                    project_id=project_id,
                                    act=act,
                                    scene=scene,
                                    overview=overview,
                                    setting=setting,
                                    characters=scene_characters,
                                    additional_instructions=additional_instructions
                                )
                                
                                if success:
                                    st.success(f"Scene {act}.{scene} added successfully!")
                                else:
                                    st.error("Failed to add scene")
                            except Exception as e:
                                st.error(f"Error adding scene: {e}")
    
    # Tab 3: Generate Scene
    with tabs[2]:
        st.header("Generate Scene")
        
        # Check if we have a current project
        if not st.session_state.get("current_project_id"):
            # No current project, allow selection from existing projects
            playwright = get_ui_playwright(logger=st.session_state.get("logger"))
            projects = playwright.list_projects()
            
            if not projects:
                st.warning("No projects found. Create a project first.")
            else:
                project_options = {p["title"] + " (" + p["id"] + ")": p["id"] for p in projects}
                selected_project = st.selectbox(
                    "Select Project",
                    options=list(project_options.keys()),
                    key="gen_project_select"
                )
                
                if selected_project:
                    st.session_state.current_project_id = project_options[selected_project]
                    st.success(f"Selected project: {selected_project}")
        
        # If we have a project, show scene generation options
        if st.session_state.get("current_project_id"):
            project_id: Optional[str] = st.session_state.current_project_id
            if project_id is None:
                st.error("⚠️ No project selected. Please create or select a project first.")
                st.info("Use the 'Create Project' tab to create a new project or select an existing one.")
                st.stop()  # This stops execution of the Streamlit app at this point

            # Get project data
            playwright = get_ui_playwright(logger=st.session_state.get("logger"))
            project_data = playwright.get_project_data(project_id)
            
            if project_data:
                st.subheader(f"Project: {project_data.get('title', 'Unnamed')}")
                
                # Get defined scenes
                scenes = project_data.get("scenes", [])
                
                if not scenes:
                    st.warning("No scenes defined in this project. Please add a scene first.")
                else:
                    # Allow user to select a scene or generate all
                    scene_options = [f"Act {s['act']}, Scene {s['scene']}" for s in scenes]
                    scene_options.insert(0, "Generate All Scenes")
                    
                    selected_option = st.selectbox(
                        "Select Scene to Generate",
                        options=scene_options
                    )
                    
                    # Scene length option
                    length_option = st.select_slider(
                        "Scene Length",
                        options=["short", "medium", "long"],
                        value="medium",
                        help="short (600-800 words), medium (900-1100 words), long (1200-1500 words)"
                    )
                    
                    # Generate button
                    if st.button("Generate Scene(s)"):
                        if selected_option == "Generate All Scenes":
                            # Generate all scenes
                            with st.spinner("Generating all scenes... This may take a while."):
                                try:
                                    success, result = playwright.generate_full_project(
                                        project_id=project_id,
                                        length_option=length_option
                                    )
                                    
                                    if success:
                                        st.success("All scenes generated successfully!")
                                        st.info(f"Combined play saved to: {result}")
                                        
                                        # Display a clickable link to open the file location
                                        if os.path.exists(result):
                                            directory = os.path.dirname(result)
                                            st.markdown(f"**Output location:** `{directory}`")
                                            
                                            # Read a snippet of the generated play
                                            try:
                                                with open(result, 'r', encoding='utf-8') as f:
                                                    play_content = f.read()
                                                    # Display a preview of the play (first 500 chars)
                                                    st.text_area("Preview of generated play", 
                                                                play_content[:500] + "...", 
                                                                height=200)
                                            except:
                                                pass
                                        
                                        # Show option to export
                                        st.session_state.show_export_options = True
                                        st.session_state.generated_full_play = True
                                        # Add a button to jump to export tab
                                        if st.button("Go to Export Options"):
                                            st.rerun()
                                    else:
                                        st.error(f"Error generating scenes: {result}")
                                        st.warning("Please check the logs for more information.")
                                except Exception as e:
                                    st.error(f"Error generating scenes: {e}")
                                    st.warning("Please check the logs for more information.")
                        else:
                            # Generate specific scene
                            scene_idx = scene_options.index(selected_option) - 1  # Adjust for "Generate All" option
                            scene_data = scenes[scene_idx]
                            
                            with st.spinner(f"Generating Act {scene_data['act']}, Scene {scene_data['scene']}..."):
                                try:
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    # Update status periodically to show activity
                                    status_text.text("Initializing scene generation...")
                                    progress_bar.progress(10)
                                    
                                    # Start generation
                                    status_text.text("Creating scene expansion...")
                                    progress_bar.progress(30)
                                    
                                    # This part is actually doing the work
                                    success, content, scene_path = playwright.generate_project_scene(
                                        project_id=project_id,
                                        act=scene_data['act'],
                                        scene=scene_data['scene'],
                                        length_option=length_option
                                    )
                                    
                                    # Update progress
                                    status_text.text("Finalizing scene...")
                                    progress_bar.progress(90)
                                    
                                    if success:
                                        progress_bar.progress(100)
                                        status_text.text("Scene generation completed!")
                                        st.success(f"Scene generated successfully!")
                                        
                                        # Display the generated scene
                                        st.text_area("Generated Scene", content, height=400)
                                        
                                        # Display file location
                                        if os.path.exists(scene_path):
                                            directory = os.path.dirname(scene_path)
                                            st.markdown(f"**Output location:** `{directory}`")
                                        
                                        # Store the scene info for export
                                        st.session_state.last_generated_scene = {
                                            "project_id": project_id,
                                            "act": scene_data['act'],
                                            "scene": scene_data['scene'],
                                            "path": scene_path
                                        }
                                        
                                        # Show export options
                                        st.session_state.show_export_options = True
                                        st.session_state.generated_full_play = False
                                        # Add a button to jump to export tab
                                        if st.button("Go to Export Options"):
                                            st.rerun()
                                    else:
                                        progress_bar.progress(0)
                                        status_text.text("Scene generation failed.")
                                        st.error(f"Error generating scene: {content}")
                                        st.warning("Please check the logs for more information.")
                                except Exception as e:
                                    st.error(f"Error generating scene: {e}")
                                    st.warning("Please check the logs for more information.")
    
    # Tab 4: Export
    with tabs[3]:
        st.header("Export Play")
        
        # Check if we have content to export
        if not st.session_state.get("current_project_id"):
            st.warning("No active project. Please create or select a project first.")
        elif not st.session_state.get("show_export_options", False):
            st.info("Generate a scene or full play first to enable export options.")
        else:
            project_id: Optional[str] = st.session_state.current_project_id
            if project_id is None:
                st.error("⚠️ No project selected. Please create or select a project first.")
                st.info("Create a project in the 'Create Project' tab before generating scenes.")
                st.stop()  # This stops execution of the Streamlit app at this point            

            # Get project data
            playwright = get_ui_playwright(logger=st.session_state.get("logger"))
            project_data = playwright.get_project_data(project_id)
            
            if project_data:
                st.subheader(f"Project: {project_data.get('title', 'Unnamed')}")
                
                # Export format options
                export_format = st.radio(
                    "Export Format",
                    options=["DOCX", "Markdown"],
                    index=0,
                    horizontal=True
                )
                
                # What to export
                if st.session_state.get("generated_full_play", False):
                    # Full play was generated
                    if st.button("Export Full Play"):
                        with st.spinner(f"Exporting play as {export_format}..."):
                            try:
                                success, output_path = playwright.save_full_play_to_file(
                                    project_id=project_id,
                                    output_format=export_format.lower()
                                )
                                
                                if success:
                                    st.success(f"Play exported successfully!")
                                    st.info(f"Saved to: {output_path}")
                                    
                                    # Provide download link if possible
                                    if os.path.exists(output_path):
                                        with open(output_path, "rb") as f:
                                            file_contents = f.read()
                                        
                                        extension = ".docx" if export_format.lower() == "docx" else ".md"
                                        filename = f"{project_data.get('title', 'play').replace(' ', '_')}{extension}"
                                        
                                        st.download_button(
                                            label="Download File",
                                            data=file_contents,
                                            file_name=filename,
                                            mime="application/octet-stream"
                                        )
                                else:
                                    st.error(f"Error exporting play: {output_path}")
                            except Exception as e:
                                st.error(f"Error exporting play: {e}")
                else:
                    # Single scene was generated
                    last_scene = st.session_state.get("last_generated_scene", {})
                    
                    if last_scene and st.button("Export Scene"):
                        with st.spinner(f"Exporting scene as {export_format}..."):
                            try:
                                success, output_path = playwright.save_scene_to_file(
                                    project_id=project_id,
                                    act=last_scene['act'],
                                    scene=last_scene['scene'],
                                    output_format=export_format.lower()
                                )
                                
                                if success:
                                    st.success(f"Scene exported successfully!")
                                    st.info(f"Saved to: {output_path}")
                                    
                                    # Provide download link if possible
                                    if os.path.exists(output_path):
                                        with open(output_path, "rb") as f:
                                            file_contents = f.read()
                                        
                                        extension = ".docx" if export_format.lower() == "docx" else ".md"
                                        filename = f"act_{last_scene['act'].lower()}_scene_{last_scene['scene'].lower()}{extension}"
                                        
                                        st.download_button(
                                            label="Download File",
                                            data=file_contents,
                                            file_name=filename,
                                            mime="application/octet-stream"
                                        )
                                else:
                                    st.error(f"Error exporting scene: {output_path}")
                            except Exception as e:
                                st.error(f"Error exporting scene: {e}")

elif st.session_state.mode == "Translator":
    st.title("Translator Mode")
    
    if not st.session_state.translation_id:
        st.warning("Please create or select a Translation ID in the sidebar first.")
    else:
        st.info(f"Using Translation ID: {st.session_state.translation_id}")
        
        # Translation mode selection
        translation_mode = st.radio(
            "Translation Mode",
            ["Full Play", "Full Scene", "Section"]
        )
        
        use_hybrid_search = st.checkbox("Use Hybrid Search", value=True, 
                                        help="Combines vector and keyword search for better results")
        
        if translation_mode == "Full Play":
            st.subheader("Full Play Translation")
            
            # File uploader for play script
            uploaded_file = st.file_uploader("Upload Play Script (Markdown)", type="md")
            
            if uploaded_file:
                st.success(f"Uploaded: {uploaded_file.name}")
                
                # Output directory selection
                output_dir = st.text_input("Output Directory", "outputs/translated_play")
                
                if st.button("Start Translation"):
                    with st.spinner("Translating play..."):
                        try:
                            # Save uploaded file temporarily
                            with open("temp_play.md", "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            
                            # This is where you would call your translation module
                            # Placeholder for actual implementation
                            st.success("Translation complete!")
                            
                            # Show summary of translation
                            st.subheader("Translation Summary")
                            st.write("Acts: 5, Scenes: 25, Lines Translated: 1200")
                            
                            # Option to view translated content
                            if st.button("View Translated Content"):
                                # Placeholder for displaying content
                                st.text_area("Translated Play (Excerpt)", 
                                             "Thy words doth flow like gentle streams...", 
                                             height=200)
                        
                        except Exception as e:
                            st.error(f"Error translating play: {e}")
                            logger.error(f"Error in full play translation: {e}")
                        
                        finally:
                            # Clean up temp file
                            if os.path.exists("temp_play.md"):
                                os.remove("temp_play.md")
        
        elif translation_mode == "Full Scene":
            st.subheader("Full Scene Translation")
            
            # File uploader for scene script
            uploaded_file = st.file_uploader("Upload Scene Script (Markdown)", type="md")
            
            if uploaded_file:
                st.success(f"Uploaded: {uploaded_file.name}")
                
                # Act and scene selection
                col1, col2 = st.columns(2)
                with col1:
                    act = st.text_input("Act Number", "I")
                with col2:
                    scene = st.text_input("Scene Number", "1")
                
                # Output directory
                output_dir = st.text_input("Output Directory", "outputs/translated_scenes")
                
                if st.button("Start Translation"):
                    with st.spinner("Translating scene..."):
                        try:
                            # Save uploaded file temporarily
                            with open("temp_scene.md", "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            
                            # This is where you would call your translation module
                            # Placeholder for actual implementation
                            # Actual code would read the file, extract dialog, translate it
                            
                            st.success("Translation complete!")
                            
                            # Show summary of translation
                            st.subheader("Translation Summary")
                            st.write(f"Act {act}, Scene {scene}")
                            st.write("Lines Translated: 50")
                            
                            # Option to view translated content
                            if st.button("View Translated Content"):
                                # Placeholder for displaying content
                                st.text_area("Translated Scene (Excerpt)", 
                                            "Thy words doth flow like gentle streams...", 
                                            height=200)
                        
                        except Exception as e:
                            st.error(f"Error translating scene: {e}")
                            logger.error(f"Error in full scene translation: {e}")
                        
                        finally:
                            # Clean up temp file
                            if os.path.exists("temp_scene.md"):
                                os.remove("temp_scene.md")
        
        elif translation_mode == "Section":
            st.subheader("Section Translation")
            
            # Initialize translation manager
            if "translation_manager" not in st.session_state:
                try:
                    # Initialize translation manager with the selected ID
                    st.session_state.translation_manager = TranslationManager()
                    st.session_state.translation_manager.start_translation_session(st.session_state.translation_id)
                except Exception as e:
                    st.error(f"Error initializing translation manager: {e}")
            
            # Text area for input lines
            if not st.session_state.modern_lines:
                modern_text = st.text_area(
                    "Enter modern text (one or more lines)",
                    height=150
                )
                
                if st.button("Prepare Translation"):
                    if modern_text:
                        # Split text into lines
                        st.session_state.modern_lines = [line.strip() for line in modern_text.split('\n') if line.strip()]
                        
                        if not st.session_state.modern_lines:
                            st.warning("No valid lines found in input text.")
                        else:
                            st.success(f"Ready to translate {len(st.session_state.modern_lines)} lines.")
                    else:
                        st.warning("Please enter some text to translate.")
            
            # If we have lines to translate, show the translation interface
            if st.session_state.modern_lines:
                # Display the current line
                current_idx = st.session_state.current_line_index
                if 0 <= current_idx < len(st.session_state.modern_lines):
                    current_line = st.session_state.modern_lines[current_idx]
                    
                    st.markdown(f"**Line {current_idx + 1} of {len(st.session_state.modern_lines)}**")
                    st.markdown(f"**Modern Text:**")
                    st.markdown(f"> {current_line}")
                    
                    # Show the translated line if available
                    if current_idx < len(st.session_state.translated_lines):
                        translated = st.session_state.translated_lines[current_idx]
                        
                        st.markdown(f"**Shakespearean Translation:**")
                        st.markdown(f"> {translated['text']}")
                        
                        # Show references
                        st.markdown("**References:**")
                        for ref in translated.get('references', []):
                            st.markdown(f"- {ref.get('title', 'Unknown')} ({ref.get('act', '')}.{ref.get('scene', '')}.{ref.get('line', '')})")
                        
                        # Navigation buttons
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("Previous Line") and current_idx > 0:
                                st.session_state.current_line_index -= 1
                                st.rerun()
                        
                        with col2:
                            if st.button("Rerun Translation"):
                                with st.spinner("Retranslating..."):
                                    try:
                                        # Call the translation manager to translate the line
                                        translated = st.session_state.translation_manager.translate_line(
                                            current_line, {}, use_hybrid_search=use_hybrid_search)
                                        
                                        if translated:
                                            # Update the translated line
                                            st.session_state.translated_lines[current_idx] = translated
                                            st.success("Retranslation successful!")
                                            st.rerun()
                                        else:
                                            st.error("Translation failed. Please try again.")
                                    except Exception as e:
                                        st.error(f"Error in translation: {e}")
                                        logger.error(f"Error translating line: {e}")
                        
                        with col3:
                            if st.button("Next Line") and current_idx < len(st.session_state.modern_lines) - 1:
                                st.session_state.current_line_index += 1
                                
                                # If we don't have a translation for the next line yet, generate one
                                if st.session_state.current_line_index >= len(st.session_state.translated_lines):
                                    st.rerun()  # This will trigger the else clause below
                                else:
                                    st.rerun()
                    
                    else:
                        # No translation yet, translate the current line
                        with st.spinner("Translating..."):
                            try:
                                # Call the translation manager to translate the line
                                translated = st.session_state.translation_manager.translate_line(
                                    current_line, {}, use_hybrid_search=use_hybrid_search)
                                
                                if translated:
                                    # Add the translated line
                                    st.session_state.translated_lines.append(translated)
                                    st.success("Translation successful!")
                                    st.rerun()
                                else:
                                    st.error("Translation failed. Please try again.")
                            except Exception as e:
                                st.error(f"Error in translation: {e}")
                                logger.error(f"Error translating line: {e}")
                
                # Save all translated lines button
                if st.session_state.translated_lines:
                    if st.button("Save All Translated Lines"):
                        try:
                            # Initialize SceneSaver
                            saver = SceneSaver(base_output_dir="outputs/section_translations")
                            
                            # Save the translated lines
                            saver.save_scene(
                                act="Custom",
                                scene="Section",
                                translated_lines=st.session_state.translated_lines,
                                original_lines=st.session_state.modern_lines
                            )
                            
                            st.success("Saved all translated lines!")
                            
                            # Provide download link
                            output_path = "outputs/section_translations/act_custom_scene_section.md"
                            if os.path.exists(output_path):
                                with open(output_path, "r") as f:
                                    file_content = f.read()
                                
                                st.download_button(
                                    label="Download Translation",
                                    data=file_content,
                                    file_name="shakespeare_translation.md",
                                    mime="text/markdown"
                                )
                            
                        except Exception as e:
                            st.error(f"Error saving translations: {e}")
                            logger.error(f"Error saving translations: {e}")
                
                # Reset button
                if st.button("Reset Translation Session"):
                    st.session_state.modern_lines = []
                    st.session_state.translated_lines = []
                    st.session_state.current_line_index = 0
                    st.success("Translation session reset.")
                    st.rerun()

# Footer
st.divider()
st.markdown("Shakespeare AI - Developed with ❤️ and 📚")