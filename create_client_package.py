"""
Create Client Package Script for Shakespeare AI.

This script creates a cleaned client-facing package from the full development repository.
It includes only the components necessary for running the application and excludes
development and data processing components.
"""
import os
import sys
import shutil
import argparse
from pathlib import Path
import datetime
import json

# Define the client package structure - only include what's needed
CLIENT_PACKAGE_STRUCTURE = {
    # Root files
    "root_files": [
        "streamlit_ui.py",
        "client_setup.py",
        "setup.py",
        "requirements.txt",
        "README.md",
        "INSTALLATION_GUIDE.md",
        ".env.template"
    ],
    # Module directories with specific files to include
    "module_directories": {
        "modules/ui": [
            "__init__.py",
            "config_manager.py",
            "session_manager.py",
            "file_helper.py",
            "ui_translator.py",
            "ui_playwright.py"
        ],
        "modules/ui/playwright": [
            "__init__.py",
            "config_manager.py",
            "export_manager.py",
            "project_manager.py",
            "scene_generator.py",
            "story_manager.py",
            "ui_playwright.py"
        ],
        "modules/playwright": [
            "__init__.py",
            "config.py",
            "story_expander.py",
            "scene_writer.py",
            "artistic_adjuster.py"
        ],
        "modules/translator": [
            "__init__.py",
            "config.py",
            "translation_manager.py",
            "assembler.py",
            "selector.py",
            "scene_saver.py",
            "types.py",
            "rag_caller.py"
        ],
        "modules/rag": [
            "__init__.py",
            "search_engine.py",
            "vector_store.py",
            "used_map.py",
            "embeddings.py"
        ],
        "modules/chunking": [
            "__init__.py",
            "base.py",
            "line_chunker.py",
            "phrase_chunker.py",
            "fragment_chunker.py"
        ],
        "modules/validation": [
            "__init__.py",
            "validator.py"
        ],
        "modules/output": [
            "__init__.py",
            "final_output_generator.py",
            "format_translated_play.py",
            "save_modern_play.py"
        ],
        "modules/utils": [
            "__init__.py",
            "logger.py"
        ]
    },
    # Minimal data needed for operation
    "data_files": {
        "data/processed_chunks": [
            "lines.json",
            "phrases.json", 
            "fragments.json"
        ],
        "data/line_corpus": [  # For validator ground truth
            "lines.json"
        ],
        "data/prompts": [
            "character_voices.json",
            "scene_summaries.json"
        ]
    },
    # Empty directories to create (will be created during operation)
    "empty_directories": [
        "embeddings",  # Add chromadb_vectors here
        "outputs/translated_scenes",
        "outputs/test_run", 
        "outputs/section_translations",
        "translation_sessions",
        "data/used_maps",  # This will be created when needed
        "data/play_projects",  # For playwright projects
        "logs",  # For application logs
        "config",  # For any config files generated at runtime
        "temp"  # For temporary files
    ]
}

def ensure_directory(dir_path):
    """Create directory if it doesn't exist."""
    os.makedirs(dir_path, exist_ok=True)

def create_readme(directory, content="This directory is used for storing output files."):
    """Create a README.md file in the specified directory."""
    readme_path = os.path.join(directory, "README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

def copy_file(source, destination, verbose=True):
    """Copy a file with error handling."""
    try:
        shutil.copy2(source, destination)
        if verbose:
            print(f"  Copied: {source} -> {destination}")
        return True
    except FileNotFoundError:
        print(f"  Warning: Source file not found: {source}")
        return False
    except Exception as e:
        print(f"  Error copying {source}: {e}")
        return False

def create_package_info(package_dir, source_dir):
    """Create a package_info.json file with metadata about the package."""
    info = {
        "package_name": "Shakespeare AI",
        "created_date": datetime.datetime.now().isoformat(),
        "source_directory": str(source_dir),
        "package_directory": str(package_dir),
        "version": "1.0.0",
        "included_modules": list(CLIENT_PACKAGE_STRUCTURE["module_directories"].keys()),
        "included_data": list(CLIENT_PACKAGE_STRUCTURE["data_files"].keys())
    }
    
    info_path = os.path.join(package_dir, "package_info.json")
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2)

