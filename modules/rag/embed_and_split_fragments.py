# modules/rag/embed_and_split_fragments.py

import json
import os
from modules.rag.embeddings import EmbeddingGenerator
from modules.utils.logger import CustomLogger

FRAGMENTS_JSON = "data/processed_chunks/fragments.json"
OUTPUT_DIR = "data/embedded_fragments_shards"
NUM_SHARDS = 10

def load_chunks(path: str) -> list:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)["chunks"]

def split_and_save_chunks(embedded_chunks, num_shards=NUM_SHARDS):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    shard_size = len(embedded_chunks) // num_shards

    for i in range(num_shards):
        start = i * shard_size
        end = (i + 1) * shard_size if i < num_shards - 1 else len(embedded_chunks)
        shard = embedded_chunks[start:end]
        out_path = os.path.join(OUTPUT_DIR, f"fragments_shard_{i+1}.json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(shard, f, indent=2)

        print(f"✅ Saved shard {i+1} with {len(shard)} chunks → {out_path}")

def main():
    logger = CustomLogger("FRAGMENTS_EmbedOnly")
    logger.info("Loading fragment source chunks...")
    fragments = load_chunks(FRAGMENTS_JSON)

    logger.info(f"Embedding {len(fragments)} fragments...")
    embedder = EmbeddingGenerator(logger=logger)
    embedded_chunks = embedder.embed_chunks(fragments)

    logger.info("Splitting into shard files...")
    split_and_save_chunks(embedded_chunks)

    logger.info("🎉 All fragments embedded and sharded successfully.")

if __name__ == "__main__":
    main()
