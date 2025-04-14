import json
import argparse
from modules.chunking.phrase_chunker import PhraseChunker
from modules.chunking.fragment_chunker import FragmentChunker
from modules.utils.logger import CustomLogger

# Paths
LINE_CHUNKS_PATH = "data/processed_chunks/lines.json"
PHRASE_OUTPUT_PATH = "data/processed_chunks/phrases.json"
FRAGMENT_OUTPUT_PATH = "data/processed_chunks/fragments.json"

def load_line_chunks(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["chunks"]

def save_chunks(chunks, output_path, chunk_type):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "chunk_type": chunk_type,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }, f, indent=2)

def main(run_phrases: bool, run_fragments: bool):
    logger = CustomLogger("ChunkingRunner", log_level="INFO")
    logger.info("Loading line chunks from lines.json...")
    line_chunks = load_line_chunks(LINE_CHUNKS_PATH)

    if run_phrases:
        logger.info("Running PhraseChunker...")
        phrase_chunker = PhraseChunker(logger=logger)
        phrase_chunks = phrase_chunker.chunk_from_line_chunks(line_chunks)
        logger.info(f"Saving {len(phrase_chunks)} phrase chunks to {PHRASE_OUTPUT_PATH}")
        save_chunks(phrase_chunks, PHRASE_OUTPUT_PATH, "phrase")

    if run_fragments:
        logger.info("Running FragmentChunker...")
        fragment_chunker = FragmentChunker(logger=logger)
        fragment_chunks = fragment_chunker.chunk_from_line_chunks(line_chunks)
        logger.info(f"Saving {len(fragment_chunks)} fragment chunks to {FRAGMENT_OUTPUT_PATH}")
        save_chunks(fragment_chunks, FRAGMENT_OUTPUT_PATH, "fragment")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk phrases and/or fragments from line chunks.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--phrases', action='store_true', help="Run only the PhraseChunker")
    group.add_argument('--fragments', action='store_true', help="Run only the FragmentChunker")
    group.add_argument('--both', action='store_true', help="Run both PhraseChunker and FragmentChunker")
    args = parser.parse_args()

    main(run_phrases=args.phrases or args.both, run_fragments=args.fragments or args.both)
