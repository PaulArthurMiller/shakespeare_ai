import os
import sys
from pathlib import Path

def check_environment():
    """Check if the environment is properly set up."""
    try:
        # Check Python version
        print(f"Python version: {sys.version}")
        
        # Check API keys
        from dotenv import load_dotenv
        load_dotenv()
        
        api_keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
        }
        
        for key, value in api_keys.items():
            status = "✓ Available" if value else "✗ Missing"
            print(f"{key}: {status}")
            
        # Check for required packages
        import spacy
        import chromadb
        import streamlit
        import anthropic
        import openai
        
        print("All required packages are installed.")
        
        # Check spaCy model
        try:
            nlp = spacy.load("en_core_web_sm")
            print("spaCy model loaded successfully.")
        except OSError:
            print("✗ spaCy model 'en_core_web_sm' not found. Please install it with:")
            print("   python -m spacy download en_core_web_sm")
            
        return True
    except ImportError as e:
        print(f"✗ Missing package: {e}")
        print("Please install all required packages with: pip install -r requirements.txt")
        return False

def check_database():
    """Check if the Chroma database is available."""
    try:
        from modules.rag.vector_store import VectorStore
        
        # First check if the directories exist
        embeddings_path = Path("embeddings/chromadb_vectors")
        if not embeddings_path.exists():
            print(f"✗ Database directory not found: {embeddings_path}")
            return False
            
        # Check for the subdirectories
        required_dirs = ["lines", "phrases", "fragments"]
        missing_dirs = [d for d in required_dirs if not (embeddings_path / d).exists()]
        
        if missing_dirs:
            print(f"✗ Missing database components: {', '.join(missing_dirs)}")
            return False
            
        # Try to initialize the vector store
        print("Attempting to load the vector stores...")
        
        for collection_name in ["lines", "phrases", "fragments"]:
            try:
                store = VectorStore(collection_name=collection_name)
                # Try a simple operation
                info = store.collection.count()
                print(f"✓ Collection '{collection_name}' loaded successfully with {info} items.")
            except Exception as e:
                print(f"✗ Error loading collection '{collection_name}': {e}")
                return False
                
        return True
    except Exception as e:
        print(f"✗ Error checking database: {e}")
        return False

if __name__ == "__main__":
    print("\n=== Shakespeare AI System Check ===\n")
    
    env_ok = check_environment()
    print("\n--- Environment Check ---")
    if env_ok:
        print("✓ Environment is properly configured.")
    else:
        print("✗ Environment is not properly configured. See errors above.")
        
    print("\n--- Database Check ---")
    db_ok = check_database()
    if db_ok:
        print("✓ Database is properly installed and accessible.")
    else:
        print("✗ Database is not properly installed or accessible. See errors above.")
        
    print("\n--- Overall Status ---")
    if env_ok and db_ok:
        print("✓ System is ready to run!")
        print("\nYou can start the application with: streamlit run streamlit_ui.py")
    else:
        print("✗ System setup is incomplete. Please fix the issues before running the application.")