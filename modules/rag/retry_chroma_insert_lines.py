# retry_chroma_insert_lines.py
import json
from modules.rag.vector_store import VectorStore
from modules.utils.logger import CustomLogger

logger = CustomLogger("RetryLinesInsert")
logger.info("Loading previously embedded line chunks...")

with open("embeddings/lines_embedded.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

logger.info(f"Loaded {len(chunks)} embedded line chunks. Starting Chroma insert...")

store = VectorStore(collection_name="lines", logger=logger)
store.add_documents(chunks)

logger.info("✅ Reinsert into Chroma complete.")
