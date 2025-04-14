# rerun_fragments_only.py

import json
import time
from chromadb import PersistentClient
from modules.rag.embeddings import EmbeddingGenerator
from modules.rag.vector_store import VectorStore
from modules.utils.logger import CustomLogger

FRAGMENTS_JSON = "data/processed_chunks/fragments.json"
CHROMA_PATH = "embeddings/chromadb_vectors"
COLLECTION_NAME = "fragments"

def load_chunks(path: str) -> list:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)["chunks"]

def delete_fragment_collection(path=CHROMA_PATH, collection_name=COLLECTION_NAME):
    client = PersistentClient(path=path)
    try:
        client.delete_collection(name=collection_name)
        print(f"🧹 Deleted existing Chroma collection: '{collection_name}'")
    except Exception as e:
        print(f"⚠️ Warning: Could not delete collection '{collection_name}': {e}")

def add_documents_in_batches(store, embedded_chunks, batch_size=1000, logger=None):
    total = len(embedded_chunks)
    logger = logger or CustomLogger("BatchInsert")
    logger.info(f"Inserting {total} embedded chunks into Chroma in batches of {batch_size}...")

    start = time.time()
    for i in range(0, total, batch_size):
        batch = embedded_chunks[i:i+batch_size]
        try:
            store.add_documents(batch)
            logger.info(f"Batch {i // batch_size + 1}: Inserted {len(batch)} fragments")
        except Exception as e:
            logger.error(f"❌ Error inserting batch {i // batch_size + 1}: {e}")
            raise
    elapsed = time.time() - start
    logger.info(f"✅ All batches inserted in {elapsed:.2f} seconds")

def main():
    overall_start = time.time()
    logger = CustomLogger("FRAGMENTS_Setup")
    logger.info("=== Starting FRAGMENTS rerun ===")

    # Step 1: Delete old fragment collection only
    delete_fragment_collection()

    # Step 2: Load chunks from JSON
    logger.info(f"Loading fragment chunks from {FRAGMENTS_JSON}...")
    fragments = load_chunks(FRAGMENTS_JSON)
    logger.info(f"Loaded {len(fragments)} fragments")

    # Step 3: Embed without saving JSON
    embedder = EmbeddingGenerator(logger=logger)
    embed_start = time.time()
    embedded_chunks = embedder.embed_chunks(fragments)
    embed_elapsed = time.time() - embed_start
    logger.info(f"✅ Embedding complete in {embed_elapsed:.2f} seconds")

    # Step 4: Insert into Chroma
    store = VectorStore(collection_name=COLLECTION_NAME, logger=logger)
    add_documents_in_batches(store, embedded_chunks, batch_size=1000, logger=logger)

    total_time = time.time() - overall_start
    logger.info(f"🎉 All fragments embedded and inserted in {total_time:.2f} seconds total.")

if __name__ == "__main__":
    main()
