# modules/rag/insert_shard.py

import json
import sys
from modules.rag.vector_store import VectorStore
from modules.utils.logger import CustomLogger

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m modules.rag.insert_shard <shard_number>")
        return

    shard_num = int(sys.argv[1])
    path = f"data/embedded_fragments_shards/fragments_shard_{shard_num}.json"
    logger = CustomLogger(f"FRAGMENTS_Insert_Shard_{shard_num}")

    logger.info(f"Loading fragment shard {shard_num} from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        shard = json.load(f)

    store = VectorStore(collection_name="fragments", logger=logger)
    store.add_documents(shard)

    logger.info(f"✅ Inserted shard {shard_num} successfully.")

if __name__ == "__main__":
    main()
