import json
from typing import Optional
from modules.rag.embeddings import EmbeddingGenerator
from modules.rag.vector_store import VectorStore
from modules.utils.logger import CustomLogger

def load_chunks(path: str) -> list:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)["chunks"]

def embed_and_store(chunk_type: str, input_path: str, collection_name: str, output_path: Optional[str] = None):
    logger = CustomLogger(f"{chunk_type.upper()}_Setup")
    logger.info(f"Processing {chunk_type} chunks from: {input_path}")

    # Load & embed
    chunks = load_chunks(input_path)
    embedder = EmbeddingGenerator(logger=logger)
    embedded_chunks = embedder.embed_chunks(chunks)

    # Save locally if desired
    if output_path:
        embedder.save_embedded_chunks(embedded_chunks, output_path)

    # Store in Chroma
    store = VectorStore(collection_name=collection_name, logger=logger)
    store.add_documents(embedded_chunks)
    logger.info(f"✅ {chunk_type.capitalize()} chunks stored in ChromaDB")

def main():
    embed_and_store(
        chunk_type="lines",
        input_path="data/processed_chunks/lines.json",
        collection_name="lines",
        output_path="embeddings/lines_embedded.json"
    )

    embed_and_store(
        chunk_type="phrases",
        input_path="data/processed_chunks/phrases.json",
        collection_name="phrases",
        output_path="embeddings/phrases_embedded.json"
    )

    embed_and_store(
        chunk_type="fragments",
        input_path="data/processed_chunks/fragments.json",
        collection_name="fragments",
        output_path="embeddings/fragments_embedded.json"
    )

if __name__ == "__main__":
    main()
