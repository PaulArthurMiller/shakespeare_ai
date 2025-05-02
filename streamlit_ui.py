import streamlit as st
import uuid
import os
import json
from pathlib import Path
from datetime import datetime

# Import your existing modules
from modules.playwright.story_expander import StoryExpander
from modules.playwright.scene_writer import SceneWriter
from modules.translator.translation_manager import TranslationManager
from modules.translator.scene_saver import SceneSaver
from modules.utils.logger import CustomLogger

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
            max_value=5, 
            value=3, 
            help="1 = Shorter, 5 = Longer"
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
    
    with st.form("playwright_form"):
        use_full_play = st.checkbox("Generate Full Play", value=False)
        
        if use_full_play:
            st.subheader("Full Play Generation")
            
            st.subheader("Story Arc")
            story_arc = st.text_area(
                "Enter full play story arc",
                height=200,
                help="Describe the overall story arc of the play"
            )
            
            # Dynamic character inputs
            st.subheader("Characters")
            num_characters = st.number_input("Number of Characters", min_value=1, max_value=10, value=3)
            
            characters = {}
            for i in range(num_characters):
                col1, col2 = st.columns(2)
                with col1:
                    char_name = st.text_input(f"Character {i+1} Name")
                with col2:
                    char_desc = st.text_input(f"Character {i+1} Description")
                if char_name:
                    characters[char_name] = char_desc
            
            # Scene structure
            st.subheader("Scene Structure")
            num_acts = st.number_input("Number of Acts", min_value=1, max_value=5, value=3)
            
            all_scenes = {}
            for act in range(1, num_acts + 1):
                st.markdown(f"##### Act {act}")
                num_scenes = st.number_input(f"Number of Scenes in Act {act}", min_value=1, max_value=10, value=2)
                
                act_scenes = {}
                for scene in range(1, num_scenes + 1):
                    scene_desc = st.text_area(f"Act {act}, Scene {scene} Description", height=100)
                    act_scenes[str(scene)] = scene_desc
                
                all_scenes[str(act)] = act_scenes
            
        else:
            st.subheader("Single Scene Generation")
            
            col1, col2 = st.columns(2)
            with col1:
                act_number = st.text_input("Act Number", value="I")
            with col2:
                scene_number = st.text_input("Scene Number", value="1")
            
            # Character inputs for single scene
            st.subheader("Characters in Scene")
            num_characters = st.number_input("Number of Characters", min_value=1, max_value=10, value=3)
            
            scene_characters = {}
            for i in range(num_characters):
                col1, col2 = st.columns(2)
                with col1:
                    char_name = st.text_input(f"Character {i+1} Name", key=f"single_char_name_{i}")
                with col2:
                    char_desc = st.text_input(f"Character {i+1} Description", key=f"single_char_desc_{i}")
                if char_name:
                    scene_characters[char_name] = char_desc
            
            # Scene description
            scene_description = st.text_area(
                "Scene Description",
                height=200,
                help="Describe what happens in this scene"
            )
        
        # Submit button
        submit = st.form_submit_button("Generate")
    
    if submit:
        with st.spinner("Generating Shakespeare-style content..."):
            try:
                # Update config
                config = {
                    "model_provider": model_provider,
                    "model_name": model_name,
                    "temperature": creativity
                }
                
                # Here you would call your existing modules
                # This is a placeholder for the actual implementation
                st.success("Generation complete!")
                
                # Display output
                st.subheader("Generated Content")
                
                # Placeholder for actual generated content
                generated_content = "Thy words doth flow like gentle streams..."
                
                st.text_area("Output", generated_content, height=400)
                
                # Save to file option
                output_filename = st.text_input("Save to filename", "shakespeare_output.md")
                if st.button("Save to File"):
                    try:
                        with open(output_filename, "w") as f:
                            f.write(generated_content)
                        st.success(f"Saved to {output_filename}")
                    except Exception as e:
                        st.error(f"Error saving file: {e}")
                
            except Exception as e:
                st.error(f"Error generating content: {e}")
                logger.error(f"Error in playwright generation: {e}")

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
                            saver = SceneSaver(output_dir="outputs/section_translations")
                            
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