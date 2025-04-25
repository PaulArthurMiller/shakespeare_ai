# verify_clear_chroma_db.py

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
    
    # Check what collections exist before deleting
    existing_collections = client.list_collections()
    logger.info(f"Collections before deletion: {[c.name for c in existing_collections]}")
    
    for collection_name in collections:
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"🧹 Deleted Chroma collection: '{collection_name}'")
        except Exception as e:
            logger.warning(f"⚠️ Warning: Could not delete collection '{collection_name}': {e}")
    
    # Verify collections are gone
    remaining_collections = client.list_collections()
    logger.info(f"Collections after deletion: {[c.name for c in remaining_collections]}")
    
    return len(remaining_collections) == 0

if __name__ == "__main__":
    logger = CustomLogger("ChromaCleaner")
    logger.info("=== Starting Chroma DB cleanup ===")
    
    success = clear_collections()
    
    if success:
        logger.info("=== All collections successfully removed ===")
    else:
        logger.warning("=== Some collections may still exist! ===")