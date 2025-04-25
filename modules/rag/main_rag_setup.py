# modules/rag/main_rag_setup.py

import json
import time
import os
import argparse
import sys
from typing import Optional, List, Dict, Any, Union

from modules.rag.embeddings import EmbeddingGenerator
from modules.rag.vector_store import VectorStore
from modules.utils.logger import CustomLogger

# Configuration
DEFAULT_BATCH_SIZE = 250
DEFAULT_SLEEP_TIME = 0.25  # Sleep time between batches for ChromaDB
CHECKPOINT_SIZE = 1000  # Save progress checkpoint every N chunks
COLLECTION_TYPES = ["lines", "phrases", "fragments"]
INPUT_PATHS = {
    "lines": "data/processed_chunks/lines.json",
    "phrases": "data/processed_chunks/phrases.json",
    "fragments": "data/processed_chunks/fragments.json"
}
SAVE_EMBEDDED_JSON = False  # Change to True to save embedded chunks to JSON
EMBEDDED_OUTPUT_DIR = "embeddings/embedded_json"

# Define a more flexible StatsDict type that allows float values
StatsDict = Dict[str, Union[int, float]]

class RagSetup:
    def __init__(
        self, 
        chunk_type: str,
        batch_size: int = DEFAULT_BATCH_SIZE, 
        sleep_time: float = DEFAULT_SLEEP_TIME,
        save_embedded: bool = SAVE_EMBEDDED_JSON,
        logger: Optional[CustomLogger] = None
    ):
        self.chunk_type = chunk_type
        self.batch_size = batch_size
        self.sleep_time = sleep_time
        self.save_embedded = save_embedded
        self.logger = logger or CustomLogger(f"{chunk_type.upper()}_Setup")
        
        # Get input path and validate it exists
        input_path = INPUT_PATHS.get(chunk_type)
        if not input_path:
            self.logger.critical(f"No input path defined for chunk type: {chunk_type}")
            raise ValueError(f"Missing input path configuration for {chunk_type}")
            
        if not os.path.exists(input_path):
            self.logger.critical(f"Input file not found: {input_path}")
            raise FileNotFoundError(f"Missing input file: {input_path}")
            
        self.input_path = input_path
            
        self.output_dir = EMBEDDED_OUTPUT_DIR
        if self.save_embedded:
            os.makedirs(self.output_dir, exist_ok=True)
            
        # Initialize components but don't load data yet
        self.embedder = EmbeddingGenerator(logger=self.logger)
        self.vector_store = VectorStore(
            collection_name=chunk_type, 
            logger=self.logger
        )
        
        # Track processing stats with proper typing for mixed int/float values
        self.stats: StatsDict = {
            "chunks_loaded": 0,
            "chunks_embedded": 0,
            "chunks_stored": 0,
            "batches_processed": 0,
            "embedding_time": 0.0,  # Explicitly a float
            "storage_time": 0.0,    # Explicitly a float
            "checkpoints_saved": 0,
            "errors": 0
        }
        
        # Progress tracking
        self.checkpoint_path = f"embeddings/checkpoints/{chunk_type}_progress.json"
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        
    def load_chunks(self) -> List[Dict[str, Any]]:
        """Load chunks from JSON file with detailed logging."""
        start_time = time.time()
        self.logger.info(f"🔍 STEP 1: Loading chunks from: {self.input_path}")
        
        try:
            with open(self.input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                chunks = data.get("chunks", [])
                
            self.stats["chunks_loaded"] = len(chunks)
            self.logger.info(f"✅ Loaded {len(chunks)} chunks in {time.time() - start_time:.2f}s")
            
            # Verify chunk structure
            if chunks and isinstance(chunks[0], dict):
                sample_keys = list(chunks[0].keys())
                self.logger.info(f"Sample chunk keys: {sample_keys}")
                
                # Check for important keys
                required_keys = ["chunk_id", "text"]
                missing_keys = [key for key in required_keys if key not in sample_keys]
                if missing_keys:
                    self.logger.warning(f"⚠️ Missing essential keys in chunks: {missing_keys}")
            else:
                self.logger.warning("⚠️ Chunks have unexpected format")
                
            return chunks
        except Exception as e:
            self.logger.critical(f"❌ Failed to load chunks: {e}")
            raise
    
    def load_progress(self) -> int:
        """Load progress from checkpoint file."""
        try:
            if os.path.exists(self.checkpoint_path):
                with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    completed = progress.get("chunks_completed", 0)
                    self.logger.info(f"📝 Loaded checkpoint: {completed} chunks already processed")
                    return completed
            return 0
        except Exception as e:
            self.logger.warning(f"⚠️ Could not load progress: {e}, starting from beginning")
            return 0
    
    def save_progress(self, completed: int):
        """Save progress to checkpoint file."""
        try:
            with open(self.checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump({"chunks_completed": completed}, f)
            self.stats["checkpoints_saved"] += 1
            self.logger.info(f"📝 Saved checkpoint: {completed} chunks completed")
        except Exception as e:
            self.logger.error(f"❌ Failed to save checkpoint: {e}")
    
    def save_embedded_chunks(self, embedded_chunks: List[Dict[str, Any]], batch_num: int):
        """Save embedded chunks to JSON file."""
        if not self.save_embedded:
            return
            
        try:
            output_path = os.path.join(
                self.output_dir, 
                f"{self.chunk_type}_embedded_batch_{batch_num}.json"
            )
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(embedded_chunks, f, ensure_ascii=False, indent=2)
            self.logger.info(f"💾 Saved embedded batch to: {output_path}")
        except Exception as e:
            self.logger.error(f"❌ Failed to save embedded chunks: {e}")
            
    def add_to_chroma(self, embedded_batch: List[Dict[str, Any]]) -> bool:
        """Custom method to add documents to ChromaDB with controlled batch size and sleep time."""
        try:
            # Process in our chosen batch size, not the VectorStore's internal one
            for i in range(0, len(embedded_batch), self.batch_size):
                sub_batch = embedded_batch[i:i+self.batch_size]
                self.logger.debug(f"Adding sub-batch {i//self.batch_size + 1} with {len(sub_batch)} chunks")
                
                # Call the original add_documents without custom parameters
                self.vector_store.add_documents(sub_batch)
                
                # Control our own sleep time between batches
                time.sleep(self.sleep_time)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to add documents to ChromaDB: {e}")
            return False
    
    def process_batch(
        self, 
        batch: List[Dict[str, Any]], 
        batch_num: int, 
        total_batches: int
    ) -> bool:
        """Process a single batch of chunks: embed and store."""
        try:
            batch_size = len(batch)
            self.logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({batch_size} chunks)")
            
            # Step 1: Embed the batch
            embed_start = time.time()
            embedded_batch = self.embedder.embed_chunks(batch)
            embed_time = time.time() - embed_start
            self.stats["embedding_time"] = self.stats["embedding_time"] + embed_time  # Explicit addition
            self.stats["chunks_embedded"] += batch_size
            self.logger.info(f"⏱️ Batch {batch_num} embedding completed in {embed_time:.2f}s")
            
            # Verify that embedding worked correctly
            if len(embedded_batch) != batch_size:
                self.logger.warning(f"⚠️ Embedding size mismatch: {len(embedded_batch)} vs {batch_size}")
                
            # Verify chunk_id is preserved 
            for chunk in embedded_batch:
                if "chunk_id" not in chunk:
                    self.logger.error("❌ chunk_id missing from embedded chunk!")
                    return False
                    
            # Step 2: Store in ChromaDB using our custom method
            store_start = time.time()
            success = self.add_to_chroma(embedded_batch)
            if not success:
                self.logger.error(f"❌ Failed to store batch {batch_num} in ChromaDB")
                return False
                
            store_time = time.time() - store_start
            self.stats["storage_time"] = self.stats["storage_time"] + store_time  # Explicit addition
            self.stats["chunks_stored"] += batch_size
            self.logger.info(f"⏱️ Batch {batch_num} storage completed in {store_time:.2f}s")
            
            # Optional: Save embedded batch to JSON
            self.save_embedded_chunks(embedded_batch, batch_num)
            
            # Update stats
            self.stats["batches_processed"] += 1
            batch_total_time = embed_time + store_time
            self.logger.info(f"✅ Batch {batch_num}/{total_batches} completed in {batch_total_time:.2f}s")
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"❌ Batch {batch_num} failed: {e}")
            return False
    
    def run(self) -> bool:
        """Run the complete embedding and storage process."""
        overall_start = time.time()
        self.logger.info(f"🚀 Starting {self.chunk_type} processing with batch size {self.batch_size}")
        
        try:
            # Step 1: Load chunks and checkpoint
            chunks = self.load_chunks()
            starting_point = self.load_progress()
            remaining_chunks = chunks[starting_point:]
            total_chunks = len(remaining_chunks)
            
            if total_chunks == 0:
                self.logger.info("✅ No chunks to process, already completed")
                return True
                
            total_batches = (total_chunks + self.batch_size - 1) // self.batch_size
            self.logger.info(f"📊 Processing {total_chunks} chunks in {total_batches} batches")
            
            # Step 2: Process in batches with checkpoints
            for i in range(0, total_chunks, self.batch_size):
                batch_num = i // self.batch_size + 1
                end_idx = min(i + self.batch_size, total_chunks)
                batch = remaining_chunks[i:end_idx]
                
                # Process the batch
                success = self.process_batch(batch, batch_num, total_batches)
                if not success:
                    self.logger.error(f"❌ Failed at batch {batch_num}, stopping process")
                    return False
                
                # Save progress checkpoint periodically
                chunks_completed = starting_point + end_idx
                if chunks_completed % CHECKPOINT_SIZE == 0 or end_idx == total_chunks:
                    self.save_progress(chunks_completed)
                    
                # Log overall progress
                progress_pct = min(end_idx / total_chunks * 100, 100)
                self.logger.info(f"🔄 Progress: {end_idx}/{total_chunks} chunks ({progress_pct:.1f}%)")
            
            # Final stats
            total_time = time.time() - overall_start
            self.logger.info(f"🎉 {self.chunk_type.upper()} processing complete!")
            self.logger.info(f"⏱️ Total time: {total_time:.2f}s")
            self.logger.info(f"📊 Embedding time: {self.stats['embedding_time']:.2f}s")
            self.logger.info(f"📊 Storage time: {self.stats['storage_time']:.2f}s")
            self.logger.info(f"📊 Chunks processed: {self.stats['chunks_embedded']}")
            self.logger.info(f"📊 Batches processed: {self.stats['batches_processed']}")
            
            # Clean up checkpoint file if completed successfully
            if os.path.exists(self.checkpoint_path):
                os.remove(self.checkpoint_path)
                self.logger.info("🧹 Removed checkpoint file (process completed)")
                
            return True
            
        except Exception as e:
            self.logger.critical(f"❌ Process failed: {e}")
            return False


def process_collection(
    collection_type: str, 
    batch_size: int = DEFAULT_BATCH_SIZE,
    sleep_time: float = DEFAULT_SLEEP_TIME
) -> bool:
    """Process a single collection type."""
    logger = CustomLogger("RagSetup")
    logger.info(f"=== Processing {collection_type} collection ===")
    
    setup = RagSetup(
        chunk_type=collection_type,
        batch_size=batch_size,
        sleep_time=sleep_time,
        save_embedded=SAVE_EMBEDDED_JSON,
        logger=logger
    )
    success = setup.run()
    
    if success:
        logger.info(f"✅ {collection_type} processing completed successfully")
    else:
        logger.error(f"❌ {collection_type} processing failed")
    
    return success


def main():
    """Main function with command-line argument parsing."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process chunks and store embeddings in ChromaDB")
    parser.add_argument(
        "--collection", 
        choices=COLLECTION_TYPES, 
        help="Process only a specific collection type"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=DEFAULT_BATCH_SIZE,
        help=f"Batch size for processing (default: {DEFAULT_BATCH_SIZE})"
    )
    parser.add_argument(
        "--sleep-time", 
        type=float, 
        default=DEFAULT_SLEEP_TIME,
        help=f"Sleep time between ChromaDB insertions (default: {DEFAULT_SLEEP_TIME})"
    )
    parser.add_argument(
        "--save-json", 
        action="store_true",
        help="Save embedded chunks to JSON files"
    )
    args = parser.parse_args()
    
    # Determine which collections to process
    collections_to_process = [args.collection] if args.collection else COLLECTION_TYPES
    
    # Update global save setting if specified
    global SAVE_EMBEDDED_JSON
    if args.save_json:
        SAVE_EMBEDDED_JSON = True
    
    # Set up logging
    logger = CustomLogger("RagSetup")
    logger.info("=== Starting RAG Setup ===")
    logger.info(f"Processing collections: {collections_to_process}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Sleep time: {args.sleep_time}")
    logger.info(f"Save embedded JSON: {SAVE_EMBEDDED_JSON}")
    
    start_time = time.time()
    results = {}
    
    # Process each collection
    for collection in collections_to_process:
        collection_start = time.time()
        success = process_collection(
            collection_type=collection,
            batch_size=args.batch_size,
            sleep_time=args.sleep_time
        )
        collection_time = time.time() - collection_start
        results[collection] = {
            "success": success,
            "time": collection_time
        }
    
    # Final report
    total_time = time.time() - start_time
    logger.info("=== RAG Setup Complete ===")
    logger.info(f"Total processing time: {total_time:.2f}s")
    
    for collection, result in results.items():
        status = "✅ Success" if result["success"] else "❌ Failed"
        logger.info(f"{collection}: {status} in {result['time']:.2f}s")


if __name__ == "__main__":
    main()