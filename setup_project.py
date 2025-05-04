"""
Setup script for Shakespeare AI project.

This script creates the necessary directory structure and initial files
for the Shakespeare AI project.
"""
import os
import shutil
from pathlib import Path
import argparse

# Define the project structure
PROJECT_STRUCTURE = {
    "modules": {
        "ui": {},
        "playwright": {},
        "translator": {},
        "utils": {},
        "rag": {},
        "validation": {},
        "output": {},
        "chunking": {}
    },
    "data": {
        "modern_play": {},
        "prompts": {},
        "processed_chunks": {},
        "templates": {},
        "raw_texts": {}
    },
    "outputs": {
        "translated_scenes": {},
        "test_run": {},
        "section_translations": {}
    },
    "logs": {},
    "embeddings": {
        "chromadb_vectors": {}
    },
    "translation_sessions": {},
    "tests": {},
    "config": {}
}

def create_directory_structure(base_path, structure, verbose=True):
    """Create the directory structure starting from base_path."""
    for dir_name, substructure in structure.items():
        dir_path = os.path.join(base_path, dir_name)
        if verbose:
            print(f"Creating directory: {dir_path}")
        os.makedirs(dir_path, exist_ok=True)
        
        # Recursively create subdirectories
        if substructure:
            create_directory_structure(dir_path, substructure, verbose)

def copy_template_files(base_path, verbose=True):
    """Copy template files to the appropriate locations."""
    # List of (source, destination) tuples for files to copy
    template_files = [
        (".env.template", ".env.template"),
        ("requirements.txt", "requirements.txt"),
        ("setup.py", "setup.py"),
        ("README.md", "README.md"),
        ("INSTALLATION_GUIDE.md", "INSTALLATION_GUIDE.md")
    ]
    
    for source, destination in template_files:
        src_path = os.path.join(base_path, source)
        dest_path = os.path.join(base_path, destination)
        
        # Skip if source doesn't exist
        if not os.path.exists(src_path):
            if verbose:
                print(f"Warning: Source file {src_path} not found. Skipping.")
            continue
            
        if verbose:
            print(f"Copying {source} to {destination}")
        
        shutil.copy2(src_path, dest_path)

def create_init_files(base_path, verbose=True):
    """Create __init__.py files in all module directories."""
    for root, dirs, files in os.walk(base_path):
        # Only create __init__.py in module directories
        if "modules" in root and "__init__.py" not in files:
            init_path = os.path.join(root, "__init__.py")
            if verbose:
                print(f"Creating __init__.py in {root}")
            # Create an empty __init__.py file
            with open(init_path, "w") as f:
                f.write("")

def main():
    parser = argparse.ArgumentParser(description="Set up Shakespeare AI project structure")
    parser.add_argument("--path", default=".", help="Base path for the project")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    
    args = parser.parse_args()
    base_path = args.path
    verbose = not args.quiet
    
    if verbose:
        print(f"Setting up Shakespeare AI project in {os.path.abspath(base_path)}")
    
    # Create the directory structure
    create_directory_structure(base_path, PROJECT_STRUCTURE, verbose)
    
    # Copy template files
    copy_template_files(base_path, verbose)
    
    # Create __init__.py files
    create_init_files(base_path, verbose)
    
    if verbose:
        print("\nProject setup complete!")
        print("\nNext steps:")
        print("1. Install the required packages:")
        print("   pip install -r requirements.txt")
        print("2. Install the spaCy English model:")
        print("   python -m spacy download en_core_web_sm")
        print("3. Configure your API keys in the .env file")
        print("4. Run the application:")
        print("   streamlit run streamlit_ui.py")

if __name__ == "__main__":
    main()