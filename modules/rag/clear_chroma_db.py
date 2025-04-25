# clear_chroma_db.py

from chromadb import PersistentClient
from modules.utils.logger import CustomLogger

# Constants
CHROMA_PATH = "embeddings/chromadb_vectors"
COLLECTIONS = ["lines", "phrases", "fragments"]

def clear_collections(path=CHROMA_PATH, collections=COLLECTIONS):
    """Clear existing Chroma collections."""
    logger = CustomLogger("ChromaCleaner")
    logger.info("Clearing existing collections...")
    
    client = PersistentClient(path=path)
    for collection_name in collections:
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"🧹 Deleted Chroma collection: '{collection_name}'")
        except Exception as e:
            logger.warning(f"⚠️ Warning: Could not delete collection '{collection_name}': {e}")

if __name__ == "__main__":
    logger = CustomLogger("ChromaCleaner")
    logger.info("=== Starting Chroma DB cleanup ===")
    
    clear_collections()
    
    logger.info("=== Chroma DB cleanup complete ===")