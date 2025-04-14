# modules/rag/main_rag_setup.py

import json
import time
from typing import Optional
from modules.rag.embeddings import EmbeddingGenerator
from modules.rag.vector_store import VectorStore
from modules.utils.logger import CustomLogger


def load_chunks(path: str) -> list:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)["chunks"]


def embed_and_store(
    chunk_type: str,
    input_path: str,
    collection_name: str,
    output_path: Optional[str] = None
):
    logger = CustomLogger(f"{chunk_type.upper()}_Setup")
    logger.info(f"🔍 Loading chunks from: {input_path}")
    chunks = load_chunks(input_path)

    # Embedding
    embedder = EmbeddingGenerator(logger=logger)
    start_embed = time.time()
    embedded_chunks = embedder.embed_chunks(chunks)
    logger.info(f"✅ Embedding complete for {chunk_type} in {time.time() - start_embed:.2f}s")

    # Optional: Save embedded JSON (DISABLED FOR NOW)
    if output_path:
        embedder.save_embedded_chunks(embedded_chunks, output_path)

    # Store in Chroma
    store = VectorStore(collection_name=collection_name, logger=logger)
    store.add_documents(embedded_chunks)
    logger.info(f"✅ {chunk_type.capitalize()} chunks stored in ChromaDB")


def main():
    start_all = time.time()

    # ❌ Lines already inserted — skip
    # embed_and_store(
    #     chunk_type="lines",
    #     input_path="data/processed_chunks/lines.json",
    #     collection_name="lines",
    #     output_path=None
    # )

    # ✅ Re-run phrases
    embed_and_store(
        chunk_type="phrases",
        input_path="data/processed_chunks/phrases.json",
        collection_name="phrases",
        output_path=None
    )

    # ✅ Re-run fragments
    embed_and_store(
        chunk_type="fragments",
        input_path="data/processed_chunks/fragments.json",
        collection_name="fragments",
        output_path=None
    )

    total = time.time() - start_all
    print(f"🎉 Phrases + Fragments embedded and inserted in {total:.2f} seconds.")


if __name__ == "__main__":
    main()