def create_client_package(source_dir, output_dir, package_name=None, verbose=True):
    """
    Create a client package from the source directory.
    
    Args:
        source_dir: Source directory with the full project
        output_dir: Directory where the client package will be created
        package_name: Name of the package directory (defaults to shakespeare_ai_client)
        verbose: Whether to print verbose output
    
    Returns:
        Path to the created package
    """
    # Convert to absolute paths
    source_dir = os.path.abspath(source_dir)
    output_dir = os.path.abspath(output_dir)
    
    # Create package name with timestamp if not provided
    if not package_name:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        package_name = f"shakespeare_ai_client_{timestamp}"
    
    # Full path to the package directory
    package_dir = os.path.join(output_dir, package_name)
    
    # Ensure output directory exists
    ensure_directory(output_dir)
    
    # Create the package directory
    if os.path.exists(package_dir):
        if verbose:
            print(f"Package directory already exists. Removing: {package_dir}")
        shutil.rmtree(package_dir)
    
    ensure_directory(package_dir)
    
    if verbose:
        print(f"Creating client package in: {package_dir}")
    
    # 1. Copy root files
    if verbose:
        print("\nCopying root files...")
    
    for filename in CLIENT_PACKAGE_STRUCTURE["root_files"]:
        source_path = os.path.join(source_dir, filename)
        dest_path = os.path.join(package_dir, filename)
        copy_file(source_path, dest_path, verbose)
    
    # 2. Copy module directories and files
    if verbose:
        print("\nCopying module files...")
    
    for module_dir, files in CLIENT_PACKAGE_STRUCTURE["module_directories"].items():
        # Create the module directory
        module_path = os.path.join(package_dir, module_dir)
        ensure_directory(module_path)
        
        # Copy each file
        for filename in files:
            source_path = os.path.join(source_dir, module_dir, filename)
            dest_path = os.path.join(module_path, filename)
            
            # For __init__.py, create it if it doesn't exist
            if filename == "__init__.py" and not os.path.exists(source_path):
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write("")
                if verbose:
                    print(f"  Created: {dest_path}")
            else:
                copy_file(source_path, dest_path, verbose)
    
    # 3. Copy specific data files
    if verbose:
        print("\nCopying required data files...")
    
    for data_dir, files in CLIENT_PACKAGE_STRUCTURE["data_files"].items():
        # Create the data directory
        data_path = os.path.join(package_dir, data_dir)
        ensure_directory(data_path)
        
        # Copy each file
        for filename in files:
            source_path = os.path.join(source_dir, data_dir, filename)
            dest_path = os.path.join(data_path, filename)
            
            if not copy_file(source_path, dest_path, verbose):
                # If the file doesn't exist, create an empty placeholder
                if filename.endswith('.json'):
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        json.dump({}, f, indent=2)
                    if verbose:
                        print(f"  Created empty: {dest_path}")
    
    # 4. Create empty directories
    if verbose:
        print("\nCreating empty directories...")
    
    for directory in CLIENT_PACKAGE_STRUCTURE["empty_directories"]:
        dir_path = os.path.join(package_dir, directory)
        ensure_directory(dir_path)
        
        # Create appropriate README for each directory
        readme_content = "This directory is used for storing output files."
        if "embeddings" in directory:
            readme_content = "Extract the Chroma database (chromadb_vectors folder) here."
        elif "used_maps" in directory:
            readme_content = "This directory stores translation session data and will be created automatically."
        elif "play_projects" in directory:
            readme_content = "This directory stores playwright project data."
        elif "logs" in directory:
            readme_content = "Application logs are stored here."
        
        create_readme(dir_path, readme_content)
        if verbose:
            print(f"  Created directory: {dir_path}")
    
    # 5. Create package info file
    create_package_info(package_dir, source_dir)
    
    if verbose:
        print(f"\nClient package created successfully: {package_dir}")
    
    return package_dir

def main():
    """Main function to parse arguments and create the client package."""
    parser = argparse.ArgumentParser(description="Create a client package for Shakespeare AI")
    parser.add_argument("--source", default=".", help="Source directory with the full project")
    parser.add_argument("--output", default="./client_packages", help="Output directory for the client package")
    parser.add_argument("--name", help="Name of the package directory")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    
    args = parser.parse_args()
    
    try:
        package_dir = create_client_package(
            source_dir=args.source,
            output_dir=args.output,
            package_name=args.name,
            verbose=not args.quiet
        )
        
        print(f"\nClient package created successfully in: {package_dir}")
        print("\nNext steps:")
        print("1. Verify the package contents")
        print("2. Test the package installation")
        print("3. Create a zip archive if needed:")
        print(f"   zip -r {os.path.basename(package_dir)}.zip {package_dir}")
        
        return 0
    
    except Exception as e:
        print(f"Error creating client package: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())