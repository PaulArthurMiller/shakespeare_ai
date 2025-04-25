# test_chroma_query.py

import chromadb
from chromadb.config import Settings
import time
import openai
from modules.utils.logger import CustomLogger

# Constants
CHROMA_PATH = "embeddings/chromadb_vectors"
COLLECTION_TO_TEST = "fragments"  # Change to test different collections
EMBEDDING_MODEL = "text-embedding-3-large"

def get_embedding(text):
    """Get embedding for a text using OpenAI's embedding model."""
    response = openai.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def test_chroma_collection(collection_name: str = COLLECTION_TO_TEST):
    """Test a Chroma collection by running some basic queries."""
    logger = CustomLogger("ChromaTest")
    logger.info(f"Testing Chroma collection: {collection_name}")
    
    try:
        # Initialize client
        logger.info(f"Connecting to ChromaDB at: {CHROMA_PATH}")
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        
        # List all collections
        collections = client.list_collections()
        collection_names = [c.name for c in collections]
        logger.info(f"Available collections: {collection_names}")
        
        if collection_name not in collection_names:
            logger.error(f"Collection '{collection_name}' not found in ChromaDB!")
            return False
            
        # Get the collection
        collection = client.get_collection(name=collection_name)
        count = collection.count()
        logger.info(f"Collection '{collection_name}' contains {count} documents")
        
        if count == 0:
            logger.error("Collection is empty! Embedding process may have failed.")
            return False
            
        # Get some sample documents and their IDs
        logger.info("Fetching sample documents...")
        sample = collection.get(limit=5)
        
        if not sample or not sample["ids"]:
            logger.error("Failed to retrieve sample documents!")
            return False
            
        logger.info(f"Sample document IDs: {sample['ids']}")
        
        # Try fetching specific IDs
        first_id = sample["ids"][0]
        logger.info(f"Fetching document with ID: {first_id}")
        doc = collection.get(ids=[first_id])
        
        if not doc or not doc["metadatas"]:
            logger.error(f"Failed to retrieve document with ID: {first_id}")
            return False
            
        logger.info(f"Document metadata sample: {list(doc['metadatas'][0].keys())}")
        
        # Try a simple query
        logger.info("Testing query functionality...")
        query_text = "the king in his castle"  # Generic Shakespeare-like text
        
        # Get embedding for the query using OpenAI
        logger.info(f"Getting embedding using {EMBEDDING_MODEL}")
        query_embedding = get_embedding(query_text)
        
        # Query using the embedding
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )
        
        if not results or not results["distances"]:
            logger.error("Query returned no results!")
            return False
            
        logger.info(f"Query successful, found {len(results['ids'])} results")
        
        # Test successful!
        logger.info("✅ All tests passed! ChromaDB is working correctly.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_chroma_collection()
    
    if success:
        print("\n✅ ChromaDB test completed successfully!")
    else:
        print("\n❌ ChromaDB test failed. See log for details.")