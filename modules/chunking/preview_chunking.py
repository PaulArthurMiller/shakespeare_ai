from modules.chunking.phrase_chunker import PhraseChunker
from modules.chunking.fragment_chunker import FragmentChunker
from modules.utils.logger import CustomLogger
import json

# Load 3 line chunks
with open("data/processed_chunks/preview_lines.json", "r", encoding="utf-8") as f:
    lines = json.load(f)

logger = CustomLogger("PreviewChunking", log_level="DEBUG")

# Phrase Chunking
phrase_chunker = PhraseChunker(logger=logger)
phrases = phrase_chunker.chunk_from_line_chunks(lines)

print("\n=== PHRASE CHUNKS ===")
for p in phrases:
    print(f"[{p['chunk_id']}] {p['text']}")

# Fragment Chunking
fragment_chunker = FragmentChunker(logger=logger)
fragments = fragment_chunker.chunk_from_line_chunks(lines)

print("\n=== FRAGMENT CHUNKS ===")
for f in fragments:
    print(f"[{f['chunk_id']}] {f['text']}")
